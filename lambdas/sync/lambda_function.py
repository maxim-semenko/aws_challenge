"""aws-challenge-sync: routes each event by the dispatch table of spec 06 §Inputs (ADR-017).

- a JSON object whose top-level "action" is embed-missing, seed or similar -> vector actions (vectors.py, specs 10, 11)
- any other JSON object with a top-level key "action" -> the migration runner (migrator.py), owner's console Test tab
- source "aws-challenge.cognito" + detail-type "UserConfirmed" -> user upsert (user_sync.py, spec 07)
- anything else -> function error UNSUPPORTED_EVENT, one log line, no DB connection
"""

from __future__ import annotations

import json
import time
from typing import Any

import migrator
import user_sync
import vectors

UNSUPPORTED_EVENT = "UNSUPPORTED_EVENT"


class UnsupportedEventError(Exception):
    """Function error for an event that matches no route of the dispatch table."""


def _log_unsupported(context: Any, started: float) -> None:
    # Never the event content (it may hold personal data).
    line = {
        "level": "ERROR",
        "message": UNSUPPORTED_EVENT,
        "function": getattr(context, "function_name", None),
        "awsRequestId": getattr(context, "aws_request_id", None),
        "outcome": "failure",
        "durationMs": round((time.monotonic() - started) * 1000),
    }
    print(json.dumps(line, separators=(",", ":")))


def lambda_handler(event: Any, context: Any) -> Any:
    started = time.monotonic()
    if isinstance(event, dict) and "action" in event:
        if isinstance(event["action"], str) and event["action"] in vectors.ACTIONS:
            return vectors.handle(event, context)
        return migrator.handle(event, context)
    if user_sync.is_user_confirmed(event):
        return user_sync.handle(event, context)
    _log_unsupported(context, started)
    raise UnsupportedEventError(UNSUPPORTED_EVENT)
