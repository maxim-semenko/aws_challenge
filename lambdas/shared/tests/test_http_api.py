"""Shared HTTP API helpers (moved from lambdas/admin by T05-02; behaviour of spec 08 unchanged)."""

import json

import pytest

import http_api


def evt(claims):
    return {"requestContext": {"authorizer": {"jwt": {"claims": claims}}}}


def test_claims_only_from_the_authorizer():
    assert http_api.claims(evt({"sub": "s"})) == {"sub": "s"}
    for event in (None, [], {}, {"requestContext": {}}, {"requestContext": {"authorizer": {"jwt": {"claims": "x"}}}},
                  {"headers": {"sub": "s"}}):
        assert http_api.claims(event) is None


@pytest.mark.parametrize(
    ("claims", "ok"),
    [
        ({"sub": "s", "token_use": "access", "exp": "1893456000"}, True),
        ({"sub": "s", "token_use": "access", "exp": 1893456000}, True),
        ({"sub": "s", "token_use": "id", "exp": "1893456000"}, False),
        ({"sub": "", "token_use": "access", "exp": "1893456000"}, False),
        ({"token_use": "access", "exp": "1893456000"}, False),
        ({"sub": "s", "token_use": "access", "exp": "soon"}, False),
        ({"sub": "s", "token_use": "access", "exp": True}, False),
        ({"sub": "s", "token_use": "access", "exp": "9" * 13}, False),
        (None, False),
    ],
)
def test_authorized(claims, ok):
    assert http_api.authorized(claims) is ok


@pytest.mark.parametrize(
    ("value", "groups"),
    [("[admin]", ["admin"]), ("admin", ["admin"]), ("[admin user]", ["admin", "user"]), ('["admin","x"]', ["admin", "x"]),
     (["admin"], ["admin"]), ("a,b", ["a", "b"]), (None, []), (5, [])],
)
def test_parse_groups(value, groups):
    assert http_api.parse_groups(value) == groups


def test_is_admin_is_exact_case():
    assert http_api.is_admin({"cognito:groups": "[admin]"})
    assert not http_api.is_admin({"cognito:groups": "[Admin]"})
    assert not http_api.is_admin({})


def test_problem_and_json_response():
    problem = http_api.problem(502, "The AI service is not available.")
    assert problem["statusCode"] == 502 and problem["isBase64Encoded"] is False
    assert problem["headers"] == {"Content-Type": "application/problem+json", "Cache-Control": "no-store"}
    assert json.loads(problem["body"]) == {"type": "about:blank", "title": "Bad Gateway", "status": 502,
                                           "detail": "The AI service is not available."}
    assert json.loads(http_api.problem(429, "x")["body"])["title"] == "Too Many Requests"
    ok = http_api.json_response({"name": "Zoë"})
    assert ok["statusCode"] == 200 and ok["body"] == '{"name":"Zoë"}'
    assert ok["headers"] == {"Content-Type": "application/json", "Cache-Control": "no-store"}
