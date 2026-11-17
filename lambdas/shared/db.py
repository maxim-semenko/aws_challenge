"""Database access for the VPC Lambda functions (admin, sync).

Connects to PostgreSQL through RDS Proxy with an IAM auth token over verified TLS (spec 06, design user-sync §1).
No secret, password or connection string comes from configuration. This file is the single source; the packaging
script copies it into each function zip (design user-sync §5). See the python-lambda skill.
"""

from __future__ import annotations

import os
import ssl
from typing import Any

import boto3
import pg8000.native

PORT = 5432
# Socket timeout in seconds for connect and every later read/write on the connection.
DEFAULT_TIMEOUT_S = 10.0
ERROR_CONNECT = "DB_CONNECT_FAILED"

_rds_client: Any = None


class DbConnectError(Exception):
    """Connection to the database could not be opened; message is always DB_CONNECT_FAILED."""

    def __init__(self) -> None:
        super().__init__(ERROR_CONNECT)


def _rds() -> Any:
    """The boto3 RDS client, created once per execution environment on first use (no network call)."""
    global _rds_client
    if _rds_client is None:
        _rds_client = boto3.client("rds", region_name=os.environ["AWS_REGION"])
    return _rds_client


def _tls_context() -> ssl.SSLContext:
    """TLS with certificate and host name verification against the default trust store (never plain text)."""
    context = ssl.create_default_context()
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    return context


def connect(timeout: float | None = DEFAULT_TIMEOUT_S) -> pg8000.native.Connection:
    """Open one connection to the RDS Proxy as DB_USER, authenticated with a fresh IAM auth token.

    The token is a local SigV4 signature (generate_db_auth_token makes no network call), valid 15 minutes, and is
    never logged. Any failure (missing configuration, token, network, TLS, authentication) raises DbConnectError
    with the original exception as __cause__; the caller logs only the cause's class name.
    """
    try:
        host = os.environ["DB_PROXY_ENDPOINT"]
        database = os.environ["DB_NAME"]
        user = os.environ["DB_USER"]
        token = _rds().generate_db_auth_token(
            DBHostname=host, Port=PORT, DBUsername=user, Region=os.environ["AWS_REGION"]
        )
        return pg8000.native.Connection(
            user=user,
            host=host,
            port=PORT,
            database=database,
            password=token,
            ssl_context=_tls_context(),
            timeout=timeout,
        )
    except Exception as exc:
        raise DbConnectError() from exc


def close_quietly(conn: pg8000.native.Connection | None) -> None:
    """Close a connection in a finally block without masking the original error."""
    if conn is None:
        return
    try:
        conn.close()
    except Exception:
        pass
