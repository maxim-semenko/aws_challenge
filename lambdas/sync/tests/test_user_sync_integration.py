"""Optional integration test of the UserConfirmed upsert against a local PostgreSQL 14 (docker compose up -d).

Skipped unless MIGRATE_TEST_DATABASE_URL is set (same variable as test_migrator_integration.py), e.g.
    MIGRATE_TEST_DATABASE_URL=postgresql://app:app@localhost:5432/aws_challenge
Applies the migrations in a throw-away schema (dropped at the end), then runs the handler with db.connect replaced by
the local connection; plain local connection, no IAM token, no TLS. Bedrock is the StubBedrock double.
"""

import copy
import os
import uuid
from datetime import date
from urllib.parse import unquote, urlparse

import pg8000.native
import pytest
from botocore.exceptions import ConnectTimeoutError

import db
import embeddings
import migrator
import user_sync
from bedrock_stub import StubBedrock, install, unit_vector

URL = os.environ.get("MIGRATE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="MIGRATE_TEST_DATABASE_URL not set")

SUB = str(uuid.uuid4())
EVENT = {
    "id": "it-event",
    "source": "aws-challenge.cognito",
    "detail-type": "UserConfirmed",
    "detail": {
        "version": 1,
        "userPoolId": "eu-west-1_EXAMPLE",
        "sub": SUB,
        "email": " Test.User@Example.com ",
        "attributes": {"given_name": "Test", "birthdate": "2000-02-31", "custom:height": "400"},
        "confirmedAt": "2026-11-16T10:00:00Z",
    },
}


class Context:
    function_name = "aws-challenge-sync"
    aws_request_id = "it"


class Unclosable:
    """Hands the test connection to the handler without letting it close it."""

    def __init__(self, conn):
        self._conn = conn

    def run(self, sql, **params):
        return self._conn.run(sql, **params)

    def close(self):
        pass


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
    schema = f"it_sync_{uuid.uuid4().hex[:12]}"
    connection.run(f"CREATE SCHEMA {schema}")  # generated identifier, no user input
    connection.run(f"SET search_path TO {schema}, public")
    migrator.run(connection, "migrate", migrator.MIGRATIONS_DIR, {"action": "migrate", "applied": [], "current": None})
    monkeypatch.setattr(db, "connect", lambda **kwargs: Unclosable(connection))
    try:
        yield connection
    finally:
        connection.run(f"DROP SCHEMA {schema} CASCADE")
        connection.close()


def test_upsert_on_postgresql_14(conn, monkeypatch):
    install(monkeypatch, StubBedrock(default=unit_vector(3, scale=2.0)))
    assert user_sync.handle(copy.deepcopy(EVENT), Context()) == {"outcome": "inserted"}
    stored = conn.run(
        "SELECT vector_dims(embedding), embedding <-> CAST(:v AS vector) FROM users",
        v=embeddings.to_vector_literal(unit_vector(3)),
    )
    assert stored[0][0] == 1024 and stored[0][1] < 1e-6  # normalised before storing
    first = conn.run("SELECT created_at, updated_at FROM users WHERE id = CAST(:id AS uuid)", id=SUB)

    changed = copy.deepcopy(EVENT)
    changed["detail"]["attributes"] = {"birthdate": "2000-02-29", "custom:weight": "-5"}
    install(monkeypatch, StubBedrock(outcomes=[ConnectTimeoutError(endpoint_url="https://x")]))
    assert user_sync.handle(changed, Context()) == {"outcome": "updated"}
    assert conn.run("SELECT embedding IS NULL FROM users") == [[True]]  # failed re-sync: no stale vector

    rows = conn.run(
        "SELECT email, given_name, birthdate, height_cm, weight_kg, created_at, updated_at FROM users "
        "WHERE id = CAST(:id AS uuid)",
        id=SUB,
    )
    assert len(rows) == 1
    email, given_name, birthdate, height_cm, weight_kg, created_at, updated_at = rows[0]
    assert (email, given_name, birthdate, height_cm, weight_kg) == (
        "test.user@example.com", None, date(2000, 2, 29), None, -5)
    assert created_at == first[0][0]
    assert updated_at >= first[0][1]
