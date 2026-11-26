"""HTTP API helpers shared by the API handlers (admin, chatbot): JWT claims, group parsing, JSON / problem+json.

Payload format 2.0 behind the Cognito JWT authorizer (ADR-004): claims are read only from
`requestContext.authorizer.jwt.claims`, never from headers, query or body. Error bodies are RFC 9457
application/problem+json with a fixed `detail` (never user data, SQL or exception text). Contract: spec 08 (claims,
401/403/404 texts) and spec 12; rules: the admin-api and chatbot-api skills. Moved here from
lambdas/admin/lambda_function.py by T05-02 (behaviour unchanged). No network call, no AWS client.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

ADMIN_GROUP = "admin"

TITLES = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    429: "Too Many Requests",
    500: "Internal Server Error",
    502: "Bad Gateway",
}
DETAIL_401 = "A valid access token is required."
DETAIL_403 = "Membership in the group admin is required."
DETAIL_404 = "The route is not served by this function."
DETAIL_500 = "The request could not be completed."

DIGITS = re.compile(r"[0-9]+")  # ASCII decimal digits only (str.isdigit also accepts other scripts)


class ApiError(Exception):
    """A 4xx/5xx answer as problem+json; `detail` is a fixed text or names a parameter, never user data."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


# --- responses -------------------------------------------------------------------------------------------------------


def response(status: int, body: dict[str, Any], content_type: str) -> dict[str, Any]:
    """Payload v2 response dict; compact JSON, UTF-8 (ensure_ascii=False), never cached."""
    return {
        "statusCode": status,
        "headers": {"Content-Type": content_type, "Cache-Control": "no-store"},
        "body": json.dumps(body, ensure_ascii=False, separators=(",", ":")),
        "isBase64Encoded": False,
    }


def json_response(body: dict[str, Any]) -> dict[str, Any]:
    return response(200, body, "application/json")


def problem(status: int, detail: str) -> dict[str, Any]:
    body = {"type": "about:blank", "title": TITLES[status], "status": status, "detail": detail}
    return response(status, body, "application/problem+json")


# --- claims ----------------------------------------------------------------------------------------------------------


def claims(event: Any) -> dict[str, Any] | None:
    """Claims of the JWT authorizer (payload 2.0); never read from headers, query or body."""
    if not isinstance(event, dict):
        return None
    context = event.get("requestContext")
    authorizer = context.get("authorizer") if isinstance(context, dict) else None
    jwt = authorizer.get("jwt") if isinstance(authorizer, dict) else None
    found = jwt.get("claims") if isinstance(jwt, dict) else None
    return found if isinstance(found, dict) else None


def expiry(found: dict[str, Any]) -> datetime | None:
    """Claim `exp` (epoch seconds; payload v2 delivers claims as strings) as an aware UTC datetime."""
    value = found.get("exp")
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        seconds = value
    elif isinstance(value, str) and DIGITS.fullmatch(value) and len(value) <= 12:
        seconds = int(value)
    else:
        return None
    try:
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def authorized(found: dict[str, Any] | None) -> bool:
    """Claims present with a subject and a valid expiry, and the token is an access token (ADR-004)."""
    if found is None:
        return False
    sub = found.get("sub")
    return (
        isinstance(sub, str)
        and sub != ""
        and found.get("token_use") == "access"
        and expiry(found) is not None
    )


def parse_groups(value: Any) -> list[str]:
    """`cognito:groups` -> list of group names.

    Payload v2 delivers the claim as a string such as "[admin]", "admin" or "[admin user]"; a JSON array string or a
    real list are accepted too. Group names never contain whitespace; commas are treated as separators as well.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item != ""]
    if not isinstance(value, str):
        return []
    text = value.strip()
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = json.loads(text)
        except ValueError:
            parsed = None
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, str) and item != ""]
        text = text[1:-1]
    return [name for name in re.split(r"[\s,]+", text) if name != ""]


def is_admin(found: dict[str, Any]) -> bool:
    """Exact-case membership in the group `admin`."""
    return ADMIN_GROUP in parse_groups(found.get("cognito:groups"))
