"""Unit tests of lambdas/shared/db.py — boto3 and pg8000 replaced by test doubles (no network, no database)."""

import importlib
import ssl

import pg8000.native
import pytest

import db

ENV = {
    "AWS_REGION": "eu-west-1",
    "DB_PROXY_ENDPOINT": "proxy.example.internal",
    "DB_NAME": "appdb",
    "DB_USER": "appuser",
}
TOKEN = "fake-iam-auth-token"


class FakeRds:
    def __init__(self, error=None):
        self.calls = []
        self.error = error

    def generate_db_auth_token(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return TOKEN


class FakeConnectionFactory:
    def __init__(self, error=None):
        self.kwargs = None
        self.error = error

    def __call__(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return "connection"


@pytest.fixture
def env(monkeypatch):
    for name, value in ENV.items():
        monkeypatch.setenv(name, value)
    # Configuration that must never be used for the connection.
    monkeypatch.setenv("DB_PASSWORD", "must-not-be-used")
    monkeypatch.setenv("DB_SECRET_ARN", "must-not-be-used")


@pytest.fixture
def rds(monkeypatch):
    fake = FakeRds()
    monkeypatch.setattr(db, "_rds_client", fake)
    return fake


@pytest.fixture
def factory(monkeypatch):
    fake = FakeConnectionFactory()
    monkeypatch.setattr(pg8000.native, "Connection", fake)
    return fake


def test_connect_uses_iam_token_as_password_with_verified_tls(env, rds, factory):
    assert db.connect() == "connection"

    assert rds.calls == [
        {"DBHostname": "proxy.example.internal", "Port": 5432, "DBUsername": "appuser", "Region": "eu-west-1"}
    ]
    kwargs = factory.kwargs
    assert kwargs["host"] == "proxy.example.internal"
    assert kwargs["port"] == 5432
    assert kwargs["database"] == "appdb"
    assert kwargs["user"] == "appuser"
    assert kwargs["password"] == TOKEN
    assert "must-not-be-used" not in kwargs.values()
    context = kwargs["ssl_context"]
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert kwargs["timeout"] == db.DEFAULT_TIMEOUT_S


@pytest.mark.parametrize("missing", ["DB_PROXY_ENDPOINT", "DB_NAME", "DB_USER", "AWS_REGION"])
def test_missing_configuration_is_db_connect_failed(env, rds, factory, monkeypatch, missing):
    monkeypatch.delenv(missing)
    with pytest.raises(db.DbConnectError, match="^DB_CONNECT_FAILED$") as raised:
        db.connect()
    assert isinstance(raised.value.__cause__, KeyError)
    assert factory.kwargs is None


def test_token_failure_is_db_connect_failed(env, monkeypatch, factory):
    monkeypatch.setattr(db, "_rds_client", FakeRds(error=RuntimeError("no credentials")))
    with pytest.raises(db.DbConnectError, match="^DB_CONNECT_FAILED$"):
        db.connect()
    assert factory.kwargs is None


@pytest.mark.parametrize(
    "error",
    [
        pg8000.native.InterfaceError("Server refuses SSL"),
        ssl.SSLCertVerificationError("certificate verify failed"),
        pg8000.native.DatabaseError({"C": "28000", "M": "IAM authentication failed"}),
        TimeoutError("timed out"),
    ],
)
def test_connection_failure_is_db_connect_failed_with_cause(env, rds, monkeypatch, error):
    monkeypatch.setattr(pg8000.native, "Connection", FakeConnectionFactory(error=error))
    with pytest.raises(db.DbConnectError, match="^DB_CONNECT_FAILED$") as raised:
        db.connect()
    assert raised.value.__cause__ is error


def test_rds_client_is_created_lazily_once_with_runtime_region(env, monkeypatch):
    created = []
    monkeypatch.setattr(db, "_rds_client", None)
    monkeypatch.setattr(db.boto3, "client", lambda service, **kw: created.append((service, kw)) or FakeRds())

    first = db._rds()
    assert db._rds() is first
    assert created == [("rds", {"region_name": "eu-west-1"})]


def test_import_makes_no_client_and_no_connection(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("no client or connection at import")

    monkeypatch.setattr("boto3.client", forbidden)
    monkeypatch.setattr(pg8000.native, "Connection", forbidden)
    reloaded = importlib.reload(db)
    assert reloaded._rds_client is None


def test_close_quietly_closes_and_swallows_errors():
    class Conn:
        closed = False

        def close(self):
            self.closed = True
            raise OSError("socket already closed")

    conn = Conn()
    db.close_quietly(conn)
    assert conn.closed
    db.close_quietly(None)
