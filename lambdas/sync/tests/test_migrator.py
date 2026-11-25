"""Unit tests of the migration runner (AC-06.2) — the database is the in-memory FakeConnection."""

import hashlib
import json
import re

import pg8000.native
import pytest

import db
import migrator as lf
from fake_db import FakeConnection


class Context:
    function_name = "aws-challenge-sync"
    aws_request_id = "req-123"


def write(directory, files):
    for name, content in files.items():
        data = content if isinstance(content, bytes) else content.encode("utf-8")
        (directory / name).write_bytes(data)
    return directory


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def migrate(conn, directory, action="migrate"):
    state = {"action": action, "applied": [], "current": None}
    return lf.run(conn, action, directory, state), state


# --- migrate / status ---------------------------------------------------------------------------------------------

def test_pending_files_applied_in_order_one_transaction_each_with_history_row(tmp_path):
    write(tmp_path, {"V2__second.sql": "SELECT 2;", "V1__first.sql": "SELECT 1;", "V10__tenth.sql": "SELECT 10;"})
    for v in range(3, 10):
        write(tmp_path, {f"V{v}__n{v}.sql": f"SELECT {v};"})
    conn = FakeConnection()

    result, _ = migrate(conn, tmp_path)

    assert result == {"applied": list(range(1, 11)), "current": 10}
    assert conn.history_table_created
    assert conn.executed == [f"SELECT {v};" for v in range(1, 11)]
    assert len(conn.transactions) == 10
    sql, rows = conn.transactions[0]
    assert sql == ["SELECT 1;"]
    assert rows == {1: ("first", sha("SELECT 1;"))}
    assert re.fullmatch(r"[0-9a-f]{64}", rows[1][1])


def test_nothing_pending_returns_empty_applied_and_changes_nothing(tmp_path):
    write(tmp_path, {"V1__first.sql": "SELECT 1;"})
    conn = FakeConnection(history={1: ("first", sha("SELECT 1;"))})

    result, _ = migrate(conn, tmp_path)

    assert result == {"applied": [], "current": 1}
    assert "BEGIN" not in conn.statements
    assert conn.executed == []


def test_status_reports_current_and_pending_without_applying(tmp_path):
    write(tmp_path, {"V1__first.sql": "SELECT 1;", "V2__second.sql": "SELECT 2;"})
    conn = FakeConnection(history={1: ("first", sha("SELECT 1;"))})

    result, _ = migrate(conn, tmp_path, action="status")

    assert result == {"current": 1, "pending": [2]}
    assert "BEGIN" not in conn.statements
    assert conn.executed == []


def test_status_on_empty_database_is_current_zero(tmp_path):
    write(tmp_path, {"V1__first.sql": "SELECT 1;"})
    result, _ = migrate(FakeConnection(), tmp_path, action="status")
    assert result == {"current": 0, "pending": [1]}


def test_status_with_no_files_and_no_history(tmp_path):
    result, _ = migrate(FakeConnection(), tmp_path, action="status")
    assert result == {"current": 0, "pending": []}


# --- invalid files ------------------------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "bad_name",
    [
        "V01__lead_zero.sql",
        "V0__zero.sql",
        "V1_single_underscore.sql",
        "V1__Upper.sql",
        "V1__with-dash.sql",
        "v1__lower_v.sql",
        "V1__.sql",
        "V1__first.txt",
        "README.md",
    ],
)
def test_bad_file_name_is_invalid_and_nothing_applied(tmp_path, bad_name):
    write(tmp_path, {"V1__first.sql": "SELECT 1;", bad_name: "SELECT 0;"})
    conn = FakeConnection()

    with pytest.raises(lf.MigrationError) as raised:
        migrate(conn, tmp_path)

    assert str(raised.value) == f"MIGRATION_INVALID_FILES: {bad_name}"
    assert conn.executed == [] and "BEGIN" not in conn.statements


def test_subdirectory_is_invalid(tmp_path):
    write(tmp_path, {"V1__first.sql": "SELECT 1;"})
    (tmp_path / "old").mkdir()
    with pytest.raises(lf.MigrationError, match="^MIGRATION_INVALID_FILES: old$"):
        migrate(FakeConnection(), tmp_path)


@pytest.mark.parametrize(
    ("files", "reported"),
    [
        ({"V1__a.sql": "SELECT 1;", "V3__c.sql": "SELECT 3;"}, "V3__c.sql"),  # gap
        ({"V2__b.sql": "SELECT 2;"}, "V2__b.sql"),  # V1 missing
        ({"V1__a.sql": "SELECT 1;", "V1__b.sql": "SELECT 1;", "V2__c.sql": "SELECT 2;"}, "V1__b.sql"),  # duplicate
    ],
)
def test_version_gap_or_duplicate_is_invalid_and_nothing_applied(tmp_path, files, reported):
    write(tmp_path, files)
    conn = FakeConnection()

    with pytest.raises(lf.MigrationError) as raised:
        migrate(conn, tmp_path)

    assert str(raised.value) == f"MIGRATION_INVALID_FILES: {reported}"
    assert conn.executed == [] and "BEGIN" not in conn.statements


def test_non_utf8_file_is_invalid(tmp_path):
    write(tmp_path, {"V1__latin1.sql": "SELECT 'café';".encode("latin-1")})
    with pytest.raises(lf.MigrationError, match="^MIGRATION_INVALID_FILES: V1__latin1.sql$"):
        migrate(FakeConnection(), tmp_path)


# --- checksum -----------------------------------------------------------------------------------------------------

def test_checksum_mismatch_of_applied_file_stops_before_anything_is_applied(tmp_path):
    write(tmp_path, {"V1__first.sql": "SELECT 1; -- edited", "V2__second.sql": "SELECT 2;"})
    conn = FakeConnection(history={1: ("first", sha("SELECT 1;"))})

    with pytest.raises(lf.MigrationError) as raised:
        migrate(conn, tmp_path)

    assert str(raised.value) == "MIGRATION_CHECKSUM_MISMATCH: V1"
    assert conn.executed == [] and "BEGIN" not in conn.statements


def test_checksum_mismatch_also_fails_status(tmp_path):
    write(tmp_path, {"V1__first.sql": "SELECT 1; -- edited"})
    conn = FakeConnection(history={1: ("first", sha("SELECT 1;"))})
    with pytest.raises(lf.MigrationError, match="^MIGRATION_CHECKSUM_MISMATCH: V1$"):
        migrate(conn, tmp_path, action="status")


def test_applied_version_without_file_is_checksum_mismatch(tmp_path):
    write(tmp_path, {"V1__first.sql": "SELECT 1;"})
    conn = FakeConnection(history={1: ("first", sha("SELECT 1;")), 2: ("gone", sha("SELECT 2;"))})
    with pytest.raises(lf.MigrationError, match="^MIGRATION_CHECKSUM_MISMATCH: V2$"):
        migrate(conn, tmp_path)


# --- lock and concurrency -----------------------------------------------------------------------------------------

def test_lock_not_acquired_is_migration_locked_and_nothing_applied(tmp_path):
    write(tmp_path, {"V1__first.sql": "SELECT 1;"})
    conn = FakeConnection(lock_available=False)

    with pytest.raises(lf.MigrationError, match="^MIGRATION_LOCKED$"):
        migrate(conn, tmp_path)

    assert conn.executed == [] and conn.history == {}
    assert conn.rollbacks == 1


def test_version_applied_by_a_parallel_run_is_skipped(tmp_path):
    write(tmp_path, {"V1__first.sql": "SELECT 1;"})
    conn = FakeConnection(applied_meanwhile={1})

    result, _ = migrate(conn, tmp_path)

    assert result == {"applied": [], "current": 1}
    assert conn.executed == []


# --- SQL error ----------------------------------------------------------------------------------------------------

def test_sql_error_rolls_back_only_the_failing_file(tmp_path):
    write(
        tmp_path,
        {"V1__first.sql": "SELECT 1;", "V2__broken.sql": "SELEC broken;", "V3__third.sql": "SELECT 3;"},
    )
    conn = FakeConnection(fail_on="SELEC broken")

    with pytest.raises(lf.MigrationError) as raised:
        migrate(conn, tmp_path)

    assert str(raised.value) == "MIGRATION_FAILED: V2 42601"
    assert isinstance(raised.value.__cause__, pg8000.native.DatabaseError)
    assert conn.executed == ["SELECT 1;"]
    assert set(conn.history) == {1}
    assert conn.rollbacks == 1
    assert "SELECT 3;" not in conn.statements


def lost(message="network error"):
    return pg8000.native.InterfaceError(message)


@pytest.mark.parametrize(
    ("marker", "exception"),
    [
        ("SELECT 2;", lost()),  # connection dropped while the file runs
        ("SELECT 2;", TimeoutError("timed out")),  # raw socket timeout (pg8000 does not wrap every read)
        (lf.SQL_INSERT_HISTORY, lost()),
        ("COMMIT", lost()),
    ],
)
def test_lost_connection_during_a_file_is_migration_failed_unknown(tmp_path, marker, exception):
    write(tmp_path, {"V1__first.sql": "SELECT 1;", "V2__second.sql": "SELECT 2;", "V3__third.sql": "SELECT 3;"})
    # COMMIT of V1 must succeed: lose the connection only from V2 on.
    conn = FakeConnection(history={1: ("first", sha("SELECT 1;"))}, lost_on=(marker, exception))

    with pytest.raises(lf.MigrationError) as raised:
        migrate(conn, tmp_path)

    assert str(raised.value) == "MIGRATION_FAILED: V2 UNKNOWN"
    assert raised.value.__cause__ is exception
    assert set(conn.history) == {1}
    assert conn.rollbacks == 1
    assert "SELECT 3;" not in conn.statements


def test_rollback_failure_after_lost_connection_is_swallowed(tmp_path):
    write(tmp_path, {"V1__first.sql": "SELECT 1;"})

    class DeadAfterFile(FakeConnection):
        def run(self, sql, **params):
            if sql == "ROLLBACK":
                raise lost("connection is closed")
            return super().run(sql, **params)

    conn = DeadAfterFile(lost_on=("SELECT 1;", lost()))
    with pytest.raises(lf.MigrationError, match="^MIGRATION_FAILED: V1 UNKNOWN$"):
        migrate(conn, tmp_path)


# --- handler ------------------------------------------------------------------------------------------------------

def log_lines(capsys):
    out = capsys.readouterr().out.strip().splitlines()
    return [json.loads(line) for line in out]


@pytest.fixture
def no_connect(monkeypatch):
    def forbidden(**kwargs):
        raise AssertionError("must not connect")

    monkeypatch.setattr(db, "connect", forbidden)


@pytest.mark.parametrize(
    "event",
    [None, [], "migrate", {}, {"action": "drop"}, {"action": 1}, {"action": "MIGRATE"},
     {"action": "migrate", "extra": True}],
)
def test_bad_request_without_connecting(event, no_connect, capsys):
    with pytest.raises(lf.MigrationError, match="^MIGRATION_BAD_REQUEST$"):
        lf.handle(event, Context())

    (line,) = log_lines(capsys)
    assert line["outcome"] == "failure"
    assert line["message"] == "MIGRATION_BAD_REQUEST"
    assert line["errorClass"] == "MigrationError"


def test_handler_migrates_packaged_files_closes_connection_and_logs_one_line(monkeypatch, capsys):
    conn = FakeConnection()
    monkeypatch.setattr(db, "connect", lambda **kwargs: conn)

    result = lf.handle({"action": "migrate"}, Context())

    assert result == {"applied": [1, 2], "current": 2}
    assert conn.closed
    (line,) = log_lines(capsys)
    assert {k: line[k] for k in ("level", "function", "awsRequestId", "action", "applied", "current", "outcome")} == {
        "level": "INFO",
        "function": "aws-challenge-sync",
        "awsRequestId": "req-123",
        "action": "migrate",
        "applied": [1, 2],
        "current": 2,
        "outcome": "success",
    }
    assert isinstance(line["durationMs"], int)
    assert "errorClass" not in line


def test_handler_connects_with_the_long_migration_timeout(monkeypatch, capsys):
    calls = []

    def connect(**kwargs):
        calls.append(kwargs)
        return FakeConnection()

    monkeypatch.setattr(db, "connect", connect)
    lf.handle({"action": "status"}, Context())

    assert calls == [{"timeout": 55.0}]
    assert lf.DB_TIMEOUT_S == 55.0 > db.DEFAULT_TIMEOUT_S


def test_handler_lost_connection_logs_stable_error_without_foreign_message(monkeypatch, capsys, tmp_path):
    write(tmp_path, {"V1__first.sql": "SELECT 1;"})
    monkeypatch.setattr(lf, "MIGRATIONS_DIR", tmp_path)
    conn = FakeConnection(lost_on=("SELECT 1;", pg8000.native.InterfaceError("network error at 10.0.0.1")))
    monkeypatch.setattr(db, "connect", lambda **kwargs: conn)

    with pytest.raises(lf.MigrationError, match="^MIGRATION_FAILED: V1 UNKNOWN$"):
        lf.handle({"action": "migrate"}, Context())

    assert conn.closed
    (line,) = log_lines(capsys)
    assert line["message"] == "MIGRATION_FAILED: V1 UNKNOWN"
    assert line["errorClass"] == "InterfaceError"
    assert line["applied"] == [] and line["outcome"] == "failure"
    assert "10.0.0.1" not in json.dumps(line)


def test_handler_status(monkeypatch, capsys):
    conn = FakeConnection()
    monkeypatch.setattr(db, "connect", lambda **kwargs: conn)
    assert lf.handle({"action": "status"}, Context()) == {"current": 0, "pending": [1, 2]}
    assert conn.closed


def test_handler_connect_failure_is_db_connect_failed(monkeypatch, capsys):
    def failing(**kwargs):
        try:
            raise pg8000.native.InterfaceError("Server refuses SSL")
        except pg8000.native.InterfaceError as exc:
            raise db.DbConnectError() from exc

    monkeypatch.setattr(db, "connect", failing)

    with pytest.raises(db.DbConnectError, match="^DB_CONNECT_FAILED$"):
        lf.handle({"action": "migrate"}, Context())

    (line,) = log_lines(capsys)
    assert line["message"] == "DB_CONNECT_FAILED"
    assert line["errorClass"] == "InterfaceError"
    assert line["outcome"] == "failure"


def test_handler_sql_failure_logs_progress_and_closes(monkeypatch, capsys, tmp_path):
    write(tmp_path, {"V1__first.sql": "SELECT 1;", "V2__broken.sql": "SELEC broken;"})
    monkeypatch.setattr(lf, "MIGRATIONS_DIR", tmp_path)
    conn = FakeConnection(fail_on="SELEC broken")
    monkeypatch.setattr(db, "connect", lambda **kwargs: conn)

    with pytest.raises(lf.MigrationError, match="^MIGRATION_FAILED: V2 42601$"):
        lf.handle({"action": "migrate"}, Context())

    assert conn.closed
    (line,) = log_lines(capsys)
    assert line["applied"] == [1] and line["current"] == 1
    assert line["errorClass"] == "DatabaseError"
    assert "SELEC" not in json.dumps(line)


def test_unexpected_error_message_is_not_logged(monkeypatch, capsys):
    class Exploding(FakeConnection):
        def run(self, sql, **params):
            raise RuntimeError("value 'secret@example.com' leaked")

    conn = Exploding()
    monkeypatch.setattr(db, "connect", lambda **kwargs: conn)

    with pytest.raises(RuntimeError):
        lf.handle({"action": "status"}, Context())

    (line,) = log_lines(capsys)
    assert line["message"] == "unexpected error"
    assert line["errorClass"] == "RuntimeError"
    assert "secret" not in json.dumps(line)
    assert conn.closed


# --- the packaged migrations (AC-06.1, static part) ---------------------------------------------------------------

EXPECTED_USERS_COLUMNS = [
    ("id", "uuid NOT NULL PRIMARY KEY"),
    ("email", "text NOT NULL"),
    ("given_name", "text"),
    ("family_name", "text"),
    ("gender", "text"),
    ("birthdate", "date"),
    ("country", "text"),
    ("height_cm", "integer"),
    ("weight_kg", "integer"),
    ("confirmed_at", "timestamptz"),
    ("created_at", "timestamptz NOT NULL DEFAULT now()"),
    ("updated_at", "timestamptz NOT NULL DEFAULT now()"),
]


def test_packaged_migrations_are_valid():
    migrations = lf.load_migrations(lf.MIGRATIONS_DIR)
    assert [(m.version, m.file_name) for m in migrations] == [
        (1, "V1__create_users.sql"), (2, "V2__add_users_embedding.sql")]


def test_v1_creates_users_exactly_as_spec_06():
    sql = (lf.MIGRATIONS_DIR / "V1__create_users.sql").read_text(encoding="utf-8")
    code = "\n".join(line.split("--", 1)[0] for line in sql.splitlines())
    body = re.fullmatch(r"\s*CREATE TABLE users \((.*)\);\s*", code, flags=re.DOTALL)
    assert body, "V1 must contain exactly one CREATE TABLE users statement"
    columns = [" ".join(part.split()) for part in body.group(1).split(",")]
    assert [tuple(c.split(" ", 1)) for c in columns] == EXPECTED_USERS_COLUMNS
    assert not re.search(r"\b(CHECK|UNIQUE|INDEX|REFERENCES|embedding)\b", code, flags=re.IGNORECASE)


# Checksum of V1 as applied in AWS (T03-03); V1 must stay byte-identical (spec 10 AC-10.1).
V1_SHA256 = "9800e6e7c23943e75c048331bfbe393159fa518fdb0734fb28e61e144fa9a5c7"


def test_v1_is_byte_identical_to_the_applied_file():
    assert hashlib.sha256((lf.MIGRATIONS_DIR / "V1__create_users.sql").read_bytes()).hexdigest() == V1_SHA256


def test_v2_adds_exactly_extension_column_and_hnsw_index():
    """AC-10.1, static part: extension vector, nullable users.embedding vector(1024), HNSW index with vector_l2_ops."""
    raw = (lf.MIGRATIONS_DIR / "V2__add_users_embedding.sql").read_bytes()
    assert b"\r" not in raw  # LF only (.gitattributes), so the checksum is the same on every checkout
    code = "\n".join(line.split("--", 1)[0] for line in raw.decode("utf-8").splitlines())
    statements = [" ".join(part.split()) for part in code.split(";") if part.strip()]
    assert statements == [
        "CREATE EXTENSION IF NOT EXISTS vector",
        "ALTER TABLE users ADD COLUMN embedding vector(1024)",
        "CREATE INDEX users_embedding_hnsw_idx ON users USING hnsw (embedding vector_l2_ops)",
    ]
    assert not re.search(r"\b(BEGIN|COMMIT|ROLLBACK|CONCURRENTLY|NOT NULL)\b", code, flags=re.IGNORECASE)
