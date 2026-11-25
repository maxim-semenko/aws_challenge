"""Owner actions of aws-challenge-sync for vectors: embed-missing (spec 10), seed and similar (spec 11).

Reached through the dispatch in lambda_function.py (spec 06 §Inputs) for {"action": "embed-missing"},
{"action": "seed", "count": N} and {"action": "similar", "userId": "<uuid>"} from the console Test tab. One DB
connection per invocation, closed in `finally`; one JSON log line without ids of results, vectors or attribute values.
Rules: the bedrock-embeddings and postgres-migrations skills.
"""

from __future__ import annotations

import json
import random
import re
import time
import uuid
from datetime import date, datetime, timezone
from typing import Any

import pg8000.native

import db
import embeddings

EMBED_MISSING, SEED, SIMILAR = "embed-missing", "seed", "similar"
ACTIONS = (EMBED_MISSING, SEED, SIMILAR)

# Socket timeout of the action connections: longer than the upsert's 10 s default (seed inserts 1000 rows, similar
# runs EXPLAIN ANALYZE twice), below the 60 s function timeout.
DB_TIMEOUT_S = 30.0
# embed-missing stops starting Bedrock calls when less than this remains of the function's time.
TIME_BUDGET_MS = 10_000
EMBED_BATCH_LIMIT = 1000
SEED_MAX = 1000
SEED_BATCH = 100

UUID_PATTERN = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")

# --- SQL (values only as :name parameters) ---------------------------------------------------------------------------

TEXT_COLUMNS = ("gender", "birthdate", "country", "height_cm", "weight_kg")
SQL_SELECT_MISSING = (
    "SELECT id, gender, birthdate, country, height_cm, weight_kg FROM users "
    f"WHERE embedding IS NULL ORDER BY id LIMIT {EMBED_BATCH_LIMIT}"
)
SQL_UPDATE_EMBEDDING = (
    "UPDATE users SET embedding = CAST(:embedding AS vector) WHERE id = CAST(:id AS uuid) AND embedding IS NULL"
)
SQL_COUNT_REMAINING = (
    "SELECT count(*) FROM users WHERE embedding IS NULL AND ("
    + " OR ".join(f"{column} IS NOT NULL" for column in TEXT_COLUMNS)
    + ")"
)

SEED_COLUMNS = (
    ("id", "uuid"), ("email", "text"), ("given_name", "text"), ("family_name", "text"), ("gender", "text"),
    ("birthdate", "date"), ("country", "text"), ("height_cm", "integer"), ("weight_kg", "integer"),
    ("confirmed_at", "timestamptz"),
)
SEED_EMAIL_DOMAIN = "seed.invalid"
SQL_COUNT_SEEDED = "SELECT count(*) FROM users WHERE email LIKE '%@seed.invalid'"

SQL_SELECT_VECTOR = "SELECT CAST(embedding AS text) FROM users WHERE id = CAST(:id AS uuid)"
SQL_COUNT_ROWS = "SELECT count(*), count(embedding) FROM users"
# The curriculum's query (W4-G3): ORDER BY embedding <-> $1 LIMIT 5, the vector passed as a parameter.
SQL_SIMILAR = (
    "SELECT id, embedding <-> CAST(:q AS vector) AS distance FROM users "
    "ORDER BY embedding <-> CAST(:q AS vector) LIMIT 5"
)
SQL_EXPLAIN_SIMILAR = "EXPLAIN (ANALYZE, FORMAT JSON) " + SQL_SIMILAR
SQL_FORCE_INDEX = "SET LOCAL enable_seqscan = off"

# --- synthetic users (spec 11 §Inputs; fictitious values only) -------------------------------------------------------

SEED_NAMESPACE = uuid.UUID("5d0a3c1e-7b42-4f6e-9a8d-2c1b0e4f7a93")
GIVEN_NAMES = ("Alex", "Robin", "Sam", "Kim", "Jo", "Lee", "Max", "Noa", "Toni", "Eli", "Ari", "Pat")
FAMILY_NAMES = ("Testmann", "Probst", "Muster", "Beispiel", "Example", "Sample", "Placeholder", "Fiktiv", "Demo",
                "Mock")
COUNTRIES = ("Austria", "Germany", "France", "Italy", "Spain", "Poland", "Ireland", "Portugal", "Sweden", "Norway",
             "Netherlands", "Belgium", "Czechia", "Greece", "Finland", "Denmark")
BIRTHDATE_FIRST = date(1950, 1, 1).toordinal()
BIRTHDATE_LAST = date(2007, 12, 31).toordinal()


class VectorError(Exception):
    """Function error whose message is one of the spec 10 / spec 11 error strings."""


def seed_user(k: int, confirmed_at: datetime) -> dict[str, Any]:
    """Synthetic user number k (1-based); the same k always gives the same values (except confirmed_at)."""
    rng = random.Random(f"seed-{k}")  # str seed: hashed with SHA-512, stable across processes
    return {
        "id": str(uuid.uuid5(SEED_NAMESPACE, f"seed-{k}")),
        "email": f"seed-{k:04d}@{SEED_EMAIL_DOMAIN}",
        "given_name": rng.choice(GIVEN_NAMES),
        "family_name": rng.choice(FAMILY_NAMES),
        "gender": rng.choice(("female", "male")),
        "birthdate": date.fromordinal(rng.randint(BIRTHDATE_FIRST, BIRTHDATE_LAST)),
        "country": rng.choice(COUNTRIES),
        "height_cm": rng.randint(140, 210),
        "weight_kg": rng.randint(40, 150),
        "confirmed_at": confirmed_at,
    }


def seed_insert_sql(rows: int) -> str:
    """Multi-row insert for `rows` users; parameter names carry only the row index, never a value."""
    values = ", ".join(
        "(" + ", ".join(f"CAST(:{name}_{i} AS {sql_type})" for name, sql_type in SEED_COLUMNS) + ")"
        for i in range(rows)
    )
    columns = ", ".join(name for name, _ in SEED_COLUMNS)
    return f"INSERT INTO users ({columns}) VALUES {values} ON CONFLICT (id) DO NOTHING RETURNING 1"


def parse_plan(explain: Any) -> dict[str, Any]:
    """{"scan", "executionMs"} from EXPLAIN (ANALYZE, FORMAT JSON) output (list with one plan object, or its text)."""
    if isinstance(explain, str):
        explain = json.loads(explain)
    top = explain[0]

    def first_scan(node: dict[str, Any]) -> str | None:
        node_type = node.get("Node Type", "")
        if node_type.endswith("Scan"):
            index = node.get("Index Name")
            return f"{node_type} using {index}" if index else node_type
        for child in node.get("Plans", []):
            found = first_scan(child)
            if found:
                return found
        return None

    return {"scan": first_scan(top["Plan"]) or "unknown", "executionMs": float(top["Execution Time"])}


# --- helpers ---------------------------------------------------------------------------------------------------------


def _sqlstate(exc: BaseException) -> str:
    detail = exc.args[0] if exc.args else None
    if isinstance(detail, dict) and detail.get("C"):
        return str(detail["C"])
    return "UNKNOWN"


DB_ERRORS = (pg8000.native.DatabaseError, pg8000.native.InterfaceError, OSError)


def _rollback_quietly(conn: Any) -> None:
    try:
        conn.run("ROLLBACK")
    except Exception:
        pass


def _remaining_ms(context: Any) -> float:
    getter = getattr(context, "get_remaining_time_in_millis", None)
    return float(getter()) if callable(getter) else float("inf")


def _is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= SEED_MAX


# --- actions ---------------------------------------------------------------------------------------------------------


def embed_missing(conn: Any, context: Any, state: dict[str, Any]) -> dict[str, Any]:
    """Spec 10 Behaviour 4: one Bedrock call per row, committed per row, stop on time budget or non-row error."""
    counts = {"embedded": 0, "skipped": 0, "failed": 0}
    stopped = "done"
    for row in conn.run(SQL_SELECT_MISSING):
        row_id, values = row[0], dict(zip(TEXT_COLUMNS, row[1:]))
        text = embeddings.build_text(values)
        if text is None:
            counts["skipped"] += 1
            continue
        if _remaining_ms(context) < TIME_BUDGET_MS:
            stopped = "time_budget"
            break
        started = time.monotonic()
        state["bedrockCalls"] += 1
        try:
            vector = embeddings.embed(text)
        except embeddings.EmbeddingError as exc:
            counts["failed"] += 1
            if exc.error_class == embeddings.BAD_RESPONSE:
                continue
            stopped = f"bedrock_error: {exc.error_class}"
            state["bedrockError"] = exc.error_class
            break
        finally:
            state["bedrockMs"] += round((time.monotonic() - started) * 1000)
        conn.run(SQL_UPDATE_EMBEDDING, embedding=embeddings.to_vector_literal(vector), id=str(row_id))
        counts["embedded"] += 1
    remaining = int(conn.run(SQL_COUNT_REMAINING)[0][0])
    return {**counts, "remaining": remaining, "stopped": stopped}


def seed(conn: Any, count: int) -> dict[str, Any]:
    """Spec 11 Behaviour 1: users 1..count in one transaction, ON CONFLICT DO NOTHING, no vectors."""
    confirmed_at = datetime.now(timezone.utc)
    users = [seed_user(k, confirmed_at) for k in range(1, count + 1)]
    inserted = 0
    conn.run("BEGIN")
    try:
        for start in range(0, len(users), SEED_BATCH):
            batch = users[start:start + SEED_BATCH]
            params = {f"{name}_{i}": user[name] for i, user in enumerate(batch) for name, _ in SEED_COLUMNS}
            inserted += len(conn.run(seed_insert_sql(len(batch)), **params))
        conn.run("COMMIT")
    except BaseException:
        _rollback_quietly(conn)
        raise
    seeded = int(conn.run(SQL_COUNT_SEEDED)[0][0])
    return {"inserted": inserted, "seeded": seeded}


def similar(conn: Any, user_id: str) -> dict[str, Any]:
    """Spec 11 Behaviour 2: top 5 by `<->`, then EXPLAIN ANALYZE default and with seq scans off, rolled back."""
    found = conn.run(SQL_SELECT_VECTOR, id=user_id)
    if not found or found[0][0] is None:
        raise VectorError("SIMILAR_NOT_FOUND")
    query_vector = found[0][0]
    rows, with_embedding = (int(value) for value in conn.run(SQL_COUNT_ROWS)[0])
    # Rows without a vector have a NULL distance (a sequential scan may return them); they are not neighbours.
    items = [
        {"id": str(row_id), "distance": float(distance)}
        for row_id, distance in conn.run(SQL_SIMILAR, q=query_vector)
        if distance is not None
    ]
    conn.run("BEGIN")
    try:
        default = parse_plan(conn.run(SQL_EXPLAIN_SIMILAR, q=query_vector)[0][0])
        conn.run(SQL_FORCE_INDEX)  # SET LOCAL: ends with this transaction
        forced = parse_plan(conn.run(SQL_EXPLAIN_SIMILAR, q=query_vector)[0][0])
    finally:
        _rollback_quietly(conn)
    return {"rows": rows, "withEmbedding": with_embedding, "items": items, "default": default, "indexForced": forced}


# --- handler ---------------------------------------------------------------------------------------------------------

BAD_REQUEST = {EMBED_MISSING: "EMBED_BAD_REQUEST", SEED: "SEED_BAD_REQUEST", SIMILAR: "SIMILAR_BAD_REQUEST"}
FAILED = {EMBED_MISSING: "EMBED_FAILED", SEED: "SEED_FAILED", SIMILAR: "SIMILAR_FAILED"}


def _parse(event: dict[str, Any]) -> tuple[str, Any]:
    action = event["action"]
    if action == EMBED_MISSING and set(event) == {"action"}:
        return action, None
    if action == SEED and set(event) == {"action", "count"} and _is_count(event["count"]):
        return action, event["count"]
    if action == SIMILAR and set(event) == {"action", "userId"}:
        user_id = event["userId"]
        if isinstance(user_id, str) and UUID_PATTERN.fullmatch(user_id):
            return action, user_id.lower()
    raise VectorError(BAD_REQUEST[action])


def _log(context: Any, state: dict[str, Any], result: dict[str, Any] | None, started: float,
         error: BaseException | None) -> None:
    # Counts and timings only: never result ids, vectors, embedding texts or attribute values.
    action = state["action"]
    line: dict[str, Any] = {
        "level": "INFO",
        "message": f"{action} completed",
        "function": getattr(context, "function_name", None),
        "awsRequestId": getattr(context, "aws_request_id", None),
        "action": action,
    }
    if action == EMBED_MISSING:
        for key in ("embedded", "skipped", "failed", "remaining", "stopped"):
            line[key] = (result or {}).get(key)
        line["bedrockCalls"] = state["bedrockCalls"]
        line["bedrockMs"] = state["bedrockMs"]
        if state["bedrockError"] is not None:
            line["level"] = "WARNING"
            line["errorClass"] = state["bedrockError"]
    elif action == SEED:
        line["inserted"] = (result or {}).get("inserted")
        line["seeded"] = (result or {}).get("seeded")
    elif action == SIMILAR:
        result = result or {}
        line["rows"] = result.get("rows")
        line["withEmbedding"] = result.get("withEmbedding")
        line["defaultScan"] = result.get("default", {}).get("scan")
        line["defaultMs"] = result.get("default", {}).get("executionMs")
        line["indexScan"] = result.get("indexForced", {}).get("scan")
        line["indexMs"] = result.get("indexForced", {}).get("executionMs")
    line["outcome"] = "success" if error is None else "failure"
    line["durationMs"] = round((time.monotonic() - started) * 1000)
    if error is not None:
        known = isinstance(error, (VectorError, db.DbConnectError))
        line["level"] = "ERROR"
        line["message"] = str(error) if known else "unexpected error"
        line["errorClass"] = type(error.__cause__ or error).__name__
    print(json.dumps(line, separators=(",", ":")))


def handle(event: dict[str, Any], context: Any) -> dict[str, Any]:
    started = time.monotonic()
    state: dict[str, Any] = {"action": event["action"], "bedrockCalls": 0, "bedrockMs": 0, "bedrockError": None}
    conn = None
    result: dict[str, Any] | None = None
    error: BaseException | None = None
    try:
        action, argument = _parse(event)
        conn = db.connect(timeout=DB_TIMEOUT_S)
        try:
            if action == EMBED_MISSING:
                result = embed_missing(conn, context, state)
            elif action == SEED:
                result = seed(conn, argument)
            else:
                result = similar(conn, argument)
        except DB_ERRORS as exc:
            raise VectorError(f"{FAILED[action]}: {_sqlstate(exc)}") from exc
        return result
    except BaseException as exc:
        error = exc
        raise
    finally:
        db.close_quietly(conn)
        _log(context, state, result, started, error)
