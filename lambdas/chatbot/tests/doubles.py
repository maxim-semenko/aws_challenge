"""Test doubles of the chatbot: Converse client and pg8000 connection (no network, no database)."""

import pg8000.native

import llm


class StubConverse:
    """Records converse calls; answers from `outcomes` in order, then `default`.

    An outcome is an exception (raised), a dict (the raw response) or a str (the model's text, usage 700/40).
    """

    def __init__(self, outcomes=(), default="SELECT count(*) FROM users", log=None):
        self.outcomes = list(outcomes)
        self.default = default
        self.calls = []
        self.log = log

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        if self.log is not None:
            self.log.append("converse")
        outcome = self.outcomes.pop(0) if self.outcomes else self.default
        if isinstance(outcome, BaseException):
            raise outcome
        if isinstance(outcome, dict):
            return outcome
        return {
            "output": {"message": {"role": "assistant", "content": [{"text": outcome}]}},
            "stopReason": "end_turn",
            "usage": {"inputTokens": 700, "outputTokens": 40, "totalTokens": 740},
        }


def install_converse(monkeypatch, stub):
    monkeypatch.setattr(llm, "_converse_client", stub)
    return stub


class Context:
    def __init__(self, rows, columns):
        self.rows = rows
        self.columns = columns


def db_error(code):
    return pg8000.native.DatabaseError({"S": "ERROR", "C": code, "M": "message with a value person@example.com"})


class FakeConnection:
    """Records every statement; `run` answers the vector query, `execute_unnamed` the guarded statement."""

    def __init__(self, vector_rows=(), rows=(), columns=("count",), statement_error=None, log=None,
                 begin_error=None):
        self.vector_rows = [list(r) for r in vector_rows]
        self.rows = [list(r) for r in rows]
        self.columns = [{"name": name, "type_oid": 25} for name in columns]
        self.statement_error = statement_error
        self.begin_error = begin_error
        self.statements = []  # (kind, sql, params)
        self.closed = False
        self.log = log

    def run(self, sql, **params):
        self.statements.append(("run", sql, params))
        if self.log is not None:
            self.log.append("db")
        if sql.startswith("BEGIN") and self.begin_error is not None:
            raise self.begin_error
        if sql.startswith("SELECT id, email"):
            return self.vector_rows
        return None

    def execute_unnamed(self, sql, vals=(), oids=(), stream=None):
        self.statements.append(("execute_unnamed", sql, {}))
        if self.statement_error is not None:
            raise self.statement_error
        return Context(self.rows, self.columns)

    def close(self):
        self.closed = True

    @property
    def sql(self):
        return [sql for _, sql, _ in self.statements]
