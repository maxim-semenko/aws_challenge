"""Optional integration test against a local PostgreSQL 14 + pgvector (docker compose up -d) — AC-06.1, AC-10.1.

Skipped unless MIGRATE_TEST_DATABASE_URL is set, e.g.
    MIGRATE_TEST_DATABASE_URL=postgresql://app:app@localhost:5432/aws_challenge
Runs in a throw-away schema (dropped at the end; `public` stays on the search path so an already installed
extension `vector` is found); plain local connection, no IAM token, no TLS.
"""

import os
import uuid
from urllib.parse import unquote, urlparse

import pg8000.native
import pytest

import migrator as lf

URL = os.environ.get("MIGRATE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="MIGRATE_TEST_DATABASE_URL not set")

EXPECTED_COLUMNS = [
    # column_name, data_type, is_nullable, column_default
    ["id", "uuid", "NO", None],
    ["email", "text", "NO", None],
    ["given_name", "text", "YES", None],
    ["family_name", "text", "YES", None],
    ["gender", "text", "YES", None],
    ["birthdate", "date", "YES", None],
    ["country", "text", "YES", None],
    ["height_cm", "integer", "YES", None],
    ["weight_kg", "integer", "YES", None],
    ["confirmed_at", "timestamp with time zone", "YES", None],
    ["created_at", "timestamp with time zone", "NO", "now()"],
    ["updated_at", "timestamp with time zone", "NO", "now()"],
    ["embedding", "USER-DEFINED", "YES", None],  # vector(1024), V2
]


@pytest.fixture
def conn():
    url = urlparse(URL)
    connection = pg8000.native.Connection(
        user=unquote(url.username or ""),
        password=unquote(url.password or "") or None,
        host=url.hostname or "localhost",
        port=url.port or 5432,
        database=url.path.lstrip("/") or None,
    )
    schema = f"it_migrate_{uuid.uuid4().hex[:12]}"
    connection.run(f"CREATE SCHEMA {schema}")  # generated identifier, no user input
    connection.run(f"SET search_path TO {schema}, public")
    connection.schema = schema
    try:
        yield connection
    finally:
        connection.run(f"DROP SCHEMA {schema} CASCADE")
        connection.close()


def run(connection, action):
    return lf.run(connection, action, lf.MIGRATIONS_DIR, {"action": action, "applied": [], "current": None})


def test_v1_v2_on_postgresql_14(conn):
    version = conn.run("SHOW server_version_num")[0][0]
    assert 140000 <= int(version) < 150000, f"local server is not PostgreSQL 14: {version}"

    assert run(conn, "migrate") == {"applied": [1, 2], "current": 2}
    assert run(conn, "migrate") == {"applied": [], "current": 2}
    assert run(conn, "status") == {"current": 2, "pending": []}

    columns = conn.run(
        "SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns "
        "WHERE table_schema = :schema AND table_name = 'users' ORDER BY ordinal_position",
        schema=conn.schema,
    )
    assert columns == EXPECTED_COLUMNS
    embedding_type = conn.run(
        "SELECT format_type(a.atttypid, a.atttypmod) FROM pg_attribute a JOIN pg_class t ON t.oid = a.attrelid "
        "JOIN pg_namespace n ON n.oid = t.relnamespace "
        "WHERE n.nspname = :schema AND t.relname = 'users' AND a.attname = 'embedding'",
        schema=conn.schema,
    )
    assert embedding_type == [["vector(1024)"]]
    assert conn.run("SELECT count(*) FROM pg_extension WHERE extname = 'vector'") == [[1]]

    constraints = conn.run(
        "SELECT c.contype, a.attname FROM pg_constraint c "
        "JOIN pg_class t ON t.oid = c.conrelid JOIN pg_namespace n ON n.oid = t.relnamespace "
        "JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY (c.conkey) "
        "WHERE n.nspname = :schema AND t.relname = 'users'",
        schema=conn.schema,
    )
    assert constraints == [["p", "id"]]

    indexes = conn.run(
        "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = :schema AND tablename = 'users' "
        "ORDER BY indexname",
        schema=conn.schema,
    )
    assert [name for name, _ in indexes] == ["users_embedding_hnsw_idx", "users_pkey"]
    assert indexes[0][1].endswith("USING hnsw (embedding vector_l2_ops)")

    history = conn.run("SELECT version, description, checksum FROM schema_migrations ORDER BY version")
    migrations = lf.load_migrations(lf.MIGRATIONS_DIR)
    assert history == [[m.version, m.description, m.checksum] for m in migrations]
    assert [m.description for m in migrations] == ["create_users", "add_users_embedding"]
