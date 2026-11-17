"""aws-challenge-post-confirmation: Cognito PostConfirmation trigger -> EventBridge UserConfirmed (spec 07, ADR-016).

Runs outside the VPC. For PostConfirmation_ConfirmSignUp it puts one event (source aws-challenge.cognito, detail-type
UserConfirmed, allow-listed attributes only) on the bus named by EVENT_BUS_NAME. It never raises and always returns the
Cognito event unchanged, so a publishing problem can never make the confirmation fail (R-02); a failed publish is
logged as publish_failed and repaired with the re-sync runbook (user-sync skill).
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.config import Config

SOURCE = "aws-challenge.cognito"
DETAIL_TYPE = "UserConfirmed"
DETAIL_VERSION = 1
CONFIRM_SIGN_UP = "PostConfirmation_ConfirmSignUp"
# Registration attributes copied into the event (allow-list, spec 07 §Inputs); nothing else leaves Cognito.
ALLOWED_ATTRIBUTES = (
    "given_name",
    "family_name",
    "gender",
    "birthdate",
    "custom:country",
    "custom:height",
    "custom:weight",
)
# Cognito waits at most 5 s for the trigger: one attempt with short timeouts (worst case ~3 s plus start-up) keeps
# PutEvents inside that budget; a missed event is logged as publish_failed and re-sent by the re-sync runbook.
CLIENT_CONFIG = Config(connect_timeout=1, read_timeout=2, retries={"total_max_attempts": 1, "mode": "standard"})

_events_client: Any = None


def _events() -> Any:
    """The boto3 EventBridge client, created once per execution environment on first use (no call at init)."""
    global _events_client
    if _events_client is None:
        _events_client = boto3.client("events", config=CLIENT_CONFIG)
    return _events_client


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def build_detail(event: dict[str, Any]) -> dict[str, Any]:
    """Event detail of spec 07 §Inputs from the Cognito event (attribute values as raw strings, allow-listed keys)."""
    user_attributes = event["request"]["userAttributes"]
    return {
        "version": DETAIL_VERSION,
        "userPoolId": event["userPoolId"],
        "sub": user_attributes.get("sub"),
        "email": user_attributes.get("email"),
        "attributes": {
            name: user_attributes[name]
            for name in ALLOWED_ATTRIBUTES
            if isinstance(user_attributes.get(name), str)
        },
        "confirmedAt": _now_iso(),
    }


def _publish(event: dict[str, Any]) -> str | None:
    """Put one entry; returns None on success, else the error class / EventBridge error code for the log line."""
    response = _events().put_events(
        Entries=[
            {
                "Source": SOURCE,
                "DetailType": DETAIL_TYPE,
                "Detail": json.dumps(build_detail(event), separators=(",", ":")),
                "EventBusName": os.environ["EVENT_BUS_NAME"],
            }
        ]
    )
    if response.get("FailedEntryCount", 0) > 0:
        entries = response.get("Entries") or [{}]
        code = entries[0].get("ErrorCode")
        return code if isinstance(code, str) and code else "FailedEntry"
    return None


def _user_sub(event: Any) -> str | None:
    try:
        sub = event["request"]["userAttributes"]["sub"]
    except (KeyError, TypeError):
        return None
    return sub if isinstance(sub, str) else None


def _log(context: Any, event: Any, outcome: str, started: float, error_class: str | None) -> None:
    # Ids and outcome only; never e-mail, names or any other attribute value (spec 07 §Outputs).
    trigger_source = event.get("triggerSource") if isinstance(event, dict) else None
    line: dict[str, Any] = {
        "level": "ERROR" if outcome == "publish_failed" else "INFO",
        "message": "post-confirmation trigger completed",
        "function": getattr(context, "function_name", None),
        "awsRequestId": getattr(context, "aws_request_id", None),
        "triggerSource": trigger_source if isinstance(trigger_source, str) else None,
        "userSub": _user_sub(event),
        "outcome": outcome,
        "durationMs": round((time.monotonic() - started) * 1000),
    }
    if error_class is not None:
        line["errorClass"] = error_class
    print(json.dumps(line, separators=(",", ":")))


def lambda_handler(event: Any, context: Any) -> Any:
    """Never raises; returns the Cognito event unchanged in every case."""
    started = time.monotonic()
    outcome, error_class = "ignored", None
    try:
        if isinstance(event, dict) and event.get("triggerSource") == CONFIRM_SIGN_UP:
            error_class = _publish(event)
            outcome = "published" if error_class is None else "publish_failed"
    except Exception as exc:
        outcome, error_class = "publish_failed", type(exc).__name__
    try:
        _log(context, event, outcome, started, error_class)
    except Exception:
        pass
    return event
