"""Unit tests of the aws-challenge-sync event dispatch (spec 06 §Inputs dispatch table, §Outputs; AC-06.2)."""

import json

import pytest

import db
import lambda_function
import migrator
import user_sync


class Context:
    function_name = "aws-challenge-sync"
    aws_request_id = "req-456"


def log_lines(capsys):
    return [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]


@pytest.fixture
def no_connect(monkeypatch):
    def forbidden(**kwargs):
        raise AssertionError("must not connect")

    monkeypatch.setattr(db, "connect", forbidden)


def test_action_event_reaches_the_migration_runner(monkeypatch):
    calls = []

    def handle(event, context):
        calls.append((event, context))
        return {"current": 1, "pending": []}

    monkeypatch.setattr(migrator, "handle", handle)
    event, context = {"action": "status"}, Context()

    assert lambda_function.lambda_handler(event, context) == {"current": 1, "pending": []}
    assert calls == [(event, context)]


def test_action_event_with_unknown_value_is_a_migration_bad_request(no_connect, capsys):
    with pytest.raises(migrator.MigrationError, match="^MIGRATION_BAD_REQUEST$"):
        lambda_function.lambda_handler({"action": "x"}, Context())

    (line,) = log_lines(capsys)
    assert line["message"] == "MIGRATION_BAD_REQUEST"


USER_CONFIRMED = {
    "version": "0",
    "id": "6a7e8feb-b491-4cf7-a9f1-bf3703467718",
    "detail-type": "UserConfirmed",
    "source": "aws-challenge.cognito",
    "time": "2026-11-16T10:00:00Z",
    "detail": {"sub": "8f1c2a3b-0000-4000-8000-000000000001", "email": "person@example.com"},
}


def test_user_confirmed_envelope_reaches_the_upsert_and_never_the_runner(monkeypatch):
    calls = []

    def runner_forbidden(event, context):
        raise AssertionError("must not reach the migration runner")

    def upsert(event, context):
        calls.append((event, context))
        return {"outcome": "inserted"}

    monkeypatch.setattr(migrator, "handle", runner_forbidden)
    monkeypatch.setattr(user_sync, "handle", upsert)
    context = Context()

    assert lambda_function.lambda_handler(USER_CONFIRMED, context) == {"outcome": "inserted"}
    assert calls == [(USER_CONFIRMED, context)]


@pytest.mark.parametrize(
    "event",
    [
        {},
        {"key1": "value1", "key2": "value2", "key3": "value3"},  # Lambda console default test template
        {**USER_CONFIRMED, "detail-type": "UserDeleted"},
        {**USER_CONFIRMED, "source": "aws.cognito-idp"},
        None,
        [],
        "action",
        [{"action": "status"}],
    ],
    ids=[
        "empty", "console-default", "other-detail-type", "other-source", "none", "list", "string", "list-with-action",
    ],
)
def test_other_events_are_unsupported_without_connecting(event, no_connect, monkeypatch, capsys):
    def runner_forbidden(event, context):
        raise AssertionError("must not reach the migration runner")

    def upsert_forbidden(event, context):
        raise AssertionError("must not reach the upsert")

    monkeypatch.setattr(migrator, "handle", runner_forbidden)
    monkeypatch.setattr(user_sync, "handle", upsert_forbidden)

    with pytest.raises(lambda_function.UnsupportedEventError, match="^UNSUPPORTED_EVENT$"):
        lambda_function.lambda_handler(event, Context())

    (line,) = log_lines(capsys)
    assert set(line) == {"level", "message", "function", "awsRequestId", "outcome", "durationMs"}
    assert {k: line[k] for k in ("level", "message", "function", "awsRequestId", "outcome")} == {
        "level": "ERROR",
        "message": "UNSUPPORTED_EVENT",
        "function": "aws-challenge-sync",
        "awsRequestId": "req-456",
        "outcome": "failure",
    }
    assert isinstance(line["durationMs"], int)
    assert "person@example.com" not in json.dumps(line)
