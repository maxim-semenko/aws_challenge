"""Profile embeddings for aws-challenge-sync: text template, Bedrock Titan Text Embeddings V2 call, vector checks.

Contract (template, request, client config, error classes): docs/specs/10-embeddings.md; decisions ADR-019 (model,
1024 dimensions, normalised) and ADR-020 (on-demand VPC endpoint, fail fast, never raise from the upsert). Rules: the
bedrock-embeddings skill. No network call at import: the client is created on first use.
"""

from __future__ import annotations

import json
import math
import os
import re
from collections.abc import Mapping
from datetime import date
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, ConnectionError as BotoConnectionError, ReadTimeoutError

MODEL_ID = "amazon.titan-embed-text-v2:0"
DIMENSIONS = 1024
CONNECT_TIMEOUT_S = 2
READ_TIMEOUT_S = 5
RETRIES = {"mode": "standard", "total_max_attempts": 1}  # no retry: fail fast while the endpoint is absent

UNREACHABLE = "UNREACHABLE"
TIMEOUT = "TIMEOUT"
BAD_RESPONSE = "BAD_RESPONSE"
# An AWS error code is logged as errorClass; anything that does not look like one is replaced.
AWS_ERROR_CODE = re.compile(r"[A-Za-z][A-Za-z0-9_.]{0,63}")

_bedrock_client: Any = None


class EmbeddingError(Exception):
    """Bedrock call or response unusable; args[0] is the errorClass of spec 10 (never a value or foreign text)."""

    @property
    def error_class(self) -> str:
        return str(self.args[0])


def build_text(row: Mapping[str, Any]) -> str | None:
    """Profile description of spec 10 §Inputs from mapped column values; None when all five parts are NULL.

    E-mail, names, ids and timestamps are never part of the text.
    """
    parts: list[str] = []
    if row.get("gender") is not None:
        parts.append(f"gender: {row['gender']}")
    birthdate = row.get("birthdate")
    if isinstance(birthdate, date):
        parts.append(f"birth year: {birthdate.year:04d}")
    if row.get("country") is not None:
        parts.append(f"country: {row['country']}")
    if row.get("height_cm") is not None:
        parts.append(f"height: {row['height_cm']} cm")
    if row.get("weight_kg") is not None:
        parts.append(f"weight: {row['weight_kg']} kg")
    return "; ".join(parts) if parts else None


def _bedrock() -> Any:
    """bedrock-runtime client, created once per execution environment on first use (no network call)."""
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=os.environ["AWS_REGION"],
            config=Config(connect_timeout=CONNECT_TIMEOUT_S, read_timeout=READ_TIMEOUT_S, retries=dict(RETRIES)),
        )
    return _bedrock_client


def request_body(text: str) -> str:
    return json.dumps({"inputText": text, "dimensions": DIMENSIONS, "normalize": True, "embeddingTypes": ["float"]})


def normalise(values: Any) -> list[float]:
    """Exactly DIMENSIONS finite numbers with norm > 0, scaled to unit length; else EmbeddingError(BAD_RESPONSE)."""
    if not isinstance(values, list) or len(values) != DIMENSIONS:
        raise EmbeddingError(BAD_RESPONSE)
    floats: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise EmbeddingError(BAD_RESPONSE)
        floats.append(float(value))
    norm = math.sqrt(math.fsum(x * x for x in floats))
    if not math.isfinite(norm) or norm == 0.0:
        raise EmbeddingError(BAD_RESPONSE)
    return [x / norm for x in floats]


def to_vector_literal(vector: list[float]) -> str:
    """Text form `[x1,...,xn]` passed as a parameter to CAST(:embedding AS vector) — never formatted into SQL."""
    return "[" + ",".join(repr(x) for x in vector) + "]"


def _error_class(exc: Exception) -> str:
    if isinstance(exc, ReadTimeoutError):
        return TIMEOUT
    if isinstance(exc, BotoConnectionError):  # ConnectTimeoutError, EndpointConnectionError, SSL/proxy errors
        return UNREACHABLE
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code")
        return code if isinstance(code, str) and AWS_ERROR_CODE.fullmatch(code) else "ClientError"
    return type(exc).__name__


def embed(text: str) -> list[float]:
    """One InvokeModel call; returns the unit-length vector. Every failure is EmbeddingError(<errorClass>)."""
    try:
        response = _bedrock().invoke_model(
            modelId=MODEL_ID, contentType="application/json", accept="application/json", body=request_body(text)
        )
        raw = response["body"].read()
    except Exception as exc:
        raise EmbeddingError(_error_class(exc)) from exc
    try:
        payload = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise EmbeddingError(BAD_RESPONSE) from exc
    return normalise(payload.get("embedding") if isinstance(payload, dict) else None)
