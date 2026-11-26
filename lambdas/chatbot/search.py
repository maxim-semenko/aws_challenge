"""Database side of POST /chat: the vector query, the execution of a guarded statement and the value mapping.

Contract: spec 12 §Outputs (vector query, columns, value mapping) and §Behaviour 3-5. Every statement runs inside
`BEGIN READ ONLY` + `SET LOCAL statement_timeout = '4s'` and is always rolled back; one connection per request
(shared db.py, socket timeout 5 s), closed in `finally`. Values only as pg8000 parameters. Rules: the chatbot-api
skill.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any, TypeVar
from uuid import UUID

import pg8000.native

import db
import embeddings

DB_TIMEOUT_S = 5.0
SQL_BEGIN = "BEGIN READ ONLY"
SQL_STATEMENT_TIMEOUT = "SET LOCAL statement_timeout = '4s'"
SQL_ROLLBACK = "ROLLBACK"

VECTOR_ROWS = 5
ROW_CAP = 100  # SQL mode; the guard sets LIMIT 101 so a 101st row means "truncated"
# The curriculum query (W5-G2), the vector passed as a parameter; never the `embedding` column in the result.
SQL_VECTOR = (
    "SELECT id, email, given_name, family_name, gender, birthdate, country, height_cm, weight_kg, "
    "embedding <-> CAST(:q AS vector) AS distance FROM users "
    "ORDER BY embedding <-> CAST(:q AS vector) LIMIT 5"
)
VECTOR_COLUMNS = (
    "id", "email", "givenName", "familyName", "gender", "birthdate", "country", "heightCm", "weightKg", "distance",
)

T = TypeVar("T")
Scalar = str | int | float | bool | None


class StatementError(Exception):
    """The guarded statement failed in PostgreSQL (SQL error or statement_timeout); __cause__ is the DB error."""


# --- value mapping (spec 12 §Outputs) --------------------------------------------------------------------------------


def _seconds_text(micros: int) -> str:
    sign = "-" if micros < 0 else ""
    micros = abs(micros)
    hours, rest = divmod(micros, 3_600_000_000)
    minutes, rest = divmod(rest, 60_000_000)
    seconds, fraction = divmod(rest, 1_000_000)
    text = f"{sign}{hours:02d}:{minutes:02d}:{seconds:02d}"
    return text + (f".{fraction:06d}".rstrip("0") if fraction else "")


def interval_text(months: int, days: int, micros: int) -> str:
    """PostgreSQL `postgres` IntervalStyle text of an interval (e.g. `1 year 2 mons 3 days 04:05:06`)."""
    years, mons = int(months / 12), months - int(months / 12) * 12
    parts: list[str] = []
    negative_before = False
    for value, unit in ((years, "year"), (mons, "mon"), (days, "day")):
        if value:
            plus = "+" if negative_before and value > 0 else ""
            parts.append(f"{plus}{value} {unit}{'' if value == 1 else 's'}")
            negative_before = value < 0
    if micros or not parts:
        plus = "+" if negative_before and micros > 0 else ""
        parts.append(plus + _seconds_text(micros))
    return " ".join(parts)


def _interval(value: Any) -> str:
    if isinstance(value, timedelta):  # pg8000 already merged days and time; one sign for both parts
        sign = -1 if value < timedelta(0) else 1
        magnitude = abs(value)
        return interval_text(
            0, sign * magnitude.days, sign * (magnitude.seconds * 1_000_000 + magnitude.microseconds)
        )
    # pg8000.types.PGInterval: an interval with months or years (no timedelta equivalent)
    months = sum(int(getattr(value, name) or 0) * factor for name, factor in (
        ("millennia", 12000), ("centuries", 1200), ("decades", 120), ("years", 12), ("months", 1)))
    days = int(getattr(value, "weeks") or 0) * 7 + int(getattr(value, "days") or 0)
    micros = sum(int(getattr(value, name) or 0) * factor for name, factor in (
        ("hours", 3_600_000_000), ("minutes", 60_000_000), ("seconds", 1_000_000), ("microseconds", 1)))
    micros += int(getattr(value, "milliseconds", 0) or 0) * 1000
    return interval_text(months, days, micros)


def _float(value: float) -> Scalar:
    if math.isfinite(value):
        return value
    return "NaN" if math.isnan(value) else ("Infinity" if value > 0 else "-Infinity")


def to_json(value: Any) -> Scalar:
    """One database value -> JSON scalar: numbers as numbers (non-finite as text), date `YYYY-MM-DD`, timestamptz
    UTC `YYYY-MM-DDTHH:MM:SSZ`, uuid as string, interval and anything else as its PostgreSQL text form, NULL null."""
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return _float(value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            return "NaN" if value.is_nan() else ("Infinity" if value > 0 else "-Infinity")
        return int(value) if value == value.to_integral_value() else _float(float(value))
    if isinstance(value, datetime):
        if value.tzinfo is None:  # timestamp without time zone: PostgreSQL text form
            return str(value)
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, timedelta) or type(value).__name__ == "PGInterval":
        return _interval(value)
    if isinstance(value, time):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray, memoryview)):
        return "\\x" + bytes(value).hex()
    return str(value)


# --- transactions ------------------------------------------------------------------------------------------------------


def _read_only(conn: Any, work: Callable[[], T]) -> T:
    """Run `work` inside BEGIN READ ONLY + SET LOCAL statement_timeout; always ROLLBACK (errors there are ignored)."""
    conn.run(SQL_BEGIN)
    try:
        conn.run(SQL_STATEMENT_TIMEOUT)
        return work()
    finally:
        try:
            conn.run(SQL_ROLLBACK)
        except Exception:
            pass  # the connection is closed right after; the original error (if any) is kept


def sqlstate(exc: BaseException) -> str:
    detail = exc.args[0] if exc.args else None
    if isinstance(detail, dict) and detail.get("C"):
        return str(detail["C"])
    return "UNKNOWN"


# --- the two paths -----------------------------------------------------------------------------------------------------


def similar_users(vector: list[float]) -> list[list[Scalar]]:
    """The five nearest users to `vector` (rows with a NULL distance dropped), mapped in VECTOR_COLUMNS order."""
    conn = None
    try:
        conn = db.connect(timeout=DB_TIMEOUT_S)
        connection = conn
        literal = embeddings.to_vector_literal(vector)
        rows = _read_only(connection, lambda: connection.run(SQL_VECTOR, q=literal))
    finally:
        db.close_quietly(conn)
    return [[to_json(value) for value in row] for row in rows if row[-1] is not None][:VECTOR_ROWS]


def run_statement(sql: str) -> tuple[list[str], list[list[Scalar]], bool]:
    """Execute the guard's rendering (extended protocol: PostgreSQL itself accepts only one statement).

    Returns (column labels, at most 100 mapped rows, truncated). A DatabaseError with a SQLSTATE outside class 08
    (connection exception) becomes StatementError; connection problems stay as they are (500).
    """
    conn = None
    try:
        conn = db.connect(timeout=DB_TIMEOUT_S)
        connection = conn

        def execute() -> Any:
            try:
                return connection.execute_unnamed(sql)
            except pg8000.native.DatabaseError as exc:
                if sqlstate(exc).startswith("08"):
                    raise
                raise StatementError() from exc

        context = _read_only(connection, execute)
    finally:
        db.close_quietly(conn)
    columns = [str(column.get("name")) for column in (context.columns or [])]
    rows = list(context.rows or [])
    truncated = len(rows) > ROW_CAP
    return columns, [[to_json(value) for value in row] for row in rows[:ROW_CAP]], truncated
