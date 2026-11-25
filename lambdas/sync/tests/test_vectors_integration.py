"""Optional integration test of seed, embed-missing and similar on local PostgreSQL 14 + pgvector (spec 10, 11).

Skipped unless MIGRATE_TEST_DATABASE_URL is set (docker compose up -d), e.g.
    MIGRATE_TEST_DATABASE_URL=postgresql://app:app@localhost:5432/aws_challenge
Applies V1+V2 in a throw-away schema (dropped at the end); Bedrock is the StubBedrock double with distinct vectors.
"""

import os
import uuid
from urllib.parse import unquote, urlparse

import pg8000.native
import pytest

import db
import embeddings
import migrator
import vectors

URL = os.environ.get("MIGRATE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="MIGRATE_TEST_DATABASE_URL not set")


class Context:
    function_name = "aws-challenge-sync"
    aws_request_id = "it"

    def get_remaining_time_in_millis(self):
        return 50_000


class Unclosable:
    def __init__(self, conn):
        self._conn = conn

    def run(self, sql, **params):
        return self._conn.run(sql, **params)

    def close(self):
        pass


class CountingBedrock:
    """Distinct deterministic vectors per call (call n -> spike at position n, plus a small common component)."""

    def __init__(self):
        self.calls = 0

    def invoke_model(self, **kwargs):
        import io
        import json

        vector = [0.01] * embeddings.DIMENSIONS
        vector[self.calls % embeddings.DIMENSIONS] = 1.0
        self.calls += 1
        return {"body": io.BytesIO(json.dumps({"embedding": vector}).encode())}


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
    schema = f"it_vec_{uuid.uuid4().hex[:12]}"
    connection.run(f"CREATE SCHEMA {schema}")  # generated identifier, no user input
    connection.run(f"SET search_path TO {schema}, public")
    migrator.run(connection, "migrate", migrator.MIGRATIONS_DIR, {"action": "migrate", "applied": [], "current": None})
    monkeypatch.setattr(db, "connect", lambda **kwargs: Unclosable(connection))
    monkeypatch.setattr(embeddings, "_bedrock_client", CountingBedrock())
    try:
        yield connection
    finally:
        connection.run("RESET enable_seqscan")
        connection.run(f"DROP SCHEMA {schema} CASCADE")
        connection.close()


def test_seed_embed_missing_and_similar_on_postgresql_14(conn):
    assert vectors.handle({"action": "seed", "count": 30}, Context()) == {"inserted": 30, "seeded": 30}
    assert vectors.handle({"action": "seed", "count": 30}, Context()) == {"inserted": 0, "seeded": 30}

    result = vectors.handle({"action": "embed-missing"}, Context())
    assert result == {"embedded": 30, "skipped": 0, "failed": 0, "remaining": 0, "stopped": "done"}

    target = str(uuid.uuid5(vectors.SEED_NAMESPACE, "seed-7"))
    similar = vectors.handle({"action": "similar", "userId": target}, Context())
    assert (similar["rows"], similar["withEmbedding"]) == (30, 30)
    assert len(similar["items"]) == 5
    assert similar["items"][0]["id"] == target and similar["items"][0]["distance"] < 1e-6
    distances = [item["distance"] for item in similar["items"]]
    assert distances == sorted(distances)
    assert similar["indexForced"]["scan"] == "Index Scan using users_embedding_hnsw_idx"
    assert similar["default"]["executionMs"] >= 0 and similar["indexForced"]["executionMs"] >= 0
    # SET LOCAL did not outlive the call
    assert conn.run("SHOW enable_seqscan") == [["on"]]
