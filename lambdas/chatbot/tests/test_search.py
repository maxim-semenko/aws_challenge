"""DB side of POST /chat: read-only transaction, vector query, statement execution, value mapping (spec 12)."""

import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

import pytest
from pg8000.types import PGInterval

import db
import search
from doubles import FakeConnection, db_error
from bedrock_stub import unit_vector


@pytest.fixture
def connect(monkeypatch):
    """Replace db.connect; returns a holder whose `conn` is the FakeConnection handed out and `timeouts` the args."""

    class Holder:
        conn = FakeConnection()
        timeouts = []

    def fake_connect(timeout=db.DEFAULT_TIMEOUT_S):
        Holder.timeouts.append(timeout)
        return Holder.conn

    monkeypatch.setattr(db, "connect", fake_connect)
    return Holder


def test_vector_query_runs_read_only_with_timeout_and_rolls_back(connect):
    connect.conn = FakeConnection(vector_rows=[
        (uuid.UUID(int=1), "a@x.test", "A", "B", "female", date(1990, 5, 17), "Poland", 170, 60, 0.0),
    ])
    rows = search.similar_users(unit_vector(2))

    assert connect.timeouts == [5.0]
    assert connect.conn.sql == [
        "BEGIN READ ONLY",
        "SET LOCAL statement_timeout = '4s'",
        search.SQL_VECTOR,
        "ROLLBACK",
    ]
    assert search.SQL_VECTOR == (
        "SELECT id, email, given_name, family_name, gender, birthdate, country, height_cm, weight_kg, "
        "embedding <-> CAST(:q AS vector) AS distance FROM users ORDER BY embedding <-> CAST(:q AS vector) LIMIT 5"
    )
    (_, _, params) = connect.conn.statements[2]
    assert set(params) == {"q"} and params["q"].startswith("[0.0,0.0,1.0,")  # the vector only as a parameter
    assert connect.conn.closed
    assert rows == [[str(uuid.UUID(int=1)), "a@x.test", "A", "B", "female", "1990-05-17", "Poland", 170, 60, 0.0]]


def test_null_distances_are_dropped(connect):
    row = (uuid.UUID(int=1), None, None, None, None, None, None, None, None)
    connect.conn = FakeConnection(vector_rows=[(*row, 0.5), (*row, None), (*row, 1.25)])
    rows = search.similar_users(unit_vector())
    assert [r[-1] for r in rows] == [0.5, 1.25]
    assert rows[0][1:9] == [None] * 8


def test_guarded_statement_uses_the_extended_protocol_and_returns_labels(connect):
    connect.conn = FakeConnection(rows=[(3, "PL")], columns=("n", "country"))
    columns, rows, truncated = search.run_statement("SELECT 1 FROM users LIMIT 101")

    assert connect.conn.statements == [
        ("run", "BEGIN READ ONLY", {}),
        ("run", "SET LOCAL statement_timeout = '4s'", {}),
        ("execute_unnamed", "SELECT 1 FROM users LIMIT 101", {}),
        ("run", "ROLLBACK", {}),
    ]
    assert (columns, rows, truncated) == (["n", "country"], [[3, "PL"]], False)
    assert connect.conn.closed and connect.timeouts == [5.0]


def test_row_cap_100_and_truncated(connect):
    connect.conn = FakeConnection(rows=[(i,) for i in range(101)], columns=("i",))
    _, rows, truncated = search.run_statement("x")
    assert len(rows) == 100 and truncated is True
    connect.conn = FakeConnection(rows=[(i,) for i in range(100)], columns=("i",))
    _, rows, truncated = search.run_statement("x")
    assert len(rows) == 100 and truncated is False


@pytest.mark.parametrize("code", ["42703", "22012", "57014", "25006", "42501"])
def test_sql_errors_become_statement_error_and_are_rolled_back(connect, code):
    error = db_error(code)
    connect.conn = FakeConnection(statement_error=error)
    with pytest.raises(search.StatementError) as raised:
        search.run_statement("x")
    assert raised.value.__cause__ is error
    assert connect.conn.sql[-1] == "ROLLBACK" and connect.conn.closed


@pytest.mark.parametrize("error", [db_error("08006"), OSError("socket"), ConnectionResetError()])
def test_connection_errors_are_not_statement_errors(connect, error):
    connect.conn = FakeConnection(statement_error=error)
    with pytest.raises(type(error)):
        search.run_statement("x")
    assert connect.conn.closed


def test_rollback_failure_keeps_the_original_error(connect):
    class BrokenRollback(FakeConnection):
        def run(self, sql, **params):
            if sql == "ROLLBACK":
                raise OSError("gone")
            return super().run(sql, **params)

    connect.conn = BrokenRollback(statement_error=db_error("42703"))
    with pytest.raises(search.StatementError):
        search.run_statement("x")


# --- value mapping --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (True, True),
        (7, 7),
        ("text", "text"),
        (1.5, 1.5),
        (float("nan"), "NaN"),
        (float("inf"), "Infinity"),
        (float("-inf"), "-Infinity"),
        (Decimal("5"), 5),
        (Decimal("5.000"), 5),
        (Decimal("172.45"), 172.45),
        (Decimal("NaN"), "NaN"),
        (Decimal("Infinity"), "Infinity"),
        (date(1990, 5, 17), "1990-05-17"),
        (datetime(2026, 11, 25, 10, 0, 1, 500, tzinfo=timezone.utc), "2026-11-25T10:00:01Z"),
        (datetime(2026, 11, 25, 11, 0, 1, tzinfo=timezone(timedelta(hours=1))), "2026-11-25T10:00:01Z"),
        (datetime(2026, 11, 25, 10, 0, 1), "2026-11-25 10:00:01"),
        (uuid.UUID(int=1), "00000000-0000-0000-0000-000000000001"),
        (time(4, 5, 6), "04:05:06"),
        (b"\x01\xff", "\\x01ff"),
        (timedelta(days=3, hours=4, minutes=5, seconds=6), "3 days 04:05:06"),
        (timedelta(days=1), "1 day"),
        (timedelta(0), "00:00:00"),
        (timedelta(seconds=1, microseconds=500000), "00:00:01.5"),
        (timedelta(days=-1), "-1 days"),
        (timedelta(hours=-2), "-02:00:00"),
        (timedelta(days=-2, hours=-3), "-2 days -03:00:00"),
        (PGInterval(years=34, months=6, days=8), "34 years 6 mons 8 days"),
        (PGInterval(years=1, months=1, days=1, hours=1), "1 year 1 mon 1 day 01:00:00"),
    ],
)
def test_value_mapping(value, expected):
    assert search.to_json(value) == expected


def test_interval_text_signs_follow_postgresql():
    assert search.interval_text(-14, 3, 0) == "-1 years -2 mons +3 days"
    assert search.interval_text(0, -3, 3_600_000_000) == "-3 days +01:00:00"
    assert search.interval_text(0, 0, -90_000_000) == "-00:01:30"
