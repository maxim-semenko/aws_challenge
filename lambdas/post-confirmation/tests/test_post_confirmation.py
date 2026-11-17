"""Unit tests of the Cognito PostConfirmation trigger aws-challenge-post-confirmation (spec 07; AC-07.1)."""

import copy
import json
from datetime import datetime

import botocore.exceptions
import pytest

import lambda_function

SUB = "8f1c2a3b-0000-4000-8000-000000000001"
USER_ATTRIBUTES = {
    "sub": SUB,
    "email": "person@example.com",
    "email_verified": "false",
    "cognito:user_status": "CONFIRMED",
    "given_name": "Anna",
    "family_name": "Karenina",
    "gender": "female",
    "birthdate": "1990-05-17",
    "custom:country": "Austria",
    "custom:height": "170",
    "custom:weight": "62",
    "custom:other": "not allow-listed",
}
VALUES = [v for k, v in USER_ATTRIBUTES.items() if k not in ("sub", "cognito:user_status")]


def cognito_event(trigger_source="PostConfirmation_ConfirmSignUp", attributes=None):
    return {
        "version": "1",
        "region": "eu-west-1",
        "userPoolId": "eu-west-1_EXAMPLE",
        "userName": SUB,
        "callerContext": {"awsSdkVersion": "aws-sdk-unknown-unknown", "clientId": "CLIENT_ID_NOT_APPLICABLE"},
        "triggerSource": trigger_source,
        "request": {"userAttributes": dict(USER_ATTRIBUTES if attributes is None else attributes)},
        "response": {},
    }


class Context:
    function_name = "aws-challenge-post-confirmation"
    aws_request_id = "req-123"


class StubEvents:
    """EventBridge client double: records put_events calls; returns `response` or raises `error`."""

    def __init__(self, response=None, error=None):
        self.response = response if response is not None else {"FailedEntryCount": 0, "Entries": [{"EventId": "e-1"}]}
        self.error = error
        self.calls = []

    def put_events(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


@pytest.fixture(autouse=True)
def bus(monkeypatch):
    monkeypatch.setenv("EVENT_BUS_NAME", "aws-challenge-events")


def use(monkeypatch, stub):
    monkeypatch.setattr(lambda_function, "_events_client", stub)
    return stub


def log_line(capsys):
    (line,) = [json.loads(text) for text in capsys.readouterr().out.splitlines() if text.strip()]
    return line


def assert_no_values_logged(line):
    text = json.dumps(line)
    for value in VALUES:
        assert value not in text, value


def test_confirm_sign_up_puts_one_entry_with_exactly_the_spec_fields(monkeypatch, capsys):
    stub = use(monkeypatch, StubEvents())
    event = cognito_event()
    original = copy.deepcopy(event)

    result = lambda_function.lambda_handler(event, Context())

    assert result is event
    assert event == original
    ((call,),) = [c["Entries"] for c in stub.calls]
    assert len(stub.calls) == 1 and set(stub.calls[0]) == {"Entries"}
    assert set(call) == {"Source", "DetailType", "Detail", "EventBusName"}
    assert (call["Source"], call["DetailType"], call["EventBusName"]) == (
        "aws-challenge.cognito",
        "UserConfirmed",
        "aws-challenge-events",
    )
    detail = json.loads(call["Detail"])
    confirmed_at = detail.pop("confirmedAt")
    assert detail == {
        "version": 1,
        "userPoolId": "eu-west-1_EXAMPLE",
        "sub": SUB,
        "email": "person@example.com",
        "attributes": {
            "given_name": "Anna",
            "family_name": "Karenina",
            "gender": "female",
            "birthdate": "1990-05-17",
            "custom:country": "Austria",
            "custom:height": "170",
            "custom:weight": "62",
        },
    }
    assert confirmed_at.endswith("Z")
    assert datetime.fromisoformat(confirmed_at).utcoffset().total_seconds() == 0

    line = log_line(capsys)
    assert line == {
        "level": "INFO",
        "message": "post-confirmation trigger completed",
        "function": "aws-challenge-post-confirmation",
        "awsRequestId": "req-123",
        "triggerSource": "PostConfirmation_ConfirmSignUp",
        "userSub": SUB,
        "outcome": "published",
        "durationMs": line["durationMs"],
    }
    assert isinstance(line["durationMs"], int)
    assert_no_values_logged(line)


def test_missing_registration_attributes_are_left_out(monkeypatch):
    stub = use(monkeypatch, StubEvents())
    lambda_function.lambda_handler(cognito_event(attributes={"sub": SUB, "email": "a@b.c"}), Context())
    detail = json.loads(stub.calls[0]["Entries"][0]["Detail"])
    assert detail["attributes"] == {}


@pytest.mark.parametrize(
    "stub",
    [
        StubEvents(error=botocore.exceptions.ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}}, "PutEvents")),
        StubEvents(error=botocore.exceptions.EndpointConnectionError(endpoint_url="https://events.example")),
        StubEvents(error=RuntimeError("anything")),
    ],
    ids=["throttled", "unreachable", "unexpected"],
)
def test_put_events_exception_is_publish_failed_and_the_event_is_returned(stub, monkeypatch, capsys):
    use(monkeypatch, stub)
    event = cognito_event()
    original = copy.deepcopy(event)

    result = lambda_function.lambda_handler(event, Context())

    assert result is event and event == original
    line = log_line(capsys)
    assert (line["outcome"], line["level"], line["userSub"]) == ("publish_failed", "ERROR", SUB)
    assert line["errorClass"] == type(stub.error).__name__
    assert_no_values_logged(line)


def test_failed_entry_count_is_publish_failed_and_the_event_is_returned(monkeypatch, capsys):
    response = {
        "FailedEntryCount": 1,
        "Entries": [{"ErrorCode": "InternalFailure", "ErrorMessage": "Internal error"}],
    }
    stub = use(monkeypatch, StubEvents(response=response))
    event = cognito_event()

    assert lambda_function.lambda_handler(event, Context()) is event

    assert len(stub.calls) == 1
    line = log_line(capsys)
    assert (line["outcome"], line["errorClass"]) == ("publish_failed", "InternalFailure")
    assert_no_values_logged(line)


def test_missing_bus_configuration_is_publish_failed(monkeypatch, capsys):
    stub = use(monkeypatch, StubEvents())
    monkeypatch.delenv("EVENT_BUS_NAME")
    event = cognito_event()

    assert lambda_function.lambda_handler(event, Context()) is event

    assert stub.calls == []
    line = log_line(capsys)
    assert (line["outcome"], line["errorClass"]) == ("publish_failed", "KeyError")


def test_forgot_password_confirmation_is_ignored_without_put_events(monkeypatch, capsys):
    stub = use(monkeypatch, StubEvents())
    event = cognito_event("PostConfirmation_ConfirmForgotPassword")
    original = copy.deepcopy(event)

    assert lambda_function.lambda_handler(event, Context()) is event

    assert event == original
    assert stub.calls == []
    line = log_line(capsys)
    assert (line["outcome"], line["level"], line["triggerSource"]) == (
        "ignored", "INFO", "PostConfirmation_ConfirmForgotPassword")
    assert "errorClass" not in line
    assert_no_values_logged(line)


@pytest.mark.parametrize("event", [{}, None, "x", {"triggerSource": "PostConfirmation_ConfirmSignUp"}],
                         ids=["empty", "none", "string", "no-request"])
def test_malformed_events_never_raise_and_are_returned(event, monkeypatch, capsys):
    use(monkeypatch, StubEvents())
    assert lambda_function.lambda_handler(event, Context()) is event
    log_line(capsys)


def test_client_is_created_lazily_with_bounded_timeouts(monkeypatch):
    created = []

    def client(name, config):
        created.append((name, config))
        return StubEvents()

    monkeypatch.setattr(lambda_function, "_events_client", None)
    monkeypatch.setattr(lambda_function.boto3, "client", client)

    lambda_function.lambda_handler(cognito_event(), Context())
    lambda_function.lambda_handler(cognito_event(), Context())

    assert len(created) == 1
    name, config = created[0]
    assert name == "events"
    assert (config.connect_timeout, config.read_timeout) == (1, 2)
    assert config.retries == {"total_max_attempts": 1, "mode": "standard"}
