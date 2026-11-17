"""Optional integration test of GET /admin against a local PostgreSQL 14 (docker compose up -d).

Skipped unless MIGRATE_TEST_DATABASE_URL is set (same variable as the sync integration tests), e.g.
    MIGRATE_TEST_DATABASE_URL=postgresql://app:app@localhost:5432/aws_challenge
Creates `users` in a throw-away schema from the migration files of lambdas/sync/migrations (dropped at the end), then
runs the handler with db.connect replaced by the local connection; plain local connection, no IAM token, no TLS.
Proves the real SQL: sort whitelist, NULLS LAST, id tiebreak, LIMIT/OFFSET parameters, column types of the mapping.
"""

import json
import os
import uuid
from pathlib import Path
from urllib.parse import unquote, urlparse

import pg8000.native
import pytest

import db
import lambda_function as lf

URL = os.environ.get("MIGRATE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="MIGRATE_TEST_DATABASE_URL not set")

MIGRATIONS = Path(__file__).resolve().parents[2] / "sync" / "migrations"
IDS = [str(uuid.UUID(int=i)) for i in range(1, 5)]


class Context:
    function_name = "aws-challenge-admin"
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
    schema = f"it_admin_{uuid.uuid4().hex[:12]}"
    connection.run(f"CREATE SCHEMA {schema}")  # generated identifier, no user input
    connection.run(f"SET search_path TO {schema}")
    for path in sorted(MIGRATIONS.glob("V*__*.sql"), key=lambda p: int(p.name[1:].split("__")[0])):
        connection.execute_simple(path.read_text(encoding="utf-8"))
    rows = [
        (IDS[0], "b@example.com", "Karenina", "2026-01-02T00:00:00Z", "1990-05-17", 170),
        (IDS[1], "a@example.com", None, "2026-01-01T00:00:00Z", None, None),
        (IDS[2], "c@example.com", "Anders", "2026-01-02T00:00:00Z", None, None),
        (IDS[3], "d@example.com", "Karenina", "2026-01-03T00:00:00Z", None, 180),
    ]
    for id_, email, family_name, created_at, birthdate, height in rows:
        connection.run(
            "INSERT INTO users (id, email, family_name, created_at, updated_at, birthdate, height_cm) VALUES "
            "(CAST(:id AS uuid), :email, :family_name, CAST(:created AS timestamptz), CAST(:created AS timestamptz), "
            "CAST(:birthdate AS date), CAST(:height AS integer))",
            id=id_, email=email, family_name=family_name, created=created_at, birthdate=birthdate, height=height,
        )
    monkeypatch.setattr(db, "connect", lambda **kwargs: Unclosable(connection))
    try:
        yield connection
    finally:
        connection.run(f"DROP SCHEMA {schema} CASCADE")
        connection.close()


def users(query):
    event = {
        "routeKey": "GET /admin",
        "rawQueryString": query,
        "requestContext": {
            "requestId": "it",
            "authorizer": {"jwt": {"claims": {
                "sub": IDS[0], "token_use": "access", "cognito:groups": "[admin]", "exp": "1700000000",
            }}},
        },
    }
    response = lf.lambda_handler(event, Context())
    assert response["statusCode"] == 200, response["body"]
    return json.loads(response["body"])


@pytest.mark.parametrize(
    "sort, expected",
    [
        ("createdAt,desc", [IDS[3], IDS[0], IDS[2], IDS[1]]),
        ("createdAt,asc", [IDS[1], IDS[0], IDS[2], IDS[3]]),
        ("email,asc", [IDS[1], IDS[0], IDS[2], IDS[3]]),
        ("familyName,asc", [IDS[2], IDS[0], IDS[3], IDS[1]]),  # NULL last, ties by id
        ("familyName,desc", [IDS[0], IDS[3], IDS[2], IDS[1]]),  # NULL last in descending order too
    ],
)
def test_sort_order_against_postgresql(conn, sort, expected):
    result = users(f"sort={sort}")
    assert [item["id"] for item in result["items"]] == expected
    assert result["total"] == 4


def test_paging_and_mapping_against_postgresql(conn):
    result = users("sort=createdAt,asc&page=0&size=1")
    assert result["total"] == 4 and len(result["items"]) == 1
    item = result["items"][0]
    assert item["id"] == IDS[1] and item["birthdate"] is None and item["createdAt"] == "2026-01-01T00:00:00Z"
    second = users("sort=createdAt,asc&page=1&size=1")["items"][0]
    assert second["birthdate"] == "1990-05-17" and second["heightCm"] == 170
    assert users("page=10&size=100") == {"items": [], "page": 10, "size": 100, "total": 4}
