"""User upsert of aws-challenge-sync for the EventBridge event aws-challenge.cognito / UserConfirmed (spec 07, ADR-016).

Reached through the dispatch in lambda_function.py. Validates `sub` and `email` (invalid -> outcome "rejected", no DB
call, no error: a retry cannot fix it), maps the registration attributes tolerantly (unparsable -> NULL, field name
logged) and runs one parameterised idempotent upsert into `users` (columns: spec 06). A database error raises, so
Lambda retries the asynchronous invocation. Rules: the user-sync skill.
"""

from __future__ import annotations

import json
import re
import time
from datetime import date, datetime, timezone
from typing import Any

import pg8000.native

import db

SOURCE = "aws-challenge.cognito"
DETAIL_TYPE = "UserConfirmed"
ERROR_FAILED = "USER_SYNC_FAILED"

UUID_PATTERN = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
INTEGER_PATTERN = re.compile(r"[+-]?[0-9]+")
INT_MIN, INT_MAX = -(2**31), 2**31 - 1

# Cognito attribute -> users column, stored as given (missing or empty string -> NULL).
TEXT_ATTRIBUTES = {
    "given_name": "given_name",
    "family_name": "family_name",
    "gender": "gender",
    "custom:country": "country",
}
INTEGER_ATTRIBUTES = {"custom:height": "height_cm", "custom:weight": "weight_kg"}

# One statement; values only as :name parameters (pg8000 native), never formatted into the SQL text.
SQL_UPSERT = (
    "INSERT INTO users (id, email, given_name, family_name, gender, birthdate, country, height_cm, weight_kg, "
    "confirmed_at) VALUES (CAST(:id AS uuid), CAST(:email AS text), CAST(:given_name AS text), "
    "CAST(:family_name AS text), CAST(:gender AS text), CAST(:birthdate AS date), CAST(:country AS text), "
    "CAST(:height_cm AS integer), CAST(:weight_kg AS integer), CAST(:confirmed_at AS timestamptz)) "
    "ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email, given_name = EXCLUDED.given_name, "
    "family_name = EXCLUDED.family_name, gender = EXCLUDED.gender, birthdate = EXCLUDED.birthdate, "
    "country = EXCLUDED.country, height_cm = EXCLUDED.height_cm, weight_kg = EXCLUDED.weight_kg, "
    "confirmed_at = EXCLUDED.confirmed_at, updated_at = now() "
    "RETURNING (xmax = 0) AS inserted"
)


class UserSyncError(Exception):
    """Function error after a database error; message USER_SYNC_FAILED: <SQLSTATE> (no foreign text, no values)."""


class Rejected(Exception):
    """The envelope cannot be stored (bad `sub` or `email`); args[0] is the field name."""


def is_user_confirmed(event: Any) -> bool:
    """Dispatch rule of spec 06 §Inputs for the upsert route."""
    return isinstance(event, dict) and event.get("source") == SOURCE and event.get("detail-type") == DETAIL_TYPE


def _present(value: Any) -> bool:
    return value is not None and value != ""


def _text(value: Any) -> tuple[str | None, bool]:
    """(column value, valid). Missing or empty -> NULL; a non-string value cannot be stored as given."""
    if not _present(value):
        return None, True
    if isinstance(value, str):
        return value, True
    return None, False


def _birthdate(value: Any) -> tuple[date | None, bool]:
    if not _present(value):
        return None, True
    if isinstance(value, str) and DATE_PATTERN.fullmatch(value):
        try:
            return date.fromisoformat(value), True
        except ValueError:  # e.g. 2000-02-31
            pass
    return None, False


def _integer(value: Any) -> tuple[int | None, bool]:
    """Optional sign + digits within PostgreSQL integer; stored even outside the SPA range."""
    if not _present(value):
        return None, True
    if isinstance(value, str) and INTEGER_PATTERN.fullmatch(value):
        try:
            number = int(value)
        except ValueError:  # more digits than int() converts (Python's int max str digits)
            return None, False
        if INT_MIN <= number <= INT_MAX:
            return number, True
    return None, False


def _timestamp(value: Any) -> tuple[datetime | None, bool]:
    """ISO-8601; a value without offset is taken as UTC (the contract says UTC)."""
    if not _present(value):
        return None, True
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None, False
        return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)), True
    return None, False


def map_detail(detail: Any) -> tuple[dict[str, Any], list[str]]:
    """Validate and map the event detail (spec 07 §Outputs) -> (upsert parameters, invalid field names).

    Raises Rejected("sub") / Rejected("email") when the row cannot be stored. Unknown keys are ignored.
    """
    if not isinstance(detail, dict):
        raise Rejected("sub")
    sub = detail.get("sub")
    if not isinstance(sub, str) or not UUID_PATTERN.fullmatch(sub):
        raise Rejected("sub")
    email = detail.get("email")
    email = email.strip().lower() if isinstance(email, str) else ""
    if not email:
        raise Rejected("email")

    invalid: list[str] = []
    attributes = detail.get("attributes")
    if not isinstance(attributes, dict):
        if attributes is not None:
            invalid.append("attributes")
        attributes = {}

    params: dict[str, Any] = {"id": sub.lower(), "email": email}
    for name, column in TEXT_ATTRIBUTES.items():
        params[column], valid = _text(attributes.get(name))
        if not valid:
            invalid.append(name)
    params["birthdate"], valid = _birthdate(attributes.get("birthdate"))
    if not valid:
        invalid.append("birthdate")
    for name, column in INTEGER_ATTRIBUTES.items():
        params[column], valid = _integer(attributes.get(name))
        if not valid:
            invalid.append(name)
    params["confirmed_at"], valid = _timestamp(detail.get("confirmedAt"))
    if not valid:
        invalid.append("confirmedAt")
    return params, invalid


def _sqlstate(exc: BaseException) -> str:
    detail = exc.args[0] if exc.args else None
    if isinstance(detail, dict) and detail.get("C"):
        return str(detail["C"])
    return "UNKNOWN"


def _log(context: Any, state: dict[str, Any], started: float, error: BaseException | None) -> None:
    # Field names and ids only; never the event detail or any attribute value (spec 07 §Outputs).
    outcome = state["outcome"] if error is None else "failure"
    line: dict[str, Any] = {
        "level": {"failure": "ERROR", "rejected": "WARNING"}.get(outcome, "INFO"),
        "message": state["message"],
        "function": getattr(context, "function_name", None),
        "awsRequestId": getattr(context, "aws_request_id", None),
        "eventId": state["eventId"],
        "userSub": state["userSub"],
        "outcome": outcome,
        "invalidFields": state["invalidFields"],
        "durationMs": round((time.monotonic() - started) * 1000),
    }
    if error is not None:
        known = isinstance(error, (UserSyncError, db.DbConnectError))
        line["message"] = str(error) if known else "unexpected error"
        line["errorClass"] = type(error.__cause__ or error).__name__
    print(json.dumps(line, separators=(",", ":")))


def handle(event: dict[str, Any], context: Any) -> dict[str, str]:
    started = time.monotonic()
    event_id = event.get("id")
    state: dict[str, Any] = {
        "eventId": event_id if isinstance(event_id, str) else None,
        "userSub": None,
        "outcome": None,
        "invalidFields": [],
        "message": "user synced",
    }
    conn = None
    error: BaseException | None = None
    try:
        detail = event.get("detail")
        try:
            params, state["invalidFields"] = map_detail(detail)
        except Rejected as rejected:
            sub = detail.get("sub") if isinstance(detail, dict) else None
            if isinstance(sub, str) and UUID_PATTERN.fullmatch(sub):
                state["userSub"] = sub.lower()
            state["invalidFields"] = [rejected.args[0]]
            state["outcome"] = "rejected"
            state["message"] = "event rejected"
            return {"outcome": "rejected"}
        state["userSub"] = params["id"]

        conn = db.connect()
        try:
            rows = conn.run(SQL_UPSERT, **params)
        except (pg8000.native.DatabaseError, pg8000.native.InterfaceError, OSError) as exc:
            raise UserSyncError(f"{ERROR_FAILED}: {_sqlstate(exc)}") from exc
        state["outcome"] = "inserted" if rows[0][0] else "updated"
        return {"outcome": state["outcome"]}
    except BaseException as exc:
        error = exc
        raise
    finally:
        db.close_quietly(conn)
        _log(context, state, started, error)
