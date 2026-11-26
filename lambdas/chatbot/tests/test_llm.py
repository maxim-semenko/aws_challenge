"""Converse request, client configuration, answer and errors (spec 12 §Inputs, AC-12.1 SQL path)."""

import importlib

import pytest
from botocore.exceptions import ClientError, ConnectTimeoutError, EndpointConnectionError, ReadTimeoutError

import llm
from doubles import StubConverse, install_converse


def test_request_has_model_id_system_prompt_user_query_and_inference_config(monkeypatch):
    stub = install_converse(monkeypatch, StubConverse())
    llm.ask("sql how many users live in Poland")

    (call,) = stub.calls
    assert set(call) == {"modelId", "system", "messages", "inferenceConfig"}
    assert call["modelId"] == "eu.amazon.nova-micro-v1:0"
    assert call["inferenceConfig"] == {"maxTokens": 300, "temperature": 0}
    assert call["system"] == [{"text": llm.SYSTEM_PROMPT}]
    assert call["messages"] == [{"role": "user", "content": [{"text": "sql how many users live in Poland"}]}]


def test_prompt_states_schema_conventions_and_rules_without_the_vector_column():
    prompt = llm.SYSTEM_PROMPT
    for column in ("id uuid", "email text", "given_name", "family_name", "gender text", "birthdate date",
                   "country text", "height_cm integer", "weight_kg integer", "confirmed_at", "created_at",
                   "updated_at"):
        assert column in prompt
    assert "embedding" not in prompt
    assert "date_part('year', age(birthdate))" in prompt
    assert "gender IN ('F', 'female')" in prompt and "country IN ('PL', 'Poland')" in prompt
    assert "exactly NONE" in prompt and "LIMIT 100" in prompt and "no Markdown" in prompt
    assert "users only" in prompt and "no data changes" in prompt


def test_answer_text_and_token_usage(monkeypatch):
    install_converse(monkeypatch, StubConverse(default="SELECT 1"))
    answer = llm.ask("sql x")
    assert answer == llm.Answer("SELECT 1", 700, 40)


def test_text_blocks_are_joined_and_missing_usage_is_zero(monkeypatch):
    response = {"output": {"message": {"content": [{"text": "SELECT "}, {"text": "1"}]}}}
    install_converse(monkeypatch, StubConverse(default=response))
    assert llm.ask("sql x") == llm.Answer("SELECT 1", 0, 0)


@pytest.mark.parametrize(
    "response",
    [{}, {"output": {}}, {"output": {"message": {"content": []}}}, {"output": {"message": {"content": [{"x": 1}]}}},
     {"output": {"message": {"content": [{"text": 5}]}}}, {"output": None}],
)
def test_unusable_response_is_bad_response(response, monkeypatch):
    install_converse(monkeypatch, StubConverse(default=response))
    with pytest.raises(llm.LlmError) as raised:
        llm.ask("sql x")
    assert raised.value.error_class == "BAD_RESPONSE"


def client_error(code):
    return ClientError({"Error": {"Code": code, "Message": "secret detail person@example.com"}}, "Converse")


@pytest.mark.parametrize(
    ("exception", "expected"),
    [
        (EndpointConnectionError(endpoint_url="https://bedrock-runtime.eu-west-1.amazonaws.com"), "UNREACHABLE"),
        (ConnectTimeoutError(endpoint_url="https://bedrock-runtime.eu-west-1.amazonaws.com"), "UNREACHABLE"),
        (ReadTimeoutError(endpoint_url="https://bedrock-runtime.eu-west-1.amazonaws.com"), "TIMEOUT"),
        (client_error("ThrottlingException"), "ThrottlingException"),
        (client_error("AccessDeniedException"), "AccessDeniedException"),
        (client_error("ValidationException"), "ValidationException"),
        (client_error("ResourceNotFoundException"), "ResourceNotFoundException"),
    ],
)
def test_error_classes(exception, expected, monkeypatch):
    install_converse(monkeypatch, StubConverse(outcomes=[exception]))
    with pytest.raises(llm.LlmError) as raised:
        llm.ask("sql x")
    assert str(raised.value) == expected and raised.value.__cause__ is exception


def test_client_is_lazy_with_fail_fast_config_and_has_converse(monkeypatch):
    monkeypatch.setattr(llm, "_converse_client", None)
    monkeypatch.setenv("AWS_REGION", "eu-west-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")

    client = llm._bedrock()

    assert client.meta.service_model.service_name == "bedrock-runtime"
    assert client.meta.region_name == "eu-west-1"
    assert client.meta.config.connect_timeout == 2
    assert client.meta.config.read_timeout == 10
    assert client.meta.config.retries == {"mode": "standard", "total_max_attempts": 1}
    assert callable(getattr(client, "converse"))
    assert llm._bedrock() is client


def test_import_creates_no_client():
    module = importlib.reload(llm)
    assert module._converse_client is None
