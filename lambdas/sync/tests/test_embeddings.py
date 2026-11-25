"""Unit tests of embeddings.py: text template, request, client config, normalisation, error classes (AC-10.2)."""

import json
import math
from datetime import date

import pytest
from botocore.exceptions import (
    ClientError,
    ConnectTimeoutError,
    EndpointConnectionError,
    ReadTimeoutError,
    SSLError,
)

import embeddings
from bedrock_stub import StubBedrock, install, unit_vector

FULL_ROW = {
    "id": "8f1c2a3b-0000-4000-8000-000000000001",
    "email": "person@example.com",
    "given_name": "Anna",
    "family_name": "Karenina",
    "gender": "female",
    "birthdate": date(1990, 5, 17),
    "country": "Austria",
    "height_cm": 170,
    "weight_kg": 62,
}


# --- text template (spec 10 §Inputs) ------------------------------------------------------------------------------


def test_text_has_all_parts_in_order_without_email_names_or_id():
    text = embeddings.build_text(FULL_ROW)
    assert text == "gender: female; birth year: 1990; country: Austria; height: 170 cm; weight: 62 kg"
    for value in ("person@example.com", "Anna", "Karenina", FULL_ROW["id"], "05-17"):
        assert value not in text


@pytest.mark.parametrize(
    "missing, expected",
    [
        (("gender",), "birth year: 1990; country: Austria; height: 170 cm; weight: 62 kg"),
        (("birthdate", "country"), "gender: female; height: 170 cm; weight: 62 kg"),
        (("height_cm", "weight_kg"), "gender: female; birth year: 1990; country: Austria"),
        (("gender", "birthdate", "country", "height_cm"), "weight: 62 kg"),
    ],
)
def test_missing_parts_are_left_out(missing, expected):
    row = {**FULL_ROW, **{key: None for key in missing}}
    assert embeddings.build_text(row) == expected


def test_all_five_null_gives_no_text():
    row = {**FULL_ROW, "gender": None, "birthdate": None, "country": None, "height_cm": None, "weight_kg": None}
    assert embeddings.build_text(row) is None
    assert embeddings.build_text({}) is None


def test_zero_and_negative_integers_are_parts():
    assert embeddings.build_text({"height_cm": 0, "weight_kg": -5}) == "height: 0 cm; weight: -5 kg"


# --- request and client -----------------------------------------------------------------------------------------


def test_model_id_and_request_body_exactly_as_spec(monkeypatch):
    stub = install(monkeypatch, StubBedrock())
    embeddings.embed("gender: female")

    (call,) = stub.calls
    assert call["modelId"] == "amazon.titan-embed-text-v2:0"
    assert call["contentType"] == "application/json"
    assert call["accept"] == "application/json"
    assert set(call) == {"modelId", "contentType", "accept", "body"}
    assert json.loads(call["body"]) == {
        "inputText": "gender: female", "dimensions": 1024, "normalize": True, "embeddingTypes": ["float"]
    }
    assert embeddings.MODEL_ID == "amazon.titan-embed-text-v2:0" and embeddings.DIMENSIONS == 1024


def test_client_is_lazy_with_fail_fast_config(monkeypatch):
    monkeypatch.setattr(embeddings, "_bedrock_client", None)
    monkeypatch.setenv("AWS_REGION", "eu-west-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")

    client = embeddings._bedrock()

    assert client.meta.service_model.service_name == "bedrock-runtime"
    assert client.meta.region_name == "eu-west-1"
    assert client.meta.config.connect_timeout == 2
    assert client.meta.config.read_timeout == 5
    assert client.meta.config.retries == {"mode": "standard", "total_max_attempts": 1}
    assert embeddings._bedrock() is client  # once per execution environment


def test_import_creates_no_client():
    import importlib

    module = importlib.reload(embeddings)
    assert module._bedrock_client is None


# --- normalisation ------------------------------------------------------------------------------------------------


def test_vector_is_scaled_to_unit_length(monkeypatch):
    raw = [0.5] * 1024  # norm 16
    install(monkeypatch, StubBedrock(default=raw))
    vector = embeddings.embed("x")
    assert len(vector) == 1024
    assert math.isclose(math.sqrt(sum(x * x for x in vector)), 1.0, rel_tol=1e-12)
    assert vector[0] == pytest.approx(1 / 32)


def test_unit_vector_is_unchanged():
    assert embeddings.normalise(unit_vector(3)) == unit_vector(3)


def test_integers_in_the_vector_are_accepted():
    vector = [0] * 1024
    vector[0] = 2
    assert embeddings.normalise(vector)[0] == 1.0


@pytest.mark.parametrize(
    "values",
    [
        [0.0] * 1024,
        [0.1] * 1023,
        [0.1] * 1025,
        [],
        None,
        "[0.1]",
        [0.1] * 1023 + [float("nan")],
        [0.1] * 1023 + [float("inf")],
        [0.1] * 1023 + ["0.1"],
        [0.1] * 1023 + [True],
        [1e308] * 1024,  # norm overflows
    ],
    ids=["zero", "short", "long", "empty", "none", "string", "nan", "inf", "str-item", "bool-item", "overflow"],
)
def test_bad_vectors_are_bad_response(values):
    with pytest.raises(embeddings.EmbeddingError) as raised:
        embeddings.normalise(values)
    assert raised.value.error_class == "BAD_RESPONSE"


@pytest.mark.parametrize(
    "body",
    [b"not json", b"[]", b"{}", json.dumps({"embedding": [0.1] * 512}).encode()],
    ids=["not-json", "list", "no-field", "wrong-dimension"],
)
def test_bad_response_bodies_are_bad_response(body, monkeypatch):
    install(monkeypatch, StubBedrock(default=body))
    with pytest.raises(embeddings.EmbeddingError, match="^BAD_RESPONSE$"):
        embeddings.embed("x")


def test_vector_literal_is_the_pgvector_text_form():
    literal = embeddings.to_vector_literal([1.0, -0.25, 1e-05])
    assert literal == "[1.0,-0.25,1e-05]"
    full = embeddings.to_vector_literal(unit_vector())
    assert full.startswith("[1.0,0.0,") and full.count(",") == 1023


# --- error classes (spec 10 §Outputs) -----------------------------------------------------------------------------


def client_error(code, message="details with a value person@example.com"):
    return ClientError({"Error": {"Code": code, "Message": message}}, "InvokeModel")


@pytest.mark.parametrize(
    "exception, expected",
    [
        (ConnectTimeoutError(endpoint_url="https://bedrock-runtime.eu-west-1.amazonaws.com"), "UNREACHABLE"),
        (EndpointConnectionError(endpoint_url="https://bedrock-runtime.eu-west-1.amazonaws.com"), "UNREACHABLE"),
        (SSLError(endpoint_url="https://x", error="bad cert"), "UNREACHABLE"),
        (ReadTimeoutError(endpoint_url="https://bedrock-runtime.eu-west-1.amazonaws.com"), "TIMEOUT"),
        (client_error("ThrottlingException"), "ThrottlingException"),
        (client_error("AccessDeniedException"), "AccessDeniedException"),
        (client_error("ValidationException"), "ValidationException"),
        (client_error("bad code with spaces <x>"), "ClientError"),
        (KeyError("AWS_REGION"), "KeyError"),
    ],
)
def test_error_class_mapping(exception, expected, monkeypatch):
    install(monkeypatch, StubBedrock(outcomes=[exception]))
    with pytest.raises(embeddings.EmbeddingError) as raised:
        embeddings.embed("x")
    assert raised.value.error_class == expected
    assert str(raised.value) == expected  # never the foreign message
    assert raised.value.__cause__ is exception
