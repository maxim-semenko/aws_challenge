"""Unit tests of the UserConfirmed upsert of aws-challenge-sync (spec 07 §Outputs, §Edge Cases; AC-07.2)."""

import copy
import json
from datetime import date, datetime, timezone

import pg8000.native
import pytest

import db
import lambda_function
import user_sync

SUB = "8f1c2a3b-0000-4000-8000-000000000001"
EMAIL = "Person@Example.com"
ATTRIBUTES = {
    "given_name": "Anna",
    "family_name": "Karenina",
    "gender": "female",
    "birthdate": "1990-05-17",
    "custom:country": "Austria",
    "custom:height": "170",
    "custom:weight": "62",
}
EVENT = {
    "version": "0",
    "id": "6a7e8feb-b491-4cf7-a9f1-bf3703467718",
    "detail-type": "UserConfirmed",
    "source": "aws-challenge.cognito",
    "account": "000000000000",
    "time": "2026-11-16T10:00:00Z",
    "region": "eu-west-1",
    "resources": [],
    "detail": {
        "version": 1,
        "userPoolId": "eu-west-1_EXAMPLE",
        "sub": SUB,
        "email": EMAIL,
        "attributes": ATTRIBUTES,
        "confirmedAt": "2026-11-16T10:00:00.123Z",
    },
}
VALUES = [EMAIL, EMAIL.lower(), *ATTRIBUTES.values()]


class Context:
    function_name = "aws-challenge-sync"
    aws_request_id = "req-789"


class FakeConnection:
    """pg8000.native.Connection double holding the users table as a dict keyed by id."""

    def __init__(self, rows=None, error=None):
        self.rows = rows if rows is not None else {}
        self.error = error
        self.calls = []
        self.closed = False

    def run(self, sql, **params):
        self.calls.append((sql, params))
        if self.error is not None:
            raise self.error
        assert sql == user_sync.SQL_UPSERT
        inserted = params["id"] not in self.rows
        self.rows[params["id"]] = dict(params)
        return [[inserted]]

    def close(self):
        self.closed = True


@pytest.fixture
def conn(monkeypatch):
    connection = FakeConnection()
    connects = []

    def connect(**kwargs):
        connects.append(kwargs)
        return connection

    monkeypatch.setattr(db, "connect", connect)
    connection.connects = connects
    return connection


@pytest.fixture
def no_connect(monkeypatch):
    def forbidden(**kwargs):
        raise AssertionError("must not connect")

    monkeypatch.setattr(db, "connect", forbidden)


def event_with(detail_changes=None, attribute_changes=None, drop=()):
    event = copy.deepcopy(EVENT)
    for key in drop:
        event["detail"]["attributes"].pop(key, None)
    event["detail"]["attributes"].update(attribute_changes or {})
    event["detail"].update(detail_changes or {})
    return event


def invoke(event):
    return lambda_function.lambda_handler(event, Context())


def log_line(capsys):
    (line,) = [json.loads(text) for text in capsys.readouterr().out.splitlines() if text.strip()]
    return line


def assert_no_values_logged(line, extra=()):
    text = json.dumps(line)
    for value in [*VALUES, *extra]:
        assert value not in text, value


# --- mapping (spec 07 §Outputs) ---------------------------------------------------------------------------------


def test_full_event_is_inserted_with_every_mapped_column(conn, capsys):
    assert invoke(copy.deepcopy(EVENT)) == {"outcome": "inserted"}

    assert conn.rows[SUB] == {
        "id": SUB,
        "email": "person@example.com",
        "given_name": "Anna",
        "family_name": "Karenina",
        "gender": "female",
        "birthdate": date(1990, 5, 17),
        "country": "Austria",
        "height_cm": 170,
        "weight_kg": 62,
        "confirmed_at": datetime(2026, 11, 16, 10, 0, 0, 123000, tzinfo=timezone.utc),
    }
    assert len(conn.calls) == 1
    assert conn.connects == [{}]  # shared default socket timeout (10 s)
    assert conn.closed

    line = log_line(capsys)
    assert line == {
        "level": "INFO",
        "message": "user synced",
        "function": "aws-challenge-sync",
        "awsRequestId": "req-789",
        "eventId": EVENT["id"],
        "userSub": SUB,
        "outcome": "inserted",
        "invalidFields": [],
        "durationMs": line["durationMs"],
    }
    assert isinstance(line["durationMs"], int)
    assert_no_values_logged(line)


def test_email_is_trimmed_and_lower_cased(conn):
    invoke(event_with({"email": "  MiXeD@Example.COM \t"}))
    assert conn.rows[SUB]["email"] == "mixed@example.com"


def test_upper_case_sub_is_accepted_and_stored_lower_case(conn):
    invoke(event_with({"sub": SUB.upper()}))
    assert list(conn.rows) == [SUB]


@pytest.mark.parametrize("missing", [True, False], ids=["missing", "empty-string"])
def test_missing_or_empty_attributes_become_null_without_invalid_fields(missing, conn, capsys):
    if missing:
        event = event_with(drop=ATTRIBUTES)
    else:
        event = event_with(attribute_changes={key: "" for key in ATTRIBUTES})

    assert invoke(event) == {"outcome": "inserted"}

    row = conn.rows[SUB]
    for column in ("given_name", "family_name", "gender", "birthdate", "country", "height_cm", "weight_kg"):
        assert row[column] is None, column
    assert log_line(capsys)["invalidFields"] == []


def test_empty_attributes_object_is_valid(conn):
    assert invoke(event_with({"attributes": {}})) == {"outcome": "inserted"}
    assert conn.rows[SUB]["given_name"] is None


def test_missing_attributes_object_is_tolerated(conn, capsys):
    event = copy.deepcopy(EVENT)
    del event["detail"]["attributes"]
    assert invoke(event) == {"outcome": "inserted"}
    assert log_line(capsys)["invalidFields"] == []


def test_attributes_not_an_object_store_nulls_and_name_the_field(conn, capsys):
    assert invoke(event_with({"attributes": "given_name=Anna"})) == {"outcome": "inserted"}
    assert conn.rows[SUB]["given_name"] is None
    assert log_line(capsys)["invalidFields"] == ["attributes"]


def test_text_attributes_are_stored_as_given(conn):
    invoke(event_with(attribute_changes={"given_name": " <b>Ann</b> ", "gender": "other", "custom:country": "xx"}))
    row = conn.rows[SUB]
    assert (row["given_name"], row["gender"], row["country"]) == (" <b>Ann</b> ", "other", "xx")


def test_non_string_text_attribute_becomes_null_and_is_named(conn, capsys):
    invoke(event_with(attribute_changes={"family_name": 42}))
    assert conn.rows[SUB]["family_name"] is None
    assert log_line(capsys)["invalidFields"] == ["family_name"]


@pytest.mark.parametrize("value", ["31/02/2000", "2000-02-31", "2000-13-01", "20000101", "2000-1-1", "abc", "１９９０-05-17"])
def test_invalid_birthdate_becomes_null_and_is_named(value, conn, capsys):
    assert invoke(event_with(attribute_changes={"birthdate": value})) == {"outcome": "inserted"}
    assert conn.rows[SUB]["birthdate"] is None
    line = log_line(capsys)
    assert line["invalidFields"] == ["birthdate"]
    assert value not in json.dumps(line)


def test_leap_day_birthdate_is_a_date(conn):
    invoke(event_with(attribute_changes={"birthdate": "2000-02-29"}))
    assert conn.rows[SUB]["birthdate"] == date(2000, 2, 29)


@pytest.mark.parametrize(
    "value, expected",
    [("400", 400), ("+170", 170), ("-5", -5), ("0", 0), ("0170", 170), ("2147483647", 2147483647),
     ("-2147483648", -2147483648)],
)
def test_integer_attributes_are_stored_even_outside_the_spa_range(value, expected, conn, capsys):
    invoke(event_with(attribute_changes={"custom:height": value, "custom:weight": value}))
    row = conn.rows[SUB]
    assert (row["height_cm"], row["weight_kg"]) == (expected, expected)
    assert log_line(capsys)["invalidFields"] == []


@pytest.mark.parametrize("value", ["170.5", "abc", "1e3", " 170", "2147483648", "-2147483649", "+", "9" * 5000, "١٧٠"])
def test_invalid_height_and_weight_become_null_and_are_named(value, conn, capsys):
    invoke(event_with(attribute_changes={"custom:height": value, "custom:weight": value}))
    row = conn.rows[SUB]
    assert (row["height_cm"], row["weight_kg"]) == (None, None)
    assert log_line(capsys)["invalidFields"] == ["custom:height", "custom:weight"]


def test_height_400_without_weight_is_stored(conn, capsys):
    """Spec 07 §Edge Cases: direct sign-up with custom:height = 400, no custom:weight."""
    assert invoke(event_with(attribute_changes={"custom:height": "400"}, drop=["custom:weight"])) == {
        "outcome": "inserted"
    }
    assert (conn.rows[SUB]["height_cm"], conn.rows[SUB]["weight_kg"]) == (400, None)
    assert log_line(capsys)["invalidFields"] == []


@pytest.mark.parametrize(
    "value, expected",
    [
        ("2026-11-16T10:00:00Z", datetime(2026, 11, 16, 10, 0, tzinfo=timezone.utc)),
        ("2026-11-16T11:00:00+01:00", datetime(2026, 11, 16, 10, 0, tzinfo=timezone.utc)),
        ("2026-11-16T10:00:00", datetime(2026, 11, 16, 10, 0, tzinfo=timezone.utc)),
    ],
)
def test_confirmed_at_is_parsed_as_iso_8601(value, expected, conn):
    invoke(event_with({"confirmedAt": value}))
    assert conn.rows[SUB]["confirmed_at"] == expected


@pytest.mark.parametrize("value", ["yesterday", "16.11.2026", 1763287200])
def test_invalid_confirmed_at_becomes_null(value, conn, capsys):
    assert invoke(event_with({"confirmedAt": value})) == {"outcome": "inserted"}
    assert conn.rows[SUB]["confirmed_at"] is None
    assert log_line(capsys)["invalidFields"] == ["confirmedAt"]


def test_unknown_keys_are_ignored(conn):
    event = event_with({"extra": "x"}, attribute_changes={"email_verified": "true", "custom:other": "y"})
    assert invoke(event) == {"outcome": "inserted"}
    assert set(conn.rows[SUB]) == {"id", "email", "given_name", "family_name", "gender", "birthdate", "country",
                                   "height_cm", "weight_kg", "confirmed_at"}


# --- idempotency ------------------------------------------------------------------------------------------------


def test_same_event_twice_is_updated_with_one_row(conn, capsys):
    assert invoke(copy.deepcopy(EVENT)) == {"outcome": "inserted"}
    first = dict(conn.rows[SUB])
    capsys.readouterr()

    assert invoke(copy.deepcopy(EVENT)) == {"outcome": "updated"}
    assert list(conn.rows) == [SUB]
    assert conn.rows[SUB] == first
    assert log_line(capsys)["outcome"] == "updated"


def test_upsert_overwrites_registration_columns_and_updated_at_but_keeps_created_at():
    sql = user_sync.SQL_UPSERT
    assert "ON CONFLICT (id) DO UPDATE SET" in sql
    update = sql.split("DO UPDATE SET")[1]
    for column in ("email", "given_name", "family_name", "gender", "birthdate", "country", "height_cm", "weight_kg",
                   "confirmed_at"):
        assert f"{column} = EXCLUDED.{column}" in update
    assert "updated_at = now()" in update
    assert "created_at" not in sql


# --- rejection (no DB call, no error) ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "changes, field, logged_sub",
    [
        ({"sub": "not-a-uuid"}, "sub", None),
        ({"sub": SUB + "0"}, "sub", None),
        ({"sub": "{" + SUB + "}"}, "sub", None),
        ({"sub": None}, "sub", None),
        ({"sub": 12345}, "sub", None),
        ({"email": None}, "email", SUB),
        ({"email": ""}, "email", SUB),
        ({"email": "   "}, "email", SUB),
        ({"email": ["a@b.c"]}, "email", SUB),
    ],
)
def test_bad_sub_or_email_is_rejected_without_db_call(changes, field, logged_sub, no_connect, capsys):
    assert invoke(event_with(changes)) == {"outcome": "rejected"}

    line = log_line(capsys)
    assert line["outcome"] == "rejected"
    assert line["level"] == "WARNING"
    assert line["invalidFields"] == [field]
    assert line["userSub"] == logged_sub
    assert "errorClass" not in line
    assert_no_values_logged(line, extra=["not-a-uuid"])


def test_missing_email_key_is_rejected(no_connect):
    event = copy.deepcopy(EVENT)
    del event["detail"]["email"]
    assert invoke(event) == {"outcome": "rejected"}


@pytest.mark.parametrize("detail", [None, "x", []], ids=["missing", "string", "list"])
def test_detail_not_an_object_is_rejected(detail, no_connect, capsys):
    event = copy.deepcopy(EVENT)
    if detail is None:
        del event["detail"]
    else:
        event["detail"] = detail
    assert invoke(event) == {"outcome": "rejected"}
    assert log_line(capsys)["invalidFields"] == ["sub"]


# --- database errors raise (Lambda async retry) -----------------------------------------------------------------


def test_database_error_raises_and_logs_failure(monkeypatch, capsys):
    error = pg8000.native.DatabaseError({"S": "ERROR", "C": "23502", "M": f"null value: {EMAIL}"})
    connection = FakeConnection(error=error)
    monkeypatch.setattr(db, "connect", lambda **kwargs: connection)

    with pytest.raises(user_sync.UserSyncError, match="^USER_SYNC_FAILED: 23502$") as raised:
        invoke(copy.deepcopy(EVENT))

    assert raised.value.__cause__ is error
    assert connection.closed
    line = log_line(capsys)
    assert line["outcome"] == "failure"
    assert line["level"] == "ERROR"
    assert line["message"] == "USER_SYNC_FAILED: 23502"
    assert line["errorClass"] == "DatabaseError"
    assert line["userSub"] == SUB
    assert_no_values_logged(line)


@pytest.mark.parametrize("error", [pg8000.native.InterfaceError("network error"), TimeoutError("timed out")])
def test_lost_connection_raises_with_unknown_sqlstate(error, monkeypatch, capsys):
    connection = FakeConnection(error=error)
    monkeypatch.setattr(db, "connect", lambda **kwargs: connection)

    with pytest.raises(user_sync.UserSyncError, match="^USER_SYNC_FAILED: UNKNOWN$"):
        invoke(copy.deepcopy(EVENT))

    assert connection.closed
    assert log_line(capsys)["errorClass"] == type(error).__name__


def test_connect_failure_raises_db_connect_failed(monkeypatch, capsys):
    def connect(**kwargs):
        raise db.DbConnectError() from KeyError("DB_PROXY_ENDPOINT")

    monkeypatch.setattr(db, "connect", connect)

    with pytest.raises(db.DbConnectError, match="^DB_CONNECT_FAILED$"):
        invoke(copy.deepcopy(EVENT))

    line = log_line(capsys)
    assert (line["outcome"], line["message"], line["errorClass"]) == ("failure", "DB_CONNECT_FAILED", "KeyError")


def test_unexpected_error_is_logged_without_its_message(monkeypatch, capsys):
    connection = FakeConnection(error=RuntimeError(f"boom {EMAIL}"))
    monkeypatch.setattr(db, "connect", lambda **kwargs: connection)

    with pytest.raises(RuntimeError):
        invoke(copy.deepcopy(EVENT))

    line = log_line(capsys)
    assert (line["message"], line["errorClass"]) == ("unexpected error", "RuntimeError")
    assert_no_values_logged(line)


# --- SQL is parameterised ---------------------------------------------------------------------------------------


def test_sql_contains_no_value_and_every_value_is_a_parameter(conn):
    event = event_with({"sub": SUB}, attribute_changes={"given_name": "Robert'); DROP TABLE users;--"})
    invoke(event)

    ((sql, params),) = conn.calls
    assert sql == user_sync.SQL_UPSERT
    for value in [SUB, "person@example.com", "Robert'); DROP TABLE users;--", "Karenina", "female", "1990",
                  "Austria", "170", "62", "2026-11-16"]:
        assert value not in sql
    assert set(params) == {"id", "email", "given_name", "family_name", "gender", "birthdate", "country",
                           "height_cm", "weight_kg", "confirmed_at"}
    for name in params:
        assert f":{name} " in sql or f":{name})" in sql
