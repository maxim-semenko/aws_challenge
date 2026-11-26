"""Test double of the boto3 bedrock-runtime client (no network); install with install(monkeypatch, stub)."""

import io
import json

import embeddings


def unit_vector(index=0, scale=1.0):
    vector = [0.0] * embeddings.DIMENSIONS
    vector[index] = scale
    return vector


class StubBedrock:
    """Records invoke_model calls; answers from `outcomes` in order, then `default`.

    An outcome is an exception (raised), bytes (raw response body) or a list (the `embedding` field).
    """

    def __init__(self, outcomes=(), default=None, log=None):
        self.outcomes = list(outcomes)
        self.default = unit_vector() if default is None else default
        self.calls = []
        self.log = log  # optional shared list to record the order of Bedrock and DB calls

    def invoke_model(self, **kwargs):
        self.calls.append(kwargs)
        if self.log is not None:
            self.log.append("bedrock")
        outcome = self.outcomes.pop(0) if self.outcomes else self.default
        if isinstance(outcome, BaseException):
            raise outcome
        body = outcome if isinstance(outcome, bytes) else json.dumps(
            {"embedding": outcome, "inputTextTokenCount": 7}
        ).encode()
        return {"body": io.BytesIO(body), "contentType": "application/json"}


def install(monkeypatch, stub):
    monkeypatch.setattr(embeddings, "_bedrock_client", stub)
    return stub
