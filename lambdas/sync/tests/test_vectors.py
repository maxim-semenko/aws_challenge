"""Unit tests of vectors.py: embed-missing (spec 10, AC-10.2), seed and similar (spec 11, AC-11.1).

The database is the in-memory VectorDb double, Bedrock the StubBedrock double; nothing reaches AWS or PostgreSQL.
"""

import json
import re
import uuid
from datetime import date, datetime, timezone

import pg8000.native
import pytest
from botocore.exceptions import ClientError, ConnectTimeoutError, EndpointConnectionError, ReadTimeoutError

import db
import embeddings
import lambda_function
import migrator
import vectors
from bedrock_stub import StubBedrock, install, unit_vector

SEQ_PLAN = [{
    "Plan": {"Node Type": "Limit", "Plans": [{"Node Type": "Sort", "Plans": [
        {"Node Type": "Seq Scan", "Relation Name": "users"}]}]},
    "Planning Time": 0.2, "Execution Time": 3.25,
}]
INDEX_PLAN = [{
    "Plan": {"Node Type": "Limit", "Plans": [
        {"Node Type": "Index Scan", "Index Name": "users_embedding_hnsw_idx", "Relation Name": "users"}]},
    "Planning Time": 0.1, "Execution Time": 0.75,
}]


class Context:
    function_name = "aws-challenge-sync"
    aws_request_id = "req-vec"

    def __init__(self, remaining_ms=None):
        # list of values returned one per call (last one repeats), or None for "plenty of time"
        self.remaining_ms = list(remaining_ms or [50_000])

    def get_remaining_time_in_millis(self):
        return self.remaining_ms.pop(0) if len(self.remaining_ms) > 1 else self.remaining_ms[0]


def user(n, **values):
    row = {"gender": "female", "birthdate": date(1990, 1, n % 28 + 1), "country": "Austria", "height_cm": 170,
           "weight_kg": 60 + n, "embedding": None, "email": f"real{n}@example.com"}
    row.update(values)
    return str(uuid.UUID(int=n)), row


class VectorDb:
    """pg8000.native.Connection double for the vector actions; users as a dict id -> column values."""

    def __init__(self, users=(), similar_rows=(), error_on=None, error=None):
        self.users = dict(users)
        self.similar_rows = list(similar_rows)
        self.error_on, self.error = error_on, error
        self.statements = []
        self.params = []
        self.tx = None
        self.seqscan_off = False
        self.commits = self.rollbacks = 0
        self.closed = False

    def run(self, sql, **params):
        self.statements.append(sql)
        self.params.append(params)
        if self.error_on is not None and (sql == self.error_on or sql.startswith(self.error_on)):
            raise self.error
        if sql == "BEGIN":
            assert self.tx is None
            self.tx = {}
            return []
        if sql == "COMMIT":
            self.users.update(self.tx)
            self.tx, self.seqscan_off = None, False
            self.commits += 1
            return []
        if sql == "ROLLBACK":
            self.tx, self.seqscan_off = None, False
            self.rollbacks += 1
            return []
        if sql == vectors.SQL_SELECT_MISSING:
            missing = sorted(k for k, v in self.users.items() if v["embedding"] is None)[:1000]
            return [[uuid.UUID(k), *(self.users[k][c] for c in vectors.TEXT_COLUMNS)] for k in missing]
        if sql == vectors.SQL_UPDATE_EMBEDDING:
            assert self.tx is None, "per-row update must be committed on its own"
            row = self.users[params["id"]]
            if row["embedding"] is None:
                row["embedding"] = params["embedding"]
            return []
        if sql == vectors.SQL_COUNT_REMAINING:
            return [[sum(1 for v in self.users.values() if v["embedding"] is None
                         and any(v[c] is not None for c in vectors.TEXT_COLUMNS))]]
        if sql.startswith("INSERT INTO users"):
            assert self.tx is not None, "seed outside its transaction"
            inserted = []
            index = 0
            while f"id_{index}" in params:
                row_id = params[f"id_{index}"]
                if row_id not in self.users and row_id not in self.tx:
                    self.tx[row_id] = {name: params[f"{name}_{index}"] for name, _ in vectors.SEED_COLUMNS}
                    self.tx[row_id]["embedding"] = None
                    inserted.append([1])
                index += 1
            return inserted
        if sql == vectors.SQL_COUNT_SEEDED:
            return [[sum(1 for v in self.users.values() if v["email"].endswith("@seed.invalid"))]]
        if sql == vectors.SQL_SELECT_VECTOR:
            row = self.users.get(params["id"])
            return [] if row is None else [[row["embedding"]]]
        if sql == vectors.SQL_COUNT_ROWS:
            return [[len(self.users), sum(1 for v in self.users.values() if v["embedding"] is not None)]]
        if sql == vectors.SQL_SIMILAR:
            return [list(r) for r in self.similar_rows]
        if sql == vectors.SQL_FORCE_INDEX:
            assert self.tx is not None, "SET LOCAL outside a transaction"
            self.seqscan_off = True
            return []
        if sql == vectors.SQL_EXPLAIN_SIMILAR:
            assert self.tx is not None, "EXPLAIN ANALYZE outside the rolled-back transaction"
            return [[INDEX_PLAN if self.seqscan_off else json.dumps(SEQ_PLAN)]]
        raise AssertionError(f"unexpected statement: {sql[:80]}")

    def close(self):
        self.closed = True


@pytest.fixture
def bedrock(monkeypatch):
    return install(monkeypatch, StubBedrock())


def use_db(monkeypatch, database):
    calls = []

    def connect(**kwargs):
        calls.append(kwargs)
        return database

    monkeypatch.setattr(db, "connect", connect)
    database.connects = calls
    return database


@pytest.fixture
def no_connect(monkeypatch):
    def forbidden(**kwargs):
        raise AssertionError("must not connect")

    monkeypatch.setattr(db, "connect", forbidden)


def invoke(event, context=None):
    return lambda_function.lambda_handler(event, context or Context())


def log_line(capsys):
    (line,) = [json.loads(text) for text in capsys.readouterr().out.splitlines() if text.strip()]
    return line


# --- dispatch (spec 06 §Inputs) -----------------------------------------------------------------------------------


@pytest.mark.parametrize("action", ["embed-missing", "seed", "similar"])
def test_vector_actions_reach_vectors_and_never_the_runner(action, monkeypatch):
    calls = []
    monkeypatch.setattr(vectors, "handle", lambda event, context: calls.append(event) or {"ok": True})
    monkeypatch.setattr(migrator, "handle", lambda event, context: pytest.fail("runner"))
    assert invoke({"action": action}) == {"ok": True}
    assert calls == [{"action": action}]


@pytest.mark.parametrize("event", [{"action": "migrate"}, {"action": "EMBED-MISSING"}, {"action": ["seed"]}])
def test_other_actions_still_reach_the_runner(event, monkeypatch):
    monkeypatch.setattr(vectors, "handle", lambda event, context: pytest.fail("vectors"))
    monkeypatch.setattr(migrator, "handle", lambda event, context: "runner")
    assert invoke(event) == "runner"


# --- embed-missing (spec 10 §Behaviour 4) -------------------------------------------------------------------------


def test_embed_missing_embeds_each_row_with_one_call_and_counts(monkeypatch, bedrock, capsys):
    rows = [user(1), user(2), user(3, embedding="[already]"),
            user(4, gender=None, birthdate=None, country=None, height_cm=None, weight_kg=None)]
    database = use_db(monkeypatch, VectorDb(rows))

    result = invoke({"action": "embed-missing"})

    assert result == {"embedded": 2, "skipped": 1, "failed": 0, "remaining": 0, "stopped": "done"}
    assert len(bedrock.calls) == 2
    assert database.users[str(uuid.UUID(int=1))]["embedding"] == embeddings.to_vector_literal(unit_vector())
    assert database.users[str(uuid.UUID(int=3))]["embedding"] == "[already]"
    assert database.users[str(uuid.UUID(int=4))]["embedding"] is None  # skipped, not counted in remaining
    assert database.connects == [{"timeout": vectors.DB_TIMEOUT_S}]
    assert vectors.DB_TIMEOUT_S < 60
    assert database.closed
    line = log_line(capsys)
    assert {k: line[k] for k in ("level", "message", "function", "awsRequestId", "action", "embedded", "skipped",
                                  "failed", "remaining", "stopped", "bedrockCalls", "outcome")} == {
        "level": "INFO", "message": "embed-missing completed", "function": "aws-challenge-sync",
        "awsRequestId": "req-vec", "action": "embed-missing", "embedded": 2, "skipped": 1, "failed": 0,
        "remaining": 0, "stopped": "done", "bedrockCalls": 2, "outcome": "success",
    }
    assert isinstance(line["bedrockMs"], int) and isinstance(line["durationMs"], int)
    assert "errorClass" not in line


def test_embed_missing_sends_the_profile_text_and_the_vector_as_a_parameter(monkeypatch, bedrock):
    database = use_db(monkeypatch, VectorDb([user(1, birthdate=date(1985, 3, 3), weight_kg=70)]))
    invoke({"action": "embed-missing"})
    assert json.loads(bedrock.calls[0]["body"])["inputText"] == (
        "gender: female; birth year: 1985; country: Austria; height: 170 cm; weight: 70 kg")
    index = database.statements.index(vectors.SQL_UPDATE_EMBEDDING)
    assert database.params[index] == {"embedding": embeddings.to_vector_literal(unit_vector()),
                                      "id": str(uuid.UUID(int=1))}
    assert "[" not in vectors.SQL_UPDATE_EMBEDDING
    assert "AND embedding IS NULL" in vectors.SQL_UPDATE_EMBEDDING  # a newer vector from an upsert is kept
    assert "updated_at" not in vectors.SQL_UPDATE_EMBEDDING


def test_embed_missing_with_nothing_to_do_makes_no_bedrock_call(monkeypatch, bedrock, capsys):
    use_db(monkeypatch, VectorDb([user(1, embedding="[x]")]))
    assert invoke({"action": "embed-missing"}) == {
        "embedded": 0, "skipped": 0, "failed": 0, "remaining": 0, "stopped": "done"}
    assert bedrock.calls == []


def test_bad_response_counts_failed_and_the_run_continues(monkeypatch, capsys):
    stub = install(monkeypatch, StubBedrock(outcomes=[[0.0] * 1024]))
    database = use_db(monkeypatch, VectorDb([user(1), user(2)]))

    result = invoke({"action": "embed-missing"})

    assert result == {"embedded": 1, "skipped": 0, "failed": 1, "remaining": 1, "stopped": "done"}
    assert len(stub.calls) == 2
    assert database.users[str(uuid.UUID(int=1))]["embedding"] is None
    assert "errorClass" not in log_line(capsys)


@pytest.mark.parametrize(
    "exception, error_class",
    [
        (ConnectTimeoutError(endpoint_url="https://bedrock-runtime.eu-west-1.amazonaws.com"), "UNREACHABLE"),
        (EndpointConnectionError(endpoint_url="https://bedrock-runtime.eu-west-1.amazonaws.com"), "UNREACHABLE"),
        (ReadTimeoutError(endpoint_url="https://x"), "TIMEOUT"),
        (ClientError({"Error": {"Code": "ThrottlingException", "Message": "x"}}, "InvokeModel"),
         "ThrottlingException"),
    ],
)
def test_other_bedrock_error_stops_after_one_call(exception, error_class, monkeypatch, capsys):
    stub = install(monkeypatch, StubBedrock(outcomes=[exception]))
    use_db(monkeypatch, VectorDb([user(1), user(2), user(3)]))

    result = invoke({"action": "embed-missing"})  # never a function error

    assert result == {"embedded": 0, "skipped": 0, "failed": 1, "remaining": 3,
                      "stopped": f"bedrock_error: {error_class}"}
    assert len(stub.calls) == 1
    line = log_line(capsys)
    assert (line["level"], line["outcome"], line["errorClass"]) == ("WARNING", "success", error_class)
    assert line["bedrockCalls"] == 1


def test_time_budget_stops_before_the_next_call(monkeypatch, bedrock):
    use_db(monkeypatch, VectorDb([user(1), user(2), user(3)]))
    context = Context(remaining_ms=[40_000, 10_000, 9_999])

    result = invoke({"action": "embed-missing"}, context)

    assert result == {"embedded": 2, "skipped": 0, "failed": 0, "remaining": 1, "stopped": "time_budget"}
    assert len(bedrock.calls) == 2
    assert vectors.TIME_BUDGET_MS == 10_000


def test_rows_are_selected_in_id_order_with_a_limit():
    assert vectors.SQL_SELECT_MISSING.endswith("WHERE embedding IS NULL ORDER BY id LIMIT 1000")


@pytest.mark.parametrize("event", [{"action": "embed-missing", "limit": 5}, {"action": "embed-missing", "x": None}])
def test_embed_missing_bad_request(event, no_connect, bedrock, capsys):
    with pytest.raises(vectors.VectorError, match="^EMBED_BAD_REQUEST$"):
        invoke(event)
    assert bedrock.calls == []
    line = log_line(capsys)
    assert (line["outcome"], line["message"], line["errorClass"]) == ("failure", "EMBED_BAD_REQUEST", "VectorError")


@pytest.mark.parametrize(
    "error, message",
    [
        (pg8000.native.DatabaseError({"S": "ERROR", "C": "42703", "M": "column embedding does not exist"}),
         "EMBED_FAILED: 42703"),
        (pg8000.native.InterfaceError("network error"), "EMBED_FAILED: UNKNOWN"),
        (TimeoutError("timed out"), "EMBED_FAILED: UNKNOWN"),
    ],
)
def test_embed_missing_db_error(error, message, monkeypatch, bedrock, capsys):
    database = use_db(monkeypatch, VectorDb([user(1)], error_on=vectors.SQL_SELECT_MISSING, error=error))
    with pytest.raises(vectors.VectorError) as raised:
        invoke({"action": "embed-missing"})
    assert str(raised.value) == message
    assert raised.value.__cause__ is error
    assert database.closed
    line = log_line(capsys)
    assert (line["message"], line["errorClass"], line["level"]) == (message, type(error).__name__, "ERROR")


def test_connect_failure_is_db_connect_failed(monkeypatch, capsys):
    def connect(**kwargs):
        raise db.DbConnectError() from KeyError("DB_PROXY_ENDPOINT")

    monkeypatch.setattr(db, "connect", connect)
    with pytest.raises(db.DbConnectError, match="^DB_CONNECT_FAILED$"):
        invoke({"action": "embed-missing"})
    line = log_line(capsys)
    assert (line["message"], line["errorClass"]) == ("DB_CONNECT_FAILED", "KeyError")


def test_embed_missing_log_has_no_text_vector_or_values(monkeypatch, capsys):
    install(monkeypatch, StubBedrock(default=[0.123456789] * 1024))
    use_db(monkeypatch, VectorDb([user(1)]))
    invoke({"action": "embed-missing"})
    text = json.dumps(log_line(capsys))
    for part in ("0.031", "gender", "Austria", "170", "birth", "real1@", str(uuid.UUID(int=1))):
        assert part not in text


# --- seed (spec 11) -----------------------------------------------------------------------------------------------

NOW = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)


def test_generator_is_deterministic_and_independent_of_count():
    assert vectors.seed_user(7, NOW) == vectors.seed_user(7, NOW)
    first = [vectors.seed_user(k, NOW) for k in range(1, 11)]
    again = [vectors.seed_user(k, NOW) for k in range(1, 11)]
    assert first == again
    assert len({u["id"] for u in first}) == 10


def test_generator_ids_and_emails():
    u = vectors.seed_user(42, NOW)
    assert u["id"] == str(uuid.uuid5(vectors.SEED_NAMESPACE, "seed-42"))
    assert u["email"] == "seed-0042@seed.invalid"
    assert vectors.seed_user(1000, NOW)["email"] == "seed-1000@seed.invalid"
    assert u["confirmed_at"] == NOW


def test_generator_value_ranges_over_1000_users():
    users = [vectors.seed_user(k, NOW) for k in range(1, 1001)]
    assert len({u["id"] for u in users}) == 1000
    assert len({u["email"] for u in users}) == 1000
    for u in users:
        assert re.fullmatch(r"seed-[0-9]{4}@seed\.invalid", u["email"])
        assert u["gender"] in ("female", "male")
        assert date(1950, 1, 1) <= u["birthdate"] <= date(2007, 12, 31)
        assert 140 <= u["height_cm"] <= 210
        assert 40 <= u["weight_kg"] <= 150
        assert u["country"] in vectors.COUNTRIES
        assert u["given_name"] in vectors.GIVEN_NAMES and u["family_name"] in vectors.FAMILY_NAMES
        assert "embedding" not in u
    assert {u["gender"] for u in users} == {"female", "male"}


def test_seed_inserts_in_one_transaction_and_is_idempotent(monkeypatch, bedrock, capsys):
    database = use_db(monkeypatch, VectorDb([user(1)]))

    assert invoke({"action": "seed", "count": 250}) == {"inserted": 250, "seeded": 250}
    assert database.commits == 1
    inserts = [s for s in database.statements if s.startswith("INSERT INTO users")]
    assert len(inserts) == 3  # batches of 100
    assert all(row["embedding"] is None for k, row in database.users.items() if k != str(uuid.UUID(int=1)))
    assert bedrock.calls == []
    line = log_line(capsys)
    assert (line["action"], line["inserted"], line["seeded"], line["outcome"]) == ("seed", 250, 250, "success")

    assert invoke({"action": "seed", "count": 250}) == {"inserted": 0, "seeded": 250}
    assert invoke({"action": "seed", "count": 100}) == {"inserted": 0, "seeded": 250}  # smaller: deletes nothing
    assert invoke({"action": "seed", "count": 1000}) == {"inserted": 750, "seeded": 1000}
    assert len(database.users) == 1001


def test_seed_sql_holds_no_values():
    sql = vectors.seed_insert_sql(2)
    assert sql.startswith("INSERT INTO users (id, email, given_name, family_name, gender, birthdate, country, "
                          "height_cm, weight_kg, confirmed_at) VALUES (CAST(:id_0 AS uuid), CAST(:email_0 AS text)")
    assert sql.endswith("CAST(:confirmed_at_1 AS timestamptz)) ON CONFLICT (id) DO NOTHING RETURNING 1")
    assert "@" not in sql and "seed-" not in sql


def test_seed_db_error_rolls_back(monkeypatch, capsys):
    error = pg8000.native.DatabaseError({"S": "ERROR", "C": "23505", "M": "dup"})
    database = use_db(monkeypatch, VectorDb(error_on="INSERT INTO users", error=error))
    with pytest.raises(vectors.VectorError, match="^SEED_FAILED: 23505$"):
        invoke({"action": "seed", "count": 5})
    assert database.rollbacks == 1 and database.commits == 0 and database.users == {}
    assert log_line(capsys)["message"] == "SEED_FAILED: 23505"


@pytest.mark.parametrize(
    "event",
    [
        {"action": "seed", "count": 0},
        {"action": "seed", "count": 1001},
        {"action": "seed", "count": "10"},
        {"action": "seed", "count": 10.0},
        {"action": "seed", "count": True},
        {"action": "seed", "count": None},
        {"action": "seed"},
        {"action": "seed", "count": 10, "extra": 1},
    ],
    ids=["zero", "1001", "string", "float", "bool", "null", "missing", "extra-key"],
)
def test_seed_bad_request(event, no_connect, capsys):
    with pytest.raises(vectors.VectorError, match="^SEED_BAD_REQUEST$"):
        invoke(event)
    assert log_line(capsys)["message"] == "SEED_BAD_REQUEST"


# --- similar (spec 11) --------------------------------------------------------------------------------------------

TARGET = str(uuid.UUID(int=1))


def similar_db(**kwargs):
    rows = [user(1, embedding="[1,0]"), user(2, embedding="[0.9,0.1]"), user(3)]
    neighbours = [(uuid.UUID(int=1), 0.0), (uuid.UUID(int=2), 0.14), (uuid.UUID(int=3), None)]
    return VectorDb(rows, similar_rows=neighbours, **kwargs)


def test_similar_returns_items_counts_and_both_plans(monkeypatch, bedrock, capsys):
    database = use_db(monkeypatch, similar_db())

    result = invoke({"action": "similar", "userId": TARGET.upper()})

    assert result == {
        "rows": 3,
        "withEmbedding": 2,
        "items": [{"id": TARGET, "distance": 0.0}, {"id": str(uuid.UUID(int=2)), "distance": 0.14}],
        "default": {"scan": "Seq Scan", "executionMs": 3.25},
        "indexForced": {"scan": "Index Scan using users_embedding_hnsw_idx", "executionMs": 0.75},
    }
    assert bedrock.calls == []
    assert database.connects == [{"timeout": vectors.DB_TIMEOUT_S}]
    # the stored vector is the parameter of every query
    for sql, params in zip(database.statements, database.params):
        if sql in (vectors.SQL_SIMILAR, vectors.SQL_EXPLAIN_SIMILAR):
            assert params == {"q": "[1,0]"}
    assert database.params[0] == {"id": TARGET}
    assert database.closed

    line = log_line(capsys)
    assert {k: line[k] for k in ("action", "rows", "withEmbedding", "defaultScan", "defaultMs", "indexScan",
                                  "indexMs", "outcome")} == {
        "action": "similar", "rows": 3, "withEmbedding": 2, "defaultScan": "Seq Scan", "defaultMs": 3.25,
        "indexScan": "Index Scan using users_embedding_hnsw_idx", "indexMs": 0.75, "outcome": "success",
    }
    text = json.dumps(line)
    assert TARGET not in text and str(uuid.UUID(int=2)) not in text and "[1,0]" not in text


def test_set_local_only_inside_a_rolled_back_transaction(monkeypatch):
    database = use_db(monkeypatch, similar_db())
    invoke({"action": "similar", "userId": TARGET})

    s = database.statements
    begin, force, rollback = s.index("BEGIN"), s.index(vectors.SQL_FORCE_INDEX), s.index("ROLLBACK")
    explains = [i for i, sql in enumerate(s) if sql == vectors.SQL_EXPLAIN_SIMILAR]
    assert begin < explains[0] < force < explains[1] < rollback == len(s) - 1
    assert "COMMIT" not in s
    assert vectors.SQL_FORCE_INDEX == "SET LOCAL enable_seqscan = off"


def test_query_text_is_the_curriculum_query_with_a_parameter():
    assert vectors.SQL_SIMILAR == (
        "SELECT id, embedding <-> CAST(:q AS vector) AS distance FROM users "
        "ORDER BY embedding <-> CAST(:q AS vector) LIMIT 5")
    assert vectors.SQL_EXPLAIN_SIMILAR == "EXPLAIN (ANALYZE, FORMAT JSON) " + vectors.SQL_SIMILAR


@pytest.mark.parametrize("rows", [[], [[None]]], ids=["unknown-user", "null-embedding"])
def test_similar_not_found(rows, monkeypatch, capsys):
    database = VectorDb()
    database.run = lambda sql, **params: rows if sql == vectors.SQL_SELECT_VECTOR else pytest.fail(sql)
    database.close = lambda: None
    use_db(monkeypatch, database)
    with pytest.raises(vectors.VectorError, match="^SIMILAR_NOT_FOUND$"):
        invoke({"action": "similar", "userId": TARGET})
    line = log_line(capsys)
    assert (line["message"], line["outcome"]) == ("SIMILAR_NOT_FOUND", "failure")
    assert TARGET not in json.dumps(line)


def test_similar_db_error_rolls_back(monkeypatch, capsys):
    error = pg8000.native.DatabaseError({"S": "ERROR", "C": "57014", "M": "canceling statement"})
    database = use_db(monkeypatch, similar_db(error_on=vectors.SQL_FORCE_INDEX, error=error))
    with pytest.raises(vectors.VectorError, match="^SIMILAR_FAILED: 57014$"):
        invoke({"action": "similar", "userId": TARGET})
    assert database.rollbacks == 1 and database.tx is None


@pytest.mark.parametrize(
    "event",
    [
        {"action": "similar"},
        {"action": "similar", "userId": "not-a-uuid"},
        {"action": "similar", "userId": TARGET + "0"},
        {"action": "similar", "userId": 1},
        {"action": "similar", "userId": TARGET, "extra": True},
    ],
)
def test_similar_bad_request(event, no_connect, capsys):
    with pytest.raises(vectors.VectorError, match="^SIMILAR_BAD_REQUEST$"):
        invoke(event)
    line = log_line(capsys)
    assert line["message"] == "SIMILAR_BAD_REQUEST"
    assert "not-a-uuid" not in json.dumps(line)


# --- plan parsing -------------------------------------------------------------------------------------------------


def test_parse_plan_from_list_and_text():
    assert vectors.parse_plan(INDEX_PLAN) == {"scan": "Index Scan using users_embedding_hnsw_idx",
                                              "executionMs": 0.75}
    assert vectors.parse_plan(json.dumps(SEQ_PLAN)) == {"scan": "Seq Scan", "executionMs": 3.25}


def test_parse_plan_without_scan_node():
    plan = [{"Plan": {"Node Type": "Result"}, "Execution Time": 0.01}]
    assert vectors.parse_plan(plan) == {"scan": "unknown", "executionMs": 0.01}


def test_parse_plan_index_only_scan():
    plan = [{"Plan": {"Node Type": "Limit", "Plans": [
        {"Node Type": "Index Only Scan", "Index Name": "users_pkey"}]}, "Execution Time": 1}]
    assert vectors.parse_plan(plan)["scan"] == "Index Only Scan using users_pkey"
