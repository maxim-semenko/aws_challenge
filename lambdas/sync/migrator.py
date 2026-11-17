"""Migration runner of aws-challenge-sync, reached through the dispatch in lambda_function.py (spec 06, ADR-017).

Applies the versioned SQL migrations in ./migrations. Invoked by the owner from the Lambda console Test tab of
aws-challenge-sync with {"action": "migrate"} or {"action": "status"}.
Contract (results, error messages, log line): docs/specs/06-users-table-and-migrations.md. Rules: the
postgres-migrations skill.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pg8000.native

import db

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
FILE_NAME = re.compile(r"^V([1-9][0-9]*)__([a-z0-9_]+)\.sql$")
ACTIONS = ("migrate", "status")
# Fixed key of the transaction-level advisory lock that serialises migration runs.
LOCK_KEY = 7302170601
# Socket timeout for the whole run: a migration statement may take longer than the shared 10 s default; stays below
# the function timeout (60 s) so a hung read ends as MIGRATION_FAILED, not as a Lambda timeout.
DB_TIMEOUT_S = 55.0

SQL_CREATE_HISTORY = (
    "CREATE TABLE IF NOT EXISTS schema_migrations ("
    "version integer PRIMARY KEY, "
    "description text NOT NULL, "
    "checksum text NOT NULL, "
    "applied_at timestamptz NOT NULL DEFAULT now())"
)
SQL_SELECT_APPLIED = "SELECT version, checksum FROM schema_migrations ORDER BY version"
SQL_TRY_LOCK = "SELECT pg_try_advisory_xact_lock(CAST(:key AS bigint))"
SQL_IS_APPLIED = "SELECT 1 FROM schema_migrations WHERE version = :version"
SQL_INSERT_HISTORY = (
    "INSERT INTO schema_migrations (version, description, checksum) VALUES (:version, :description, :checksum)"
)


class MigrationError(Exception):
    """Function error whose message is one of the spec 06 error strings."""


@dataclass(frozen=True)
class Migration:
    version: int
    description: str
    file_name: str
    checksum: str
    sql: str


def load_migrations(directory: Path) -> list[Migration]:
    """Read and validate every file in the directory: names, versions 1..n without gap or duplicate, UTF-8."""
    parsed: list[tuple[int, str, Path]] = []
    for path in sorted(directory.iterdir(), key=lambda p: p.name):
        match = FILE_NAME.fullmatch(path.name)
        if not path.is_file() or match is None:
            raise MigrationError(f"MIGRATION_INVALID_FILES: {path.name}")
        parsed.append((int(match.group(1)), match.group(2), path))

    parsed.sort(key=lambda item: (item[0], item[2].name))
    migrations: list[Migration] = []
    for index, (version, description, path) in enumerate(parsed):
        if version != index + 1:  # covers a gap, a missing V1 and a duplicate version
            raise MigrationError(f"MIGRATION_INVALID_FILES: {path.name}")
        content = path.read_bytes()
        try:
            sql = content.decode("utf-8")
        except UnicodeDecodeError:
            raise MigrationError(f"MIGRATION_INVALID_FILES: {path.name}") from None
        migrations.append(
            Migration(version, description, path.name, hashlib.sha256(content).hexdigest(), sql)
        )
    return migrations


def _sqlstate(exc: Exception) -> str:
    detail = exc.args[0] if exc.args else None
    if isinstance(detail, dict) and detail.get("C"):
        return str(detail["C"])
    return "UNKNOWN"


def _rollback_quietly(conn: Any) -> None:
    try:
        conn.run("ROLLBACK")
    except Exception:
        pass


def _apply(conn: Any, migration: Migration) -> bool:
    """Apply one migration in its own transaction; False if a parallel run applied it meanwhile.

    A server error maps to MIGRATION_FAILED: V<n> <SQLSTATE>; a lost connection or socket timeout (pg8000
    InterfaceError, or a raw OSError such as TimeoutError) has no SQLSTATE and maps to MIGRATION_FAILED: V<n> UNKNOWN,
    so no foreign message reaches the caller. The file is one transaction: it is either fully applied or not at all
    (`status` shows which after a lost connection).
    """
    try:
        conn.run("BEGIN")
        locked = conn.run(SQL_TRY_LOCK, key=LOCK_KEY)[0][0]
        if not locked:
            raise MigrationError("MIGRATION_LOCKED")
        if conn.run(SQL_IS_APPLIED, version=migration.version):
            conn.run("ROLLBACK")
            return False
        conn.execute_simple(migration.sql)
        conn.run(
            SQL_INSERT_HISTORY,
            version=migration.version,
            description=migration.description,
            checksum=migration.checksum,
        )
        conn.run("COMMIT")
        return True
    except pg8000.native.DatabaseError as exc:
        _rollback_quietly(conn)
        raise MigrationError(f"MIGRATION_FAILED: V{migration.version} {_sqlstate(exc)}") from exc
    except (pg8000.native.InterfaceError, OSError) as exc:
        _rollback_quietly(conn)
        raise MigrationError(f"MIGRATION_FAILED: V{migration.version} UNKNOWN") from exc
    except BaseException:
        _rollback_quietly(conn)
        raise


def run(conn: Any, action: str, directory: Path, state: dict[str, Any]) -> dict[str, Any]:
    """Run `action` on an open connection; `state` receives applied/current progress for the log line."""
    conn.run(SQL_CREATE_HISTORY)
    migrations = load_migrations(directory)
    applied = {int(version): checksum for version, checksum in conn.run(SQL_SELECT_APPLIED)}
    state["current"] = max(applied, default=0)

    by_version = {m.version: m for m in migrations}
    for version in sorted(applied):
        migration = by_version.get(version)
        if migration is None or migration.checksum != applied[version]:
            raise MigrationError(f"MIGRATION_CHECKSUM_MISMATCH: V{version}")

    pending = [m for m in migrations if m.version not in applied]
    if action == "status":
        return {"current": state["current"], "pending": [m.version for m in pending]}

    for migration in pending:
        if _apply(conn, migration):
            state["applied"].append(migration.version)
        state["current"] = max(state["current"], migration.version)
    return {"applied": list(state["applied"]), "current": state["current"]}


def _parse_action(event: Any) -> str:
    if not isinstance(event, dict) or set(event) != {"action"} or event["action"] not in ACTIONS:
        raise MigrationError("MIGRATION_BAD_REQUEST")
    return event["action"]


def _error_class(exc: BaseException) -> str:
    return type(exc.__cause__ or exc).__name__


def _log(context: Any, state: dict[str, Any], started: float, error: BaseException | None) -> None:
    line: dict[str, Any] = {
        "level": "INFO" if error is None else "ERROR",
        "message": "migration run completed",
        "function": getattr(context, "function_name", None),
        "awsRequestId": getattr(context, "aws_request_id", None),
        "action": state["action"],
        "applied": state["applied"],
        "current": state["current"],
        "outcome": "success" if error is None else "failure",
        "durationMs": round((time.monotonic() - started) * 1000),
    }
    if error is not None:
        # Only our own error strings are logged; foreign messages may contain SQL values.
        known = isinstance(error, (MigrationError, db.DbConnectError))
        line["message"] = str(error) if known else "unexpected error"
        line["errorClass"] = _error_class(error)
    print(json.dumps(line, separators=(",", ":")))


def handle(event: Any, context: Any) -> dict[str, Any]:
    started = time.monotonic()
    state: dict[str, Any] = {"action": None, "applied": [], "current": None}
    conn = None
    error: BaseException | None = None
    try:
        state["action"] = _parse_action(event)
        conn = db.connect(timeout=DB_TIMEOUT_S)
        return run(conn, state["action"], MIGRATIONS_DIR, state)
    except BaseException as exc:
        error = exc
        raise
    finally:
        db.close_quietly(conn)
        _log(context, state, started, error)
