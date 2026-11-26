"""Optional integration test of the chatbot DB side against a local PostgreSQL 14 + pgvector (docker compose up -d).

Skipped unless MIGRATE_TEST_DATABASE_URL is set (same variable as the sync and admin integration tests), e.g.
    MIGRATE_TEST_DATABASE_URL=postgresql://app:app@localhost:5432/aws_challenge
Builds `users` in a throw-away schema from lambdas/sync/migrations (search path `<schema>, public`, so an extension
already installed in `public` is found; dropped at the end) and proves: the guard's renderings of the accepted
statements run on PostgreSQL 14; the read-only transaction blocks a write that slipped through; the vector query
returns the nearest users with NULL distances dropped.
"""

import os
import uuid
from pathlib import Path
from urllib.parse import unquote, urlparse

import pg8000.native
import pytest

import db
import search
import sql_guard
from test_sql_guard import ACCEPTED

URL = os.environ.get("MIGRATE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="MIGRATE_TEST_DATABASE_URL not set")

MIGRATIONS = Path(__file__).resolve().parents[2] / "sync" / "migrations"


class Unclosable:
    """Hands the test connection to the code under test without letting it close it."""

    def __init__(self, conn):
        self._conn = conn

    def run(self, sql, **params):
        return self._conn.run(sql, **params)

    def execute_unnamed(self, sql):
        return self._conn.execute_unnamed(sql)

    def close(self):
        pass


def vector(index):
    values = [0.0] * 1024
    values[index] = 1.0
    return values


@pytest.fixture
def conn(monkeypatch):
    url = urlparse(URL)
    connection = pg8000.native.Connection(
        user=unquote(url.username or ""),
        password=unquote(url.password or "") or None,
        host=url.hostname or "localhost",
        port=url.port or 5432,
        database=url.path.lstrip("/") or None,
    )
    schema = f"it_chat_{uuid.uuid4().hex[:12]}"
    connection.run(f"CREATE SCHEMA {schema}")  # generated identifier, no user input
    connection.run(f"SET search_path TO {schema}, public")
    for path in sorted(MIGRATIONS.glob("V*__*.sql"), key=lambda p: int(p.name[1:].split("__")[0])):
        connection.execute_simple(path.read_text(encoding="utf-8"))
    for i in range(1, 4):
        connection.run(
            "INSERT INTO users (id, email, gender, birthdate, country, height_cm, weight_kg, confirmed_at, embedding) "
            "VALUES (CAST(:id AS uuid), :email, 'female', DATE '1995-01-01', 'Poland', 170, 75, now(), "
            "CAST(:v AS vector))",
            id=str(uuid.UUID(int=i)), email=f"it-{i}@seed.invalid", v=str(vector(i)),
        )
    connection.run("INSERT INTO users (id, email) VALUES (CAST(:id AS uuid), 'no-vector@seed.invalid')",
                   id=str(uuid.UUID(int=9)))
    monkeypatch.setattr(db, "connect", lambda **kwargs: Unclosable(connection))
    try:
        yield connection
    finally:
        connection.run(f"DROP SCHEMA {schema} CASCADE")
        connection.close()


@pytest.mark.parametrize("answer", ACCEPTED)
def test_guard_renderings_run_on_postgresql_14(conn, answer):
    columns, rows, truncated = search.run_statement(sql_guard.check(answer).sql)
    assert columns and truncated is False and len(rows) <= 100


def test_statistics_question_counts_rows(conn):
    sql = sql_guard.check(
        "SELECT count(*) FROM users WHERE country IN ('PL','Poland') AND weight_kg > 70 "
        "AND date_part('year', age(birthdate)) BETWEEN 25 AND 35"
    ).sql
    columns, rows, _ = search.run_statement(sql)
    assert columns == ["count"] and rows[0][0] in (0, 3)  # 3 while the fixed birthdate gives an age of 25..35


def test_a_write_that_slipped_through_fails_read_only(conn):
    with pytest.raises(search.StatementError) as raised:
        search.run_statement("DELETE FROM users")
    assert raised.value.__cause__.args[0]["C"] == "25006"
    assert conn.run("SELECT count(*) FROM users")[0][0] == 4


def test_vector_query_nearest_first_and_null_distance_dropped(conn):
    rows = search.similar_users(vector(2))
    assert rows[0][0] == str(uuid.UUID(int=2)) and rows[0][-1] == pytest.approx(0.0)
    assert len(rows) == 3  # the row without a vector is dropped
