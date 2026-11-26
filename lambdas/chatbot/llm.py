"""NL -> SQL through Amazon Bedrock `Converse` (Amazon Nova Micro via the EU geo inference profile).

Contract: spec 12 §Inputs (model id, inference config, client config, prompt), §Outputs (errors); decisions ADR-021
(direct Converse, no Bedrock Agent) and ADR-022 (Nova Micro). The client is created on first use (no network call at
import); one attempt, no retry. Errors carry only an errorClass of spec 10 (never the model's text or AWS messages).
Rules: the chatbot-api skill.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.config import Config

import embeddings

MODEL_ID = "eu.amazon.nova-micro-v1:0"
INFERENCE_CONFIG = {"maxTokens": 300, "temperature": 0}
CONNECT_TIMEOUT_S = 2
READ_TIMEOUT_S = 10
RETRIES = {"mode": "standard", "total_max_attempts": 1}  # no retry: fail fast while the endpoint is absent

THROTTLED = "ThrottlingException"

# System prompt (spec 12 §Inputs "LLM prompt"). The user message is the trimmed query. The column list equals the
# allowlist of sql_guard.ALLOWED_COLUMNS; `embedding` is never mentioned.
SYSTEM_PROMPT = """You translate an administrator's question into one PostgreSQL 14 query.

Table users (one row per registered user):
- id uuid: user id
- email text: e-mail address
- given_name text, family_name text: first and last name
- gender text: either 'F'/'M' or 'female'/'male' (both forms occur)
- birthdate date: date of birth; age in years = date_part('year', age(birthdate))
- country text: either an ISO 3166-1 alpha-2 code (e.g. 'PL') or an English country name (e.g. 'Poland') (both forms occur)
- height_cm integer: height in centimetres
- weight_kg integer: weight in kilograms
- confirmed_at timestamptz: when the account was confirmed
- created_at timestamptz, updated_at timestamptz: row timestamps

Value conventions:
- A gender filter must match both forms, e.g. gender IN ('F', 'female').
- A country filter must match both forms, e.g. country IN ('PL', 'Poland').

Rules:
- Answer with exactly one PostgreSQL SELECT statement on the table users only. No other table, no other schema.
- Use only the columns listed above.
- No semicolon-separated statements, no data changes, no comments.
- For a list of rows use LIMIT 100 or less.
- When the question asks "how many", "average" or similar, use an aggregate (count, avg, min, max, sum).
- The word "sql" in the question only selects this mode; ignore it.
- If the question cannot be answered from this table, answer exactly NONE.
- Answer with the SQL text only: no explanation, no Markdown."""

_converse_client: Any = None


class LlmError(Exception):
    """Converse call or response unusable; args[0] is the errorClass (spec 10 classes, never foreign text)."""

    @property
    def error_class(self) -> str:
        return str(self.args[0])


@dataclass(frozen=True)
class Answer:
    text: str
    input_tokens: int
    output_tokens: int


def _bedrock() -> Any:
    """bedrock-runtime client for Converse, created once per execution environment on first use (no network call)."""
    global _converse_client
    if _converse_client is None:
        _converse_client = boto3.client(
            "bedrock-runtime",
            region_name=os.environ["AWS_REGION"],
            config=Config(connect_timeout=CONNECT_TIMEOUT_S, read_timeout=READ_TIMEOUT_S, retries=dict(RETRIES)),
        )
    return _converse_client


def request(query: str) -> dict[str, Any]:
    """Keyword arguments of the Converse call for one question."""
    return {
        "modelId": MODEL_ID,
        "system": [{"text": SYSTEM_PROMPT}],
        "messages": [{"role": "user", "content": [{"text": query}]}],
        "inferenceConfig": dict(INFERENCE_CONFIG),
    }


def _count(value: Any) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return 0


def ask(query: str) -> Answer:
    """One Converse call -> the model's text and token usage. Every failure is LlmError(<errorClass>)."""
    try:
        response = _bedrock().converse(**request(query))
    except Exception as exc:
        raise LlmError(embeddings.error_class(exc)) from exc
    try:
        blocks = response["output"]["message"]["content"]
        texts = [block["text"] for block in blocks if isinstance(block, dict) and "text" in block]
        if not texts or not all(isinstance(text, str) for text in texts):
            raise ValueError("no text block")
    except (KeyError, TypeError, ValueError) as exc:
        raise LlmError(embeddings.BAD_RESPONSE) from exc
    usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    return Answer("".join(texts), _count(usage.get("inputTokens")), _count(usage.get("outputTokens")))
