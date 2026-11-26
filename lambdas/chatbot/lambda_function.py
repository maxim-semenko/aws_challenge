"""aws-challenge-chatbot: POST /chat — natural-language question -> rows (spec 12, design semantic-search §4).

Payload format 2.0 behind the HTTP API JWT authorizer. Checks in this order, no Bedrock or DB call before all pass:
claims present and token_use == "access" (else 401) -> routeKey `POST /chat` (else 404) -> group "admin" (else 403)
-> body (else 400). Then the mode (S2): the whole word "sql" (case-insensitive) -> LLM writes one SELECT (llm.py),
validated by sql_guard.py and executed read-only (search.py); otherwise the query is embedded with Titan V2 (shared
embeddings.py) and the five most similar users are returned. Bedrock is always called before the DB connection is
opened; nothing is retried. Exactly one JSON log line per request, never the query text, the model's answer, the SQL
text, row values, the vector or the token (length and hash only). Rules: the chatbot-api skill.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import time
from typing import Any

import db
import embeddings
import http_api
import llm
import search
import sql_guard
from http_api import ApiError

ROUTE_CHAT = "POST /chat"
MODE_SQL, MODE_VECTOR = "sql", "vector"

BODY_MAX_BYTES = 4096
QUERY_MIN, QUERY_MAX = 1, 500
SQL_KEYWORD = re.compile(r"\bsql\b", re.IGNORECASE)
SIMILARITY_PREFIX = re.compile(
    r"^\s*(?:which|what|find|show(?:\s+me)?)?\s*(?:users?|people)\s+(?:are\s+|is\s+)?similar\s+to\s*[:\-]?\s*",
    re.IGNORECASE,
)

DETAIL_BODY_OBJECT = "body must be a JSON object"
DETAIL_BODY_SIZE = "body must be at most 4096 bytes"
DETAIL_UNKNOWN_FIELD = "unknown field"
DETAIL_QUERY_LENGTH = "query must be 1 to 500 characters"
DETAIL_QUERY_PARAMETERS = "query parameters are not accepted"
DETAIL_EMPTY_AFTER_PREFIX = "query must name what the users are similar to"
DETAIL_REPHRASE = "The question could not be turned into a safe query. Rephrase it."
DETAIL_429 = "The AI service is busy. Try again shortly."
DETAIL_502 = "The AI service is not available."

MESSAGE_DONE = "request completed"
MESSAGE_FAILED = "INTERNAL_ERROR"
MESSAGE_BEDROCK = "BEDROCK_FAILED"

LOG_FIELDS = (
    "mode", "queryLength", "queryHash", "embedMs", "llmMs", "dbMs", "inputTokens", "outputTokens", "modelId",
    "rowCount", "truncated", "sqlHash", "guardResult", "errorClass",
)


def short_hash(text: str) -> str:
    """First 16 hex characters of SHA-256 (log correlation without the text)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _ms(since: float) -> int:
    return round((time.monotonic() - since) * 1000)


# --- request ---------------------------------------------------------------------------------------------------------


def parse_query(event: dict[str, Any]) -> str:
    """The trimmed `query` of the body (spec 12 §Inputs); ApiError(400) with a fixed detail otherwise."""
    if event.get("rawQueryString") or event.get("queryStringParameters"):
        raise ApiError(400, DETAIL_QUERY_PARAMETERS)
    body = event.get("body")
    if not isinstance(body, str):
        raise ApiError(400, DETAIL_BODY_OBJECT)
    try:
        raw = base64.b64decode(body, validate=True) if event.get("isBase64Encoded") is True else body.encode("utf-8")
    except (binascii.Error, ValueError, UnicodeError) as exc:
        raise ApiError(400, DETAIL_BODY_OBJECT) from exc
    if len(raw) > BODY_MAX_BYTES:
        raise ApiError(400, DETAIL_BODY_SIZE)
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ApiError(400, DETAIL_BODY_OBJECT) from exc
    if not isinstance(data, dict):
        raise ApiError(400, DETAIL_BODY_OBJECT)
    if set(data) - {"query"}:
        raise ApiError(400, DETAIL_UNKNOWN_FIELD)
    query = data.get("query")
    if not isinstance(query, str):
        raise ApiError(400, DETAIL_QUERY_LENGTH)
    query = query.strip()
    if not QUERY_MIN <= len(query) <= QUERY_MAX:
        raise ApiError(400, DETAIL_QUERY_LENGTH)
    return query


def mode_of(query: str) -> str:
    return MODE_SQL if SQL_KEYWORD.search(query) else MODE_VECTOR


def strip_similarity_prefix(query: str) -> str:
    return SIMILARITY_PREFIX.sub("", query, count=1).strip()


# --- the two paths ---------------------------------------------------------------------------------------------------


def _bedrock_failed(state: dict[str, Any], error_class: str) -> ApiError:
    state["errorClass"] = error_class
    if error_class == llm.THROTTLED:
        return ApiError(429, DETAIL_429)
    return ApiError(502, DETAIL_502)


def _vector(query: str, state: dict[str, Any]) -> dict[str, Any]:
    text = strip_similarity_prefix(query)
    if text == "":
        raise ApiError(400, DETAIL_EMPTY_AFTER_PREFIX)
    state["modelId"] = embeddings.MODEL_ID
    started = time.monotonic()
    try:
        vector, tokens = embeddings.embed_with_usage(text)
    except embeddings.EmbeddingError as exc:
        raise _bedrock_failed(state, exc.error_class) from exc
    finally:
        state["embedMs"] = _ms(started)
    state["inputTokens"], state["outputTokens"] = tokens, 0
    started = time.monotonic()
    try:
        rows = search.similar_users(vector)
    finally:
        state["dbMs"] = _ms(started)
    state["rowCount"], state["truncated"] = len(rows), False
    return {"columns": list(search.VECTOR_COLUMNS), "rows": rows, "sql": None}


def _sql(query: str, state: dict[str, Any]) -> dict[str, Any]:
    state["modelId"] = llm.MODEL_ID
    started = time.monotonic()
    try:
        answer = llm.ask(query)
    except llm.LlmError as exc:
        raise _bedrock_failed(state, exc.error_class) from exc
    finally:
        state["llmMs"] = _ms(started)
    state["inputTokens"], state["outputTokens"] = answer.input_tokens, answer.output_tokens
    try:
        accepted = sql_guard.check(answer.text)
    except sql_guard.Rejected as exc:
        state["guardResult"] = exc.code
        raise ApiError(400, DETAIL_REPHRASE) from exc
    state["guardResult"] = sql_guard.ACCEPTED
    state["sqlHash"] = short_hash(accepted.sql)
    started = time.monotonic()
    try:
        columns, rows, truncated = search.run_statement(accepted.sql)
    except search.StatementError as exc:
        state["errorClass"] = type(exc.__cause__ or exc).__name__
        raise ApiError(400, DETAIL_REPHRASE) from exc
    finally:
        state["dbMs"] = _ms(started)
    state["rowCount"], state["truncated"] = len(rows), truncated
    return {"columns": columns, "rows": rows, "sql": accepted.sql}


def _chat(event: dict[str, Any], state: dict[str, Any], started: float) -> dict[str, Any]:
    query = parse_query(event)
    state["queryLength"], state["queryHash"] = len(query), short_hash(query)
    state["mode"] = mode_of(query)
    result = _sql(query, state) if state["mode"] == MODE_SQL else _vector(query, state)
    return http_api.json_response({
        "mode": state["mode"],
        "columns": result["columns"],
        "rows": result["rows"],
        "rowCount": state["rowCount"],
        "truncated": state["truncated"],
        "sql": result["sql"],
        "timings": {
            "embedMs": state["embedMs"],
            "llmMs": state["llmMs"],
            "dbMs": state["dbMs"],
            "totalMs": _ms(started),
        },
        "tokens": {"input": state["inputTokens"], "output": state["outputTokens"]},
        "modelId": state["modelId"],
    })


# --- handler ---------------------------------------------------------------------------------------------------------


def _error_class(exc: BaseException) -> str:
    """Class name only (never the message); the cause for DB_CONNECT_FAILED."""
    if isinstance(exc, db.DbConnectError) and exc.__cause__ is not None:
        return type(exc.__cause__).__name__
    return type(exc).__name__


def _log(context: Any, event: Any, claims: dict[str, Any] | None, status: int, started: float,
         state: dict[str, Any], error: BaseException | None) -> None:
    request_context = event.get("requestContext") if isinstance(event, dict) else None
    sub = claims.get("sub") if claims is not None else None
    if status >= 500:
        level, outcome = "ERROR", "failure"
        if status == 502:
            message = MESSAGE_BEDROCK
        elif isinstance(error, db.DbConnectError):
            message = db.ERROR_CONNECT
        else:
            message = MESSAGE_FAILED
    elif status >= 400:
        level, outcome, message = "WARNING", "client_error", MESSAGE_DONE
    else:
        level, outcome, message = "INFO", "success", MESSAGE_DONE
    if error is not None and state["errorClass"] is None:
        state["errorClass"] = _error_class(error)
    line: dict[str, Any] = {
        "level": level,
        "message": message,
        "function": getattr(context, "function_name", None),
        "awsRequestId": getattr(context, "aws_request_id", None),
        "apiRequestId": request_context.get("requestId") if isinstance(request_context, dict) else None,
        "userSub": sub if isinstance(sub, str) else None,
        "route": event.get("routeKey") if isinstance(event, dict) else None,
        "status": status,
        "outcome": outcome,
        "durationMs": _ms(started),
    }
    line.update({field: state[field] for field in LOG_FIELDS})
    print(json.dumps(line, separators=(",", ":")))


def lambda_handler(event: Any, context: Any) -> dict[str, Any]:
    started = time.monotonic()
    claims: dict[str, Any] | None = None
    state: dict[str, Any] = {field: None for field in LOG_FIELDS}
    error: BaseException | None = None
    response: dict[str, Any] = http_api.problem(500, http_api.DETAIL_500)
    try:
        claims = http_api.claims(event)
        if not http_api.authorized(claims):
            raise ApiError(401, http_api.DETAIL_401)
        assert claims is not None and isinstance(event, dict)
        if event.get("routeKey") != ROUTE_CHAT:
            raise ApiError(404, http_api.DETAIL_404)
        if not http_api.is_admin(claims):
            raise ApiError(403, http_api.DETAIL_403)
        response = _chat(event, state, started)
    except ApiError as exc:
        response = http_api.problem(exc.status, exc.detail)
    except Exception as exc:  # database or unexpected error: generic detail, class name in the log only
        error = exc
        response = http_api.problem(500, http_api.DETAIL_500)
    finally:
        _log(context, event, claims, response["statusCode"], started, state, error)
    return response
