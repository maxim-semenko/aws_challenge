"""aws-challenge-admin: the admin route behind the HTTP API JWT authorizer (spec 08, design admin-api §2).
Claims, group parsing and response helpers: shared http_api.py.

Payload format 2.0. Checks in this order: claims present and token_use == "access" (else 401) -> route by
`routeKey` (else 404) -> group "admin" (else 403) -> query parameters (else 400) -> database.

- GET /admin  page of `users` through RDS Proxy (shared db.py: IAM auth token, verified TLS); owner decision
  2026-11-17: the HTTP API has only `GET /admin` and `POST /chat` (curriculum diagram), no `/api` prefix

Errors are RFC 9457 application/problem+json. Every request writes exactly one JSON log line (never the token, the
Authorization header, e-mail or any other user data, never query results). Rules: the admin-api skill.
"""

from __future__ import annotations

import json
import re
import time
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import parse_qsl

import db
from http_api import (  # shared HTTP helpers (lambdas/shared/http_api.py, T05-02); parse_groups re-exported for tests
    DETAIL_401,
    DETAIL_403,
    DETAIL_404,
    DETAIL_500,
    ApiError,
    authorized,
    claims as read_claims,
    is_admin,
    json_response,
    parse_groups,  # noqa: F401
    problem,
)

ROUTE_USERS = "GET /admin"

PAGE_MAX = 1_000_000
SIZE_MIN, SIZE_MAX = 1, 100
DEFAULT_PAGE, DEFAULT_SIZE, DEFAULT_SORT = 0, 20, "createdAt,desc"
USERS_PARAMETERS = ("page", "size", "sort")
DIGITS = re.compile(r"[0-9]+")  # ASCII decimal digits only (str.isdigit also accepts other scripts)

# Sort whitelist: API field -> column, direction -> keyword. The SQL text is built only from these constants.
SORT_COLUMNS = {"createdAt": "created_at", "email": "email", "familyName": "family_name"}
SORT_DIRECTIONS = {"asc": "ASC", "desc": "DESC"}

SQL_COUNT = "SELECT count(*) FROM users"
USER_COLUMNS = (
    "id, email, given_name, family_name, gender, birthdate, country, height_cm, weight_kg, created_at, updated_at"
)
# One fixed statement per (field, direction); values only as :name parameters (pg8000 native).
SQL_PAGE = {
    (field, direction): (
        f"SELECT {USER_COLUMNS} FROM users ORDER BY {column} {keyword} NULLS LAST, id "
        "LIMIT :limit OFFSET :offset"
    )
    for field, column in SORT_COLUMNS.items()
    for direction, keyword in SORT_DIRECTIONS.items()
}

NAME_MAX = 64  # longest parameter name echoed in a 400 detail

MESSAGE_DONE = "request completed"
MESSAGE_FAILED = "INTERNAL_ERROR"


# --- query parameters ------------------------------------------------------------------------------------------------


def _query_pairs(event: dict[str, Any]) -> list[tuple[str, str]]:
    """Query parameters in request order, repeats kept.

    `rawQueryString` is the source: `queryStringParameters` joins repeated values with commas, which cannot be told
    apart from the comma inside `sort`. The dict is used only when the raw string is absent (hand-made test events).
    """
    raw = event.get("rawQueryString")
    if isinstance(raw, str):
        return parse_qsl(raw, keep_blank_values=True)
    params = event.get("queryStringParameters")
    if isinstance(params, dict):
        return [(str(name), str(value)) for name, value in params.items()]
    return []


def _name(name: str) -> str:
    return name if len(name) <= NAME_MAX else name[:NAME_MAX] + "..."


def _integer(name: str, value: str, low: int, high: int) -> int:
    if DIGITS.fullmatch(value) and len(value) <= 12:
        number = int(value)
        if low <= number <= high:
            return number
    raise ApiError(400, f"Query parameter '{name}' must be an integer from {low} to {high}.")


def parse_users_query(pairs: list[tuple[str, str]]) -> tuple[int, int, str, str]:
    """(page, size, sort field, sort direction) from the query of GET /admin (spec 08 §Inputs)."""
    values: dict[str, str] = {}
    for name, value in pairs:
        if name not in USERS_PARAMETERS:
            raise ApiError(400, f"Unknown query parameter '{_name(name)}'; allowed: page, size, sort.")
        if name in values:
            raise ApiError(400, f"Query parameter '{name}' must be given at most once.")
        values[name] = value
    page = _integer("page", values["page"], 0, PAGE_MAX) if "page" in values else DEFAULT_PAGE
    size = _integer("size", values["size"], SIZE_MIN, SIZE_MAX) if "size" in values else DEFAULT_SIZE
    field, _, direction = values.get("sort", DEFAULT_SORT).partition(",")
    if field not in SORT_COLUMNS or direction not in SORT_DIRECTIONS:
        raise ApiError(
            400,
            "Query parameter 'sort' must be '<field>,<direction>' with field createdAt, email or familyName "
            "and direction asc or desc.",
        )
    return page, size, field, direction


# --- routes ----------------------------------------------------------------------------------------------------------


def _iso_utc(value: datetime) -> str:
    aware = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return aware.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _text(value: Any) -> str | None:
    return None if value is None else str(value)


def map_user(row: list[Any] | tuple[Any, ...]) -> dict[str, Any]:
    """One `users` row in USER_COLUMNS order -> the User object of spec 08 §Outputs."""
    (id_, email, given_name, family_name, gender, birthdate, country, height_cm, weight_kg, created_at,
     updated_at) = row
    return {
        "id": str(id_),
        "email": _text(email),
        "givenName": _text(given_name),
        "familyName": _text(family_name),
        "gender": _text(gender),
        "birthdate": birthdate.isoformat() if isinstance(birthdate, date) else _text(birthdate),
        "country": _text(country),
        "heightCm": height_cm,
        "weightKg": weight_kg,
        "createdAt": _iso_utc(created_at),
        "updatedAt": _iso_utc(updated_at),
    }


def _users(event: dict[str, Any]) -> dict[str, Any]:
    page, size, field, direction = parse_users_query(_query_pairs(event))
    conn = None
    try:
        conn = db.connect()
        total = conn.run(SQL_COUNT)[0][0]
        rows = conn.run(SQL_PAGE[(field, direction)], limit=size, offset=page * size)
    finally:
        db.close_quietly(conn)
    return json_response({"items": [map_user(row) for row in rows], "page": page, "size": size, "total": total})


def _route(event: dict[str, Any], route: Any, claims: dict[str, Any]) -> dict[str, Any]:
    if route == ROUTE_USERS:
        if not is_admin(claims):
            raise ApiError(403, DETAIL_403)
        return _users(event)
    raise ApiError(404, DETAIL_404)


# --- handler ---------------------------------------------------------------------------------------------------------


def _error_class(exc: BaseException) -> str:
    """Class name only (never the message, which may hold SQL or values); the cause for DB_CONNECT_FAILED."""
    if isinstance(exc, db.DbConnectError) and exc.__cause__ is not None:
        return type(exc.__cause__).__name__
    return type(exc).__name__


def _log(
    context: Any,
    event: Any,
    claims: dict[str, Any] | None,
    status: int,
    started: float,
    error: BaseException | None,
) -> None:
    request_context = event.get("requestContext") if isinstance(event, dict) else None
    sub = claims.get("sub") if claims is not None else None
    if status >= 500:
        level, outcome = "ERROR", "failure"
        message = db.ERROR_CONNECT if isinstance(error, db.DbConnectError) else MESSAGE_FAILED
    elif status >= 400:
        level, outcome, message = "WARNING", "client_error", MESSAGE_DONE
    else:
        level, outcome, message = "INFO", "success", MESSAGE_DONE
    line: dict[str, Any] = {
        "level": level,
        "message": message,
        "function": getattr(context, "function_name", None),
        "awsRequestId": getattr(context, "aws_request_id", None),
        "apiRequestId": request_context.get("requestId") if isinstance(request_context, dict) else None,
        "userSub": sub if isinstance(sub, str) else None,
        "route": event.get("routeKey") if isinstance(event, dict) else None,
        "status": status,
        "durationMs": round((time.monotonic() - started) * 1000),
        "outcome": outcome,
    }
    if status >= 500 and error is not None:
        line["errorClass"] = _error_class(error)
    print(json.dumps(line, separators=(",", ":")))


def lambda_handler(event: Any, context: Any) -> dict[str, Any]:
    started = time.monotonic()
    claims: dict[str, Any] | None = None
    error: BaseException | None = None
    response: dict[str, Any] = problem(500, DETAIL_500)
    try:
        claims = read_claims(event)
        if not authorized(claims):
            raise ApiError(401, DETAIL_401)
        assert claims is not None and isinstance(event, dict)
        response = _route(event, event.get("routeKey"), claims)
    except ApiError as exc:
        response = problem(exc.status, exc.detail)
    except Exception as exc:  # database or unexpected error: generic detail, class name in the log only
        error = exc
        response = problem(500, DETAIL_500)
    finally:
        _log(context, event, claims, response["statusCode"], started, error)
    return response
