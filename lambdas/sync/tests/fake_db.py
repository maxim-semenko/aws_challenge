"""In-memory test double of a pg8000.native.Connection for the migration runner (no database)."""

import pg8000.native

import migrator as lf


class FakeConnection:
    def __init__(self, history=None, lock_available=True, fail_on=None, applied_meanwhile=(), lost_on=None):
        # version -> (description, checksum); committed state
        self.history = dict(history or {})
        self.executed = []  # committed migration SQL, in order
        self.transactions = []  # committed transactions: (sql list, history rows)
        self.statements = []  # every statement sent, for assertions
        self.lock_available = lock_available
        self.fail_on = fail_on
        # (marker, exception): the migration SQL containing marker, or the statement equal to it, raises exception
        self.lost_on = lost_on
        self.applied_meanwhile = set(applied_meanwhile)
        self.history_table_created = False
        self.rollbacks = 0
        self.closed = False
        self._tx = None

    def _maybe_lose_connection(self, sql, exact):
        if self.lost_on and (sql == self.lost_on[0] if exact else self.lost_on[0] in sql):
            raise self.lost_on[1]

    def run(self, sql, **params):
        self.statements.append(sql)
        self._maybe_lose_connection(sql, exact=True)
        if sql == "BEGIN":
            assert self._tx is None, "nested transaction"
            self._tx = {"sql": [], "history": {}}
        elif sql == "COMMIT":
            self.executed.extend(self._tx["sql"])
            self.history.update(self._tx["history"])
            self.transactions.append((self._tx["sql"], self._tx["history"]))
            self._tx = None
        elif sql == "ROLLBACK":
            self._tx = None
            self.rollbacks += 1
        elif sql == lf.SQL_CREATE_HISTORY:
            self.history_table_created = True
            return []
        elif sql == lf.SQL_SELECT_APPLIED:
            return [[version, row[1]] for version, row in sorted(self.history.items())]
        elif sql == lf.SQL_TRY_LOCK:
            assert self._tx is not None, "lock outside a transaction"
            assert params == {"key": lf.LOCK_KEY}
            return [[self.lock_available]]
        elif sql == lf.SQL_IS_APPLIED:
            version = params["version"]
            return [[1]] if version in self.history or version in self.applied_meanwhile else []
        elif sql == lf.SQL_INSERT_HISTORY:
            assert self._tx is not None, "history row outside the migration transaction"
            self._tx["history"][params["version"]] = (params["description"], params["checksum"])
        else:
            raise AssertionError(f"unexpected statement: {sql}")
        return []

    def execute_simple(self, sql):
        assert self._tx is not None, "migration outside a transaction"
        self.statements.append(sql)
        self._maybe_lose_connection(sql, exact=False)
        if self.fail_on and self.fail_on in sql:
            raise pg8000.native.DatabaseError({"S": "ERROR", "C": "42601", "M": "syntax error"})
        self._tx["sql"].append(sql)

    def close(self):
        self.closed = True
