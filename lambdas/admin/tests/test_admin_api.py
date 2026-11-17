"""Unit tests of aws-challenge-admin (spec 08 §Outputs, §Behaviour, §Edge Cases; AC-08.1). No AWS, no database."""

import json
import uuid
from datetime import date, datetime, timedelta, timezone

import pg8000.native
import pytest

import db
import lambda_function as lf

SUB = "8f1c2a3b-0000-4000-8000-000000000001"
EXP = 1_700_000_000  # 2023-11-14T22:13:20Z
TOKEN = "eyJraWQiOiJleGFtcGxlIn0.payload.signature"
EMAIL = "anna.karenina@example.com"


class Context:
    function_name = "aws-challenge-admin"
    aws_request_id = "req-123"


def claims(**overrides):
    """Claims as delivered by the HTTP API JWT authorizer in payload 2.0 (all values strings)."""
    base = {
        "sub": SUB,
        "token_use": "access",
        "username": "anna",
        "cognito:groups": "[admin]",
        "exp": str(EXP),
        "client_id": "exampleclientid",
        "scope": "aws.cognito.signin.user.admin",
    }
    base.update(overrides)
    return {name: value for name, value in base.items() if value is not None}


def event(route="GET /admin", query="", token_claims=None, with_claims=True):
    path = route.split(" ", 1)[1]
    request_context = {"requestId": "api-req-456", "routeKey": route, "http": {"method": "GET", "path": path}}
    if with_claims:
        request_context["authorizer"] = {"jwt": {"claims": token_claims or claims(), "scopes": None}}
    return {
        "version": "2.0",
        "routeKey": route,
        "rawPath": path,
        "rawQueryString": query,
        "headers": {"authorization": f"Bearer {TOKEN}"},
        "requestContext": request_context,
        "isBase64Encoded": False,
    }


def user_row(index, **overrides):
    row = {
        "id": uuid.UUID(int=index),
        "email": f"user{index}@example.com",
        "given_name": "Anna",
        "family_name": "Karenina",
        "gender": "female",
        "birthdate": date(1990, 5, 17),
        "country": "Austria",
        "height_cm": 170,
        "weight_kg": 62,
        "created_at": datetime(2026, 11, 16, 10, 0, 0, 123456, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 11, 16, 12, 30, 5, tzinfo=timezone.utc),
    }
    row.update(overrides)
    return [row[column.strip()] for column in lf.USER_COLUMNS.split(",")]


class FakeConnection:
    """pg8000.native.Connection double over a list of rows; ordering is the database's job (integration test)."""

    def __init__(self, rows=(), error=None):
        self.rows = list(rows)
        self.error = error
        self.calls = []
        self.closed = False

    def run(self, sql, **params):
        self.calls.append((sql, params))
        if self.error is not None:
            raise self.error
        if sql == lf.SQL_COUNT:
            assert params == {}
            return [[len(self.rows)]]
        assert sql in lf.SQL_PAGE.values(), f"unexpected statement: {sql}"
        assert set(params) == {"limit", "offset"}
        return self.rows[params["offset"]: params["offset"] + params["limit"]]

    def close(self):
        self.closed = True


@pytest.fixture
def database(monkeypatch):
    """Replaces db.connect; `database.conn` is the connection handed out, `database.connects` counts the calls."""

    class Database:
        conn = FakeConnection()
        connects = 0
        error = None

    def connect(**kwargs):
        Database.connects += 1
        if Database.error is not None:
            raise Database.error
        return Database.conn

    monkeypatch.setattr(db, "connect", connect)
    return Database


def invoke(evt, capsys):
    response = lf.lambda_handler(evt, Context())
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 1, "exactly one log line per request"
    return response, json.loads(lines[0]), lines[0]


def body(response):
    return json.loads(response["body"])


def assert_problem(response, status, title):
    assert response["statusCode"] == status
    assert response["headers"] == {"Content-Type": "application/problem+json", "Cache-Control": "no-store"}
    problem = body(response)
    assert problem["type"] == "about:blank"
    assert problem["title"] == title
    assert problem["status"] == status
    assert isinstance(problem["detail"], str) and problem["detail"]
    assert set(problem) == {"type", "title", "status", "detail"}
    return problem


# --- 401: claims and token_use ---------------------------------------------------------------------------------------


def test_route_key_is_get_admin():
    assert lf.ROUTE_USERS == "GET /admin"


def test_id_token_is_rejected_with_401_and_no_database_call(database, capsys):
    response, log, _ = invoke(event(token_claims=claims(token_use="id", aud="exampleclientid")), capsys)
    assert_problem(response, 401, "Unauthorized")
    assert database.connects == 0
    assert log["status"] == 401 and log["outcome"] == "client_error"


@pytest.mark.parametrize(
    "token_claims",
    [
        None,  # no authorizer block at all
        claims(token_use=None),
        claims(sub=None),
        claims(sub=""),
        claims(exp=None),
        claims(exp="soon"),
        claims(exp="-1"),
    ],
    ids=["no-claims", "no-token_use", "no-sub", "empty-sub", "no-exp", "bad-exp", "negative-exp"],
)
def test_missing_or_incomplete_claims_give_401(token_claims, database, capsys):
    evt = event(token_claims=token_claims, with_claims=token_claims is not None)
    response, _, _ = invoke(evt, capsys)
    assert_problem(response, 401, "Unauthorized")
    assert database.connects == 0


def test_claims_are_not_read_from_headers(database, capsys):
    evt = event(with_claims=False)
    evt["headers"]["x-claims"] = json.dumps(claims())
    response, _, _ = invoke(evt, capsys)
    assert response["statusCode"] == 401


def test_non_dict_event_gives_401(capsys):
    response, log, _ = invoke("not an event", capsys)
    assert_problem(response, 401, "Unauthorized")
    assert log["route"] is None and log["apiRequestId"] is None


# --- 404 -------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "route",
    [
        "GET /api/admin/users",  # removed 2026-11-17 (owner decision: only GET /admin and POST /chat)
        "GET /api/me",  # removed 2026-11-17 (the SPA reads the role from the token)
        "POST /admin",
        "GET /admin/users",
        "POST /chat",  # chatbot function, never this one
        "GET /api/admin/ping",
        "$default",
    ],
)
def test_unknown_route_gives_404(route, database, capsys):
    evt = event("GET /x")
    evt["routeKey"] = route
    response, log, _ = invoke(evt, capsys)
    assert_problem(response, 404, "Not Found")
    assert database.connects == 0
    assert log["route"] == route


def test_401_is_checked_before_the_route(capsys):
    evt = event("GET /x", token_claims=claims(token_use="id"))
    evt["routeKey"] = "GET /unknown"
    response, _, _ = invoke(evt, capsys)
    assert response["statusCode"] == 401


def test_numeric_exp_is_accepted(database, capsys):
    response, _, _ = invoke(event(token_claims=claims(exp=EXP)), capsys)
    assert response["statusCode"] == 200


# --- cognito:groups formats ------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected",
    [
        ("[admin]", ["admin"]),
        ("admin", ["admin"]),
        ("[admin user]", ["admin", "user"]),
        ('["admin","user"]', ["admin", "user"]),
        (["admin", "user"], ["admin", "user"]),
        ("[admin, user]", ["admin", "user"]),
        (" [ admin ] ", ["admin"]),
        ("[]", []),
        ("", []),
        (None, []),
        (42, []),
    ],
)
def test_group_claim_formats(value, expected):
    assert lf.parse_groups(value) == expected


@pytest.mark.parametrize("groups", ["[admin]", "admin", "[admin user]", "[user admin]"])
def test_admin_group_in_any_format_is_allowed(groups, database, capsys):
    response, _, _ = invoke(event(token_claims=claims(**{"cognito:groups": groups})), capsys)
    assert response["statusCode"] == 200


# --- 403 -------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("groups", [None, "[]", "[user]", "[administrators]", "[Admin]"])
def test_non_admin_gets_403_without_database_call(groups, database, capsys):
    response, log, _ = invoke(event(token_claims=claims(**{"cognito:groups": groups})), capsys)
    assert_problem(response, 403, "Forbidden")
    assert database.connects == 0
    assert log["outcome"] == "client_error" and log["status"] == 403


def test_403_is_checked_before_the_parameters(database, capsys):
    response, _, _ = invoke(event(query="size=0", token_claims=claims(**{"cognito:groups": None})), capsys)
    assert response["statusCode"] == 403


# --- 400: query parameters of GET /admin -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query, parameter",
    [
        ("size=0", "size"),
        ("size=101", "size"),
        ("page=-1", "page"),
        ("page=abc", "page"),
        ("sort=email", "sort"),
        ("sort=password,asc", "sort"),
        ("foo=1", "foo"),
        ("page=1&page=2", "page"),
        ("page=1000001", "page"),
        ("page=", "page"),
        ("size=1.5", "size"),
        ("size=+5", "size"),
        ("page=%D9%A1", "page"),  # Arabic-Indic digit one: not an ASCII decimal digit
        ("size=99999999999999999999", "size"),
        ("sort=createdAt,DESC", "sort"),
        ("sort=createdAt", "sort"),
        ("sort=created_at,asc", "sort"),
        ("sort=email,asc,extra", "sort"),
        ("sort=email,asc&sort=email,desc", "sort"),
        ("size=10&Page=1", "Page"),
    ],
)
def test_invalid_parameter_gives_400_naming_it_without_database_call(query, parameter, database, capsys):
    response, log, _ = invoke(event(query=query), capsys)
    problem = assert_problem(response, 400, "Bad Request")
    assert f"'{parameter}'" in problem["detail"]
    assert database.connects == 0
    assert log["outcome"] == "client_error" and log["status"] == 400


def test_long_unknown_parameter_name_is_truncated_in_detail(database, capsys):
    response, _, _ = invoke(event(query="a" * 500 + "=1"), capsys)
    assert len(body(response)["detail"]) < 200


@pytest.mark.parametrize(
    "query, page, size",
    [("", 0, 20), ("page=1000000", 1_000_000, 20), ("size=1", 0, 1), ("size=100&page=2", 2, 100), ("page=007", 7, 20)],
)
def test_valid_page_and_size(query, page, size, database, capsys):
    response, _, _ = invoke(event(query=query), capsys)
    assert response["statusCode"] == 200
    result = body(response)
    assert (result["page"], result["size"]) == (page, size)
    sql, params = database.conn.calls[1]
    assert params == {"limit": size, "offset": page * size}


def test_query_string_parameters_used_when_raw_query_absent(database, capsys):
    evt = event()
    del evt["rawQueryString"]
    evt["queryStringParameters"] = {"size": "5", "sort": "email,asc"}
    response, _, _ = invoke(evt, capsys)
    assert body(response)["size"] == 5
    assert database.conn.calls[1][0] == lf.SQL_PAGE[("email", "asc")]


def test_url_encoded_comma_in_sort(database, capsys):
    response, _, _ = invoke(event(query="sort=familyName%2Casc"), capsys)
    assert response["statusCode"] == 200
    assert database.conn.calls[1][0] == lf.SQL_PAGE[("familyName", "asc")]


# --- sort whitelist and SQL ------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sort, column, keyword",
    [
        ("createdAt,asc", "created_at", "ASC"),
        ("createdAt,desc", "created_at", "DESC"),
        ("email,asc", "email", "ASC"),
        ("email,desc", "email", "DESC"),
        ("familyName,asc", "family_name", "ASC"),
        ("familyName,desc", "family_name", "DESC"),
    ],
)
def test_sort_maps_to_a_fixed_statement(sort, column, keyword, database, capsys):
    invoke(event(query=f"sort={sort}"), capsys)
    (count_sql, count_params), (page_sql, _) = database.conn.calls
    assert (count_sql, count_params) == ("SELECT count(*) FROM users", {})
    assert page_sql == (
        "SELECT id, email, given_name, family_name, gender, birthdate, country, height_cm, weight_kg, created_at, "
        f"updated_at FROM users ORDER BY {column} {keyword} NULLS LAST, id LIMIT :limit OFFSET :offset"
    )


def test_default_sort_is_created_at_desc(database, capsys):
    invoke(event(), capsys)
    assert database.conn.calls[1] == (lf.SQL_PAGE[("createdAt", "desc")], {"limit": 20, "offset": 0})


def test_no_input_reaches_the_sql_text(database, capsys):
    hostile = "email,asc;DROP TABLE users--"
    response, _, _ = invoke(event(query="sort=" + hostile.replace(";", "%3B")), capsys)
    assert response["statusCode"] == 400
    assert database.connects == 0
    # Every statement the handler can send is one of these constants.
    assert len(lf.SQL_PAGE) == 6
    for sql in lf.SQL_PAGE.values():
        assert ":limit" in sql and ":offset" in sql and "users" in sql


# --- 200: users mapping, paging --------------------------------------------------------------------------------------


def test_users_mapping(database, capsys):
    database.conn = FakeConnection(rows=[user_row(1)])
    response, log, raw_log = invoke(event(), capsys)
    assert response["statusCode"] == 200
    assert response["headers"] == {"Content-Type": "application/json", "Cache-Control": "no-store"}
    assert body(response) == {
        "items": [
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "email": "user1@example.com",
                "givenName": "Anna",
                "familyName": "Karenina",
                "gender": "female",
                "birthdate": "1990-05-17",
                "country": "Austria",
                "heightCm": 170,
                "weightKg": 62,
                "createdAt": "2026-11-16T10:00:00Z",
                "updatedAt": "2026-11-16T12:30:05Z",
            }
        ],
        "page": 0,
        "size": 20,
        "total": 1,
    }
    assert database.conn.closed
    assert "user1@example.com" not in raw_log and "Karenina" not in raw_log
    assert log["outcome"] == "success"


def test_nulls_and_odd_values_are_returned_as_stored(database, capsys):
    row = user_row(
        2,
        given_name=None,
        family_name="",
        gender="something else",
        birthdate=None,
        country=None,
        height_cm=None,
        weight_kg=-5,
        email="  Mixed@Case.example ",
    )
    database.conn = FakeConnection(rows=[row])
    response, _, _ = invoke(event(), capsys)
    item = body(response)["items"][0]
    assert item["givenName"] is None and item["birthdate"] is None and item["country"] is None
    assert item["heightCm"] is None and item["weightKg"] == -5
    assert item["familyName"] == "" and item["gender"] == "something else"
    assert item["email"] == "  Mixed@Case.example "


def test_timestamps_are_converted_to_utc(database, capsys):
    plus_two = timezone(timedelta(hours=2))
    row = user_row(
        3,
        created_at=datetime(2026, 1, 1, 1, 0, 0, tzinfo=plus_two),
        updated_at=datetime(2026, 1, 1, 0, 0, 0),  # naive: taken as UTC
    )
    database.conn = FakeConnection(rows=[row])
    item = body(invoke(event(), capsys)[0])["items"][0]
    assert item["createdAt"] == "2025-12-31T23:00:00Z"
    assert item["updatedAt"] == "2026-01-01T00:00:00Z"


def test_unicode_is_returned_as_utf8_json(database, capsys):
    database.conn = FakeConnection(rows=[user_row(4, given_name="Анна")])
    response, _, _ = invoke(event(), capsys)
    assert "Анна" in response["body"]


def test_page_slice_and_total(database, capsys):
    database.conn = FakeConnection(rows=[user_row(i) for i in range(1, 6)])
    result = body(invoke(event(query="page=1&size=2"), capsys)[0])
    assert [item["id"][-1] for item in result["items"]] == ["3", "4"]
    assert (result["page"], result["size"], result["total"]) == (1, 2, 5)


def test_page_beyond_the_end_gives_empty_items_and_correct_total(database, capsys):
    database.conn = FakeConnection(rows=[user_row(i) for i in range(1, 4)])
    response, _, _ = invoke(event(query="page=5&size=2"), capsys)
    assert response["statusCode"] == 200
    assert body(response) == {"items": [], "page": 5, "size": 2, "total": 3}


def test_empty_table(database, capsys):
    response, _, _ = invoke(event(), capsys)
    assert body(response) == {"items": [], "page": 0, "size": 20, "total": 0}


def test_one_connection_per_request_closed_afterwards(database, capsys):
    invoke(event(), capsys)
    assert database.connects == 1 and database.conn.closed


# --- 500 -------------------------------------------------------------------------------------------------------------


def test_connect_failure_gives_generic_500(database, capsys):
    try:
        raise ConnectionRefusedError("proxy.example.internal:5432 refused")
    except ConnectionRefusedError as cause:
        error = db.DbConnectError()
        error.__cause__ = cause
    database.error = error
    response, log, raw_log = invoke(event(), capsys)
    problem = assert_problem(response, 500, "Internal Server Error")
    assert "proxy" not in problem["detail"] and "5432" not in problem["detail"]
    assert log["outcome"] == "failure" and log["level"] == "ERROR"
    assert log["message"] == "DB_CONNECT_FAILED" and log["errorClass"] == "ConnectionRefusedError"
    assert "proxy.example" not in raw_log


def test_query_failure_gives_generic_500_and_closes_the_connection(database, capsys):
    database.conn = FakeConnection(
        error=pg8000.native.DatabaseError({"S": "ERROR", "C": "42P01", "M": 'relation "users" does not exist'})
    )
    response, log, raw_log = invoke(event(), capsys)
    problem = assert_problem(response, 500, "Internal Server Error")
    assert "users" not in problem["detail"] and "42P01" not in problem["detail"]
    assert database.conn.closed
    assert log["errorClass"] == "DatabaseError" and log["message"] == "INTERNAL_ERROR"
    assert "relation" not in raw_log


def test_unexpected_error_gives_500(database, monkeypatch, capsys):
    database.conn = FakeConnection(rows=[user_row(1)])

    def broken(row):
        raise KeyError("boom")

    monkeypatch.setattr(lf, "map_user", broken)
    response, log, _ = invoke(event(), capsys)
    assert_problem(response, 500, "Internal Server Error")
    assert log["errorClass"] == "KeyError" and log["outcome"] == "failure"


# --- log line --------------------------------------------------------------------------------------------------------


def test_log_line_fields_on_success(database, capsys):
    _, log, raw_log = invoke(event(), capsys)
    assert set(log) == {
        "level", "message", "function", "awsRequestId", "apiRequestId", "userSub", "route", "status", "durationMs",
        "outcome",
    }
    assert log["level"] == "INFO"
    assert log["message"] == "request completed"
    assert log["function"] == "aws-challenge-admin"
    assert log["awsRequestId"] == "req-123"
    assert log["apiRequestId"] == "api-req-456"
    assert log["userSub"] == SUB
    assert log["route"] == "GET /admin"
    assert log["status"] == 200
    assert isinstance(log["durationMs"], int) and log["durationMs"] >= 0
    assert TOKEN not in raw_log and "Bearer" not in raw_log and "anna" not in raw_log


def test_log_line_has_error_class_only_on_5xx(database, capsys):
    _, log, _ = invoke(event(query="size=0"), capsys)
    assert "errorClass" not in log and log["level"] == "WARNING"


def test_log_line_without_claims_has_no_user_sub(capsys):
    _, log, _ = invoke(event(with_claims=False), capsys)
    assert log["userSub"] is None and log["status"] == 401
