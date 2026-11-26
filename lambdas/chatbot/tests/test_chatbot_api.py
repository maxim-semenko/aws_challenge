"""POST /chat handler: check order, body, mode, both paths, error mapping, response and log line (AC-12.1)."""

import base64
import json
import uuid
from datetime import date

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError, ReadTimeoutError

import db
import embeddings
import lambda_function as lf
import llm
from bedrock_stub import StubBedrock, install, unit_vector
from doubles import FakeConnection, StubConverse, db_error, install_converse

SUB = "8f1c2a3b-0000-4000-8000-000000000001"
QUERY_SECRET = "which users are similar to gender: female; country: Poland"


class Context:
    function_name = "aws-challenge-chatbot"
    aws_request_id = "req-1"


def event(body=None, *, groups="[admin]", token_use="access", route="POST /chat", claims=True, raw_query="",
          base64_body=False, **extra):
    jwt_claims = {"sub": SUB, "token_use": token_use, "exp": "1893456000", "cognito:groups": groups}
    if groups is None:
        del jwt_claims["cognito:groups"]
    text = body if isinstance(body, str) or body is None else json.dumps(body)
    if base64_body and text is not None:
        text = base64.b64encode(text.encode("utf-8")).decode("ascii")
    result = {
        "version": "2.0",
        "routeKey": route,
        "rawPath": "/chat",
        "rawQueryString": raw_query,
        "headers": {"authorization": "Bearer secret-token-value"},
        "requestContext": {"requestId": "api-1", "authorizer": {"jwt": {"claims": jwt_claims}} if claims else {}},
        "body": text,
        "isBase64Encoded": base64_body,
    }
    result.update(extra)
    return result


@pytest.fixture
def calls():
    return []


@pytest.fixture
def bedrock(monkeypatch, calls):
    return install(monkeypatch, StubBedrock(default=unit_vector(4), log=calls))


@pytest.fixture
def converse(monkeypatch, calls):
    return install_converse(monkeypatch, StubConverse(log=calls))


@pytest.fixture
def database(monkeypatch, calls):
    """db.connect replaced; `holder.conn` is handed out, `holder.error` raised instead when set."""

    class Holder:
        conn = FakeConnection(log=calls)
        error = None
        connects = 0

    def fake_connect(timeout=db.DEFAULT_TIMEOUT_S):
        Holder.connects += 1
        calls.append("connect")
        if Holder.error is not None:
            raise Holder.error
        Holder.conn.log = calls
        return Holder.conn

    monkeypatch.setattr(db, "connect", fake_connect)
    return Holder


@pytest.fixture(autouse=True)
def doubles(bedrock, converse, database):
    """No test reaches Bedrock or a database."""


def invoke(evt, capsys):
    response = lf.lambda_handler(evt, Context())
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert len(lines) == 1, lines
    return response, json.loads(response["body"]), json.loads(lines[0])


def assert_problem(response, body, status, detail=None):
    assert response["statusCode"] == status
    assert response["headers"] == {"Content-Type": "application/problem+json", "Cache-Control": "no-store"}
    assert set(body) == {"type", "title", "status", "detail"}
    assert body["type"] == "about:blank" and body["status"] == status
    if detail is not None:
        assert body["detail"] == detail


# --- check order: 401 -> 404 -> 403 -> 400, no Bedrock or DB call before the body is valid -----------------------------


@pytest.mark.parametrize(
    ("evt", "status"),
    [
        (event({"query": "x"}, claims=False), 401),
        (event({"query": "x"}, token_use="id"), 401),
        (event({"query": "x"}, token_use="id", route="GET /admin", groups="[user]"), 401),
        (event({"query": "x"}, route="GET /admin"), 404),
        (event({"query": "x"}, route="GET /admin", groups="[user]"), 404),
        (event({"query": "x"}, groups="[user]"), 403),
        (event({"query": "x"}, groups=None), 403),
        (event({"query": "x"}, groups="[Admin]"), 403),
        (event("not json", groups="[user]"), 403),
        (event("not json"), 400),
    ],
)
def test_check_order_and_no_call_before_a_valid_body(evt, status, capsys, calls):
    response, body, log = invoke(evt, capsys)
    assert_problem(response, body, status)
    assert calls == []
    assert log["status"] == status and log["mode"] is None and log["queryHash"] is None


def test_problem_texts(capsys):
    _, body, _ = invoke(event({"query": "x"}, token_use="id"), capsys)
    assert body["detail"] == "A valid access token is required." and body["title"] == "Unauthorized"
    _, body, _ = invoke(event({"query": "x"}, groups="[user]"), capsys)
    assert body["detail"] == "Membership in the group admin is required." and body["title"] == "Forbidden"
    _, body, _ = invoke(event({"query": "x"}, route="GET /api/me"), capsys)
    assert body["detail"] == "The route is not served by this function."


@pytest.mark.parametrize(
    ("evt", "detail"),
    [
        (event({"query": ""}), "query must be 1 to 500 characters"),
        (event({"query": "   "}), "query must be 1 to 500 characters"),
        (event({"query": "x" * 501}), "query must be 1 to 500 characters"),
        (event({"query": 5}), "query must be 1 to 500 characters"),
        (event({"query": None}), "query must be 1 to 500 characters"),
        (event({}), "query must be 1 to 500 characters"),
        (event({"query": "x", "mode": "sql"}), "unknown field"),
        (event([]), "body must be a JSON object"),
        (event("[]"), "body must be a JSON object"),
        (event("\"text\""), "body must be a JSON object"),
        (event("{invalid"), "body must be a JSON object"),
        (event(None), "body must be a JSON object"),
        (event({"query": "x"}, raw_query="a=1"), "query parameters are not accepted"),
        (event({"query": "x"}, queryStringParameters={"a": "1"}), "query parameters are not accepted"),
        (event({"query": "x" * 4100}), "body must be at most 4096 bytes"),
        (event("%%%not-base64", base64_body=False, isBase64Encoded=True), "body must be a JSON object"),
        (event({"query": "which users are similar to"}), "query must name what the users are similar to"),
        (event({"query": "  users similar to :  "}), "query must name what the users are similar to"),
    ],
)
def test_body_errors_are_400_without_echo_and_without_calls(evt, detail, capsys, calls):
    response, body, log = invoke(evt, capsys)
    assert_problem(response, body, 400, detail)
    assert calls == []
    assert log["level"] == "WARNING" and log["outcome"] == "client_error"


def test_500_characters_after_trimming_are_accepted(capsys):
    response, body, _ = invoke(event({"query": "  " + "a" * 500 + "  "}), capsys)
    assert response["statusCode"] == 200 and body["mode"] == "vector"


def test_base64_body_is_decoded(capsys, bedrock):
    response, body, _ = invoke(event({"query": "gender: female"}, base64_body=True), capsys)
    assert response["statusCode"] == 200
    assert json.loads(bedrock.calls[0]["body"])["inputText"] == "gender: female"


# --- mode and prefix ------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("query", "mode"),
    [("SQL", "sql"), ("Sql: how many users", "sql"), ("my sql question", "sql"), ("how many? (sql)", "sql"),
     ("mysql", "vector"), ("sqlite users", "vector"), ("my_sql", "vector"), ("gender: female", "vector")],
)
def test_mode_is_the_whole_word_sql(query, mode):
    assert lf.mode_of(query) == mode


@pytest.mark.parametrize(
    ("query", "text"),
    [
        ("which users are similar to gender: female", "gender: female"),
        ("Which users are similar to: country: Poland", "country: Poland"),
        ("what user is similar to - height: 170 cm", "height: 170 cm"),
        ("find people similar to weight: 60 kg", "weight: 60 kg"),
        ("show me users similar to birth year: 1990", "birth year: 1990"),
        ("users similar to x", "x"),
        ("gender: female; country: Poland", "gender: female; country: Poland"),
        ("tell me which users are similar to x", "tell me which users are similar to x"),
    ],
)
def test_similarity_prefix_is_stripped(query, text):
    assert lf.strip_similarity_prefix(query) == text


# --- vector path ----------------------------------------------------------------------------------------------------


def vector_row(i, distance):
    return (uuid.UUID(int=i), f"seed-{i:04d}@seed.invalid", "Alex", "Muster", "female", date(1990, 5, 17), "Poland",
            170, 60, distance)


def test_vector_path_response_and_log(capsys, bedrock, converse, database, calls):
    database.conn = FakeConnection(vector_rows=[vector_row(1, 0.0), vector_row(2, 0.25), vector_row(3, None)])
    response, body, log = invoke(event({"query": "  " + QUERY_SECRET + " "}), capsys)

    assert response["statusCode"] == 200
    assert response["headers"] == {"Content-Type": "application/json", "Cache-Control": "no-store"}
    assert set(body) == {"mode", "columns", "rows", "rowCount", "truncated", "sql", "timings", "tokens", "modelId"}
    assert body["mode"] == "vector" and body["sql"] is None and body["truncated"] is False
    assert body["columns"] == ["id", "email", "givenName", "familyName", "gender", "birthdate", "country",
                               "heightCm", "weightKg", "distance"]
    assert body["rows"] == [
        [str(uuid.UUID(int=1)), "seed-0001@seed.invalid", "Alex", "Muster", "female", "1990-05-17", "Poland", 170,
         60, 0.0],
        [str(uuid.UUID(int=2)), "seed-0002@seed.invalid", "Alex", "Muster", "female", "1990-05-17", "Poland", 170,
         60, 0.25],
    ]
    assert body["rowCount"] == 2
    assert body["tokens"] == {"input": 7, "output": 0}
    assert body["modelId"] == "amazon.titan-embed-text-v2:0"
    timings = body["timings"]
    assert set(timings) == {"embedMs", "llmMs", "dbMs", "totalMs"} and timings["llmMs"] is None
    assert all(isinstance(timings[k], int) for k in ("embedMs", "dbMs", "totalMs"))

    # Titan request through the shared helper, with the prefix stripped; Bedrock before the DB; no Converse
    (call,) = bedrock.calls
    assert json.loads(call["body"]) == {"inputText": "gender: female; country: Poland", "dimensions": 1024,
                                        "normalize": True, "embeddingTypes": ["float"]}
    assert converse.calls == []
    assert calls[0] == "bedrock" and calls[1] == "connect"
    assert database.conn.sql[0] == "BEGIN READ ONLY" and database.conn.sql[-1] == "ROLLBACK"
    assert database.conn.closed

    assert log["mode"] == "vector" and log["status"] == 200 and log["outcome"] == "success"
    assert log["queryLength"] == len(QUERY_SECRET) and log["queryHash"] == lf.short_hash(QUERY_SECRET)
    assert log["inputTokens"] == 7 and log["outputTokens"] == 0 and log["rowCount"] == 2
    assert log["sqlHash"] is None and log["guardResult"] is None and log["llmMs"] is None


def test_aggregate_with_no_rows_is_one_row_zero(capsys, converse, database):
    database.conn = FakeConnection(rows=[(0,)], columns=("count",))
    response, body, _ = invoke(event({"query": "sql how many"}), capsys)
    assert response["statusCode"] == 200 and body["rows"] == [[0]] and body["rowCount"] == 1


def test_fewer_than_five_vector_rows(capsys, database):
    database.conn = FakeConnection(vector_rows=[vector_row(1, 0.1)])
    _, body, _ = invoke(event({"query": "gender: male"}), capsys)
    assert body["rowCount"] == 1


# --- SQL path -------------------------------------------------------------------------------------------------------

STAT_QUERY = "sql how many users aged 25 to 35 live in Poland and weigh more than 70 kg"
STAT_SQL = ("SELECT count(*) FROM users WHERE country IN ('PL','Poland') AND weight_kg > 70 "
            "AND date_part('year', age(birthdate)) BETWEEN 25 AND 35")


def test_sql_path_response_and_log(capsys, bedrock, converse, database, calls):
    converse.default = "```sql\n" + STAT_SQL + ";\n```"
    database.conn = FakeConnection(rows=[(4,)], columns=("count",))
    response, body, log = invoke(event({"query": STAT_QUERY}), capsys)

    assert response["statusCode"] == 200
    executed = ("SELECT COUNT(*) FROM users WHERE country IN ('PL', 'Poland') AND weight_kg > 70 "
                "AND DATE_PART('year', AGE(birthdate)) BETWEEN 25 AND 35 LIMIT 101")
    assert body == {
        "mode": "sql",
        "columns": ["count"],
        "rows": [[4]],
        "rowCount": 1,
        "truncated": False,
        "sql": executed,
        "timings": body["timings"],
        "tokens": {"input": 700, "output": 40},
        "modelId": "eu.amazon.nova-micro-v1:0",
    }
    assert body["timings"]["embedMs"] is None and isinstance(body["timings"]["llmMs"], int)
    # the executed text is the guard's rendering, inside READ ONLY + statement_timeout + ROLLBACK
    assert database.conn.statements == [
        ("run", "BEGIN READ ONLY", {}),
        ("run", "SET LOCAL statement_timeout = '4s'", {}),
        ("execute_unnamed", executed, {}),
        ("run", "ROLLBACK", {}),
    ]
    (call,) = converse.calls
    assert call["messages"][0]["content"][0]["text"] == STAT_QUERY
    assert bedrock.calls == []
    assert calls.index("converse") < calls.index("connect")

    assert log["mode"] == "sql" and log["guardResult"] == "ACCEPTED" and log["sqlHash"] == lf.short_hash(executed)
    assert log["inputTokens"] == 700 and log["outputTokens"] == 40 and log["modelId"] == "eu.amazon.nova-micro-v1:0"
    assert log["embedMs"] is None and isinstance(log["llmMs"], int) and isinstance(log["dbMs"], int)


def test_truncated_result(capsys, converse, database):
    converse.default = "SELECT email FROM users"
    database.conn = FakeConnection(rows=[(f"u{i}",) for i in range(101)], columns=("email",))
    _, body, log = invoke(event({"query": "sql list all e-mails"}), capsys)
    assert body["rowCount"] == 100 and body["truncated"] is True and len(body["rows"]) == 100
    assert body["sql"].endswith("LIMIT 101")
    assert log["rowCount"] == 100 and log["truncated"] is True


@pytest.mark.parametrize(
    ("answer", "code"),
    [("NONE", "NO_QUERY"), ("I am sorry, I cannot do that.", "PARSE_ERROR"), ("DELETE FROM users", "NOT_SELECT"),
     ("SELECT embedding FROM users", "COLUMN_NOT_ALLOWED"), ("SELECT 1; DROP TABLE users", "MULTIPLE_STATEMENTS")],
)
def test_guard_rejection_is_400_rephrase_without_db_call(answer, code, capsys, converse, database):
    converse.default = answer
    response, body, log = invoke(event({"query": "sql do something"}), capsys)
    assert_problem(response, body, 400, "The question could not be turned into a safe query. Rephrase it.")
    assert database.connects == 0
    assert log["guardResult"] == code and log["errorClass"] is None and log["dbMs"] is None
    assert log["inputTokens"] == 700


@pytest.mark.parametrize(("code", "name"), [("42703", "DatabaseError"), ("57014", "DatabaseError"),
                                            ("25006", "DatabaseError")])
def test_sql_error_or_timeout_or_write_is_400_with_db_class(code, name, capsys, database):
    database.conn = FakeConnection(statement_error=db_error(code))
    response, body, log = invoke(event({"query": "sql how many"}), capsys)
    assert_problem(response, body, 400, "The question could not be turned into a safe query. Rephrase it.")
    assert log["errorClass"] == name and log["guardResult"] == "ACCEPTED"
    assert database.conn.sql[-1] == "ROLLBACK" and database.conn.closed
    assert "42703" not in json.dumps(body)


# --- Bedrock and DB failures ----------------------------------------------------------------------------------------


def client_error(code, operation):
    return ClientError({"Error": {"Code": code, "Message": "AWS detail person@example.com"}}, operation)


@pytest.mark.parametrize(
    ("exception", "status", "error_class"),
    [
        (EndpointConnectionError(endpoint_url="https://bedrock-runtime.eu-west-1.amazonaws.com"), 502, "UNREACHABLE"),
        (ReadTimeoutError(endpoint_url="https://bedrock-runtime.eu-west-1.amazonaws.com"), 502, "TIMEOUT"),
        (client_error("AccessDeniedException", "x"), 502, "AccessDeniedException"),
        (client_error("ValidationException", "x"), 502, "ValidationException"),
        (client_error("ResourceNotFoundException", "x"), 502, "ResourceNotFoundException"),
        (client_error("ThrottlingException", "x"), 429, "ThrottlingException"),
    ],
)
@pytest.mark.parametrize("query", ["gender: female", "sql how many"])
def test_bedrock_failures(exception, status, error_class, query, capsys, bedrock, converse, database):
    bedrock.outcomes = [exception]
    converse.outcomes = [exception]
    response, body, log = invoke(event({"query": query}), capsys)
    detail = "The AI service is busy. Try again shortly." if status == 429 else "The AI service is not available."
    assert_problem(response, body, status, detail)
    assert database.connects == 0 and log["dbMs"] is None
    assert log["errorClass"] == error_class and log["status"] == status
    assert log["level"] == ("WARNING" if status == 429 else "ERROR")
    assert log["outcome"] == ("client_error" if status == 429 else "failure")


def test_bad_titan_response_is_502(capsys, bedrock):
    bedrock.outcomes = [b"not json"]
    response, _, log = invoke(event({"query": "gender: female"}), capsys)
    assert response["statusCode"] == 502 and log["errorClass"] == "BAD_RESPONSE"


def test_db_connect_failure_is_500_with_cause_class(capsys, database):
    error = db.DbConnectError()
    error.__cause__ = TimeoutError("proxy")
    database.error = error
    response, body, log = invoke(event({"query": "gender: female"}), capsys)
    assert_problem(response, body, 500, "The request could not be completed.")
    assert log["message"] == "DB_CONNECT_FAILED" and log["errorClass"] == "TimeoutError"
    assert log["level"] == "ERROR" and log["outcome"] == "failure"


def test_lost_connection_in_sql_mode_is_500(capsys, database):
    database.conn = FakeConnection(statement_error=OSError("reset"))
    response, _, log = invoke(event({"query": "sql how many"}), capsys)
    assert response["statusCode"] == 500 and log["errorClass"] == "OSError" and log["message"] == "INTERNAL_ERROR"


def test_vector_query_failure_is_500(capsys, database):
    database.conn = FakeConnection(begin_error=db_error("42883"))
    response, _, log = invoke(event({"query": "gender: female"}), capsys)
    assert response["statusCode"] == 500 and log["errorClass"] == "DatabaseError"


# --- log line -------------------------------------------------------------------------------------------------------

LOG_KEYS = {
    "level", "message", "function", "awsRequestId", "apiRequestId", "userSub", "route", "status", "outcome",
    "durationMs", "mode", "queryLength", "queryHash", "embedMs", "llmMs", "dbMs", "inputTokens", "outputTokens",
    "modelId", "rowCount", "truncated", "sqlHash", "guardResult", "errorClass",
}


@pytest.mark.parametrize("query", [QUERY_SECRET, "sql list the e-mail of user secret-person@example.com"])
def test_log_line_has_exactly_the_fields_and_no_forbidden_values(query, capsys, converse, database):
    converse.default = "SELECT email FROM users WHERE email = 'secret-person@example.com'"
    database.conn = FakeConnection(vector_rows=[vector_row(1, 0.0)], rows=[("secret-person@example.com",)],
                                   columns=("email",))
    response, body, log = invoke(event({"query": query}), capsys)
    assert response["statusCode"] == 200
    assert set(log) == LOG_KEYS
    assert log["function"] == "aws-challenge-chatbot" and log["awsRequestId"] == "req-1"
    assert log["apiRequestId"] == "api-1" and log["userSub"] == SUB and log["route"] == "POST /chat"
    text = json.dumps(log)
    for forbidden in (query, "secret-token-value", "secret-person", "seed-0001", "Muster", "SELECT", "0.0,0.0"):
        assert forbidden not in text
    assert len(log["queryHash"]) == 16


def test_error_log_line_has_the_same_fields(capsys):
    _, _, log = invoke(event({"query": "x"}, token_use="id"), capsys)
    assert set(log) == LOG_KEYS and log["userSub"] == SUB and log["errorClass"] is None


def test_non_dict_event_is_401(capsys):
    response = lf.lambda_handler(None, Context())
    out = capsys.readouterr().out.strip()
    assert response["statusCode"] == 401 and json.loads(out)["route"] is None


def test_model_ids_are_code_constants():
    assert embeddings.MODEL_ID == "amazon.titan-embed-text-v2:0"
    assert llm.MODEL_ID == "eu.amazon.nova-micro-v1:0"
