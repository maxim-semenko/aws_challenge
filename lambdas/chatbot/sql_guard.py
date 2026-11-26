"""SQL guard for LLM-generated statements (spec 12 §Outputs "SQL guard", design semantic-search §5).

The model's answer is untrusted code. It is parsed with sqlglot (PostgreSQL dialect) and accepted only if the whole
tree consists of allowlisted parts; the statement that runs is the guard's re-rendering of the validated tree (never
the model's text), with LIMIT forced to at most 101. Checks run in a fixed order, the first failing rule gives the
reject code: NO_QUERY -> TOO_LONG -> PARSE_ERROR -> MULTIPLE_STATEMENTS -> NOT_SELECT -> TABLE_NOT_ALLOWED (FROM items)
-> FUNCTION_NOT_ALLOWED (every expression node) -> TABLE_NOT_ALLOWED (SELECT without FROM) -> COLUMN_NOT_ALLOWED.
Node classes are compared exactly (type(node) is X), never with isinstance, so a subclass (e.g. TryCast of Cast)
is not accepted by accident. Rules and how to change an allowlist: the chatbot-api skill.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import sqlglot
from sqlglot import exp

# sqlglot logs warnings that quote the parsed SQL (e.g. unsupported syntax); the log must never hold SQL text.
logging.getLogger("sqlglot").disabled = True

DIALECT = "postgres"
MAX_LENGTH = 2000
ROW_CAP = 100
FETCH_LIMIT = ROW_CAP + 1  # one extra row tells whether the result was truncated

NO_QUERY = "NO_QUERY"
TOO_LONG = "TOO_LONG"
PARSE_ERROR = "PARSE_ERROR"
MULTIPLE_STATEMENTS = "MULTIPLE_STATEMENTS"
NOT_SELECT = "NOT_SELECT"
TABLE_NOT_ALLOWED = "TABLE_NOT_ALLOWED"
COLUMN_NOT_ALLOWED = "COLUMN_NOT_ALLOWED"
FUNCTION_NOT_ALLOWED = "FUNCTION_NOT_ALLOWED"
ACCEPTED = "ACCEPTED"

TABLE = "users"
SCHEMA = "public"
# Every column of `users` (spec 06 §Outputs) except `embedding`.
ALLOWED_COLUMNS = frozenset({
    "id", "email", "given_name", "family_name", "gender", "birthdate", "country", "height_cm", "weight_kg",
    "confirmed_at", "created_at", "updated_at",
})
# Real columns that must never be reached through the select-list alias exception (GROUP BY resolves a bare name to an
# input column first in PostgreSQL): the vector and the system columns. The table name and table aliases are excluded
# as well (whole-row reference), see _check_columns.
NEVER_ALIASES = frozenset({"embedding", "ctid", "xmin", "xmax", "cmin", "cmax", "tableoid", "oid"})

# Functions of the spec 12 allowlist as sqlglot parses them in the PostgreSQL dialect (checked by the tests):
# count sum avg min max round floor ceil abs lower upper trim length coalesce nullif; date_part/extract -> Extract;
# date_trunc -> TimestampTrunc; current_date -> CurrentDate; now() -> CurrentTimestamp; to_char -> TimeToStr.
FUNCTION_NODES = frozenset({
    exp.Count, exp.Sum, exp.Avg, exp.Min, exp.Max, exp.Round, exp.Floor, exp.Ceil, exp.Abs, exp.Lower, exp.Upper,
    exp.Trim, exp.Length, exp.Coalesce, exp.Nullif, exp.Extract, exp.TimestampTrunc, exp.DateTrunc, exp.CurrentDate,
    exp.CurrentTimestamp, exp.TimeToStr,
})
# Allowlisted functions that sqlglot keeps as a generic call (exp.Anonymous), by lower-case name.
ANONYMOUS_FUNCTIONS = frozenset({"age", "date_part", "date_trunc", "now", "to_char", "current_date"})
# Operators and expression syntax: CASE, comparison, arithmetic, logical, LIKE/ILIKE, IN, BETWEEN, IS [NOT] NULL,
# DISTINCT, string concatenation, literals, parentheses, scalar / IN / EXISTS subqueries (checked as statements too).
OPERATOR_NODES = frozenset({
    exp.Case, exp.If, exp.EQ, exp.NEQ, exp.GT, exp.GTE, exp.LT, exp.LTE, exp.NullSafeEQ, exp.NullSafeNEQ,
    exp.Add, exp.Sub, exp.Mul, exp.Div, exp.Mod, exp.Neg, exp.And, exp.Or, exp.Not, exp.Like, exp.ILike, exp.In,
    exp.Between, exp.Is, exp.Distinct, exp.DPipe, exp.Literal, exp.Null, exp.Boolean, exp.Paren, exp.Exists,
    exp.Interval,
})
# Statement structure; the table and column rules check these separately.
STRUCTURE_NODES = frozenset({
    exp.Select, exp.From, exp.Table, exp.TableAlias, exp.Identifier, exp.Column, exp.Star, exp.Alias, exp.Where,
    exp.Group, exp.Having, exp.Order, exp.Ordered, exp.Limit, exp.Offset, exp.Subquery,
})
SELECT_KEYS = frozenset({"expressions", "distinct", "from_", "where", "group", "having", "order", "limit", "offset"})
TABLE_KEYS = frozenset({"this", "db", "alias"})
CAST_TYPES = frozenset({
    exp.DataType.Type.SMALLINT, exp.DataType.Type.INT, exp.DataType.Type.BIGINT, exp.DataType.Type.DECIMAL,
    exp.DataType.Type.FLOAT, exp.DataType.Type.DOUBLE, exp.DataType.Type.TEXT, exp.DataType.Type.VARCHAR,
    exp.DataType.Type.DATE, exp.DataType.Type.TIMESTAMP, exp.DataType.Type.TIMESTAMPTZ, exp.DataType.Type.INTERVAL,
    exp.DataType.Type.BOOLEAN,
})
# A unit keyword (Var) is allowed only in these places: EXTRACT(<unit> FROM …), date_trunc unit, interval unit,
# LIMIT ALL.
VAR_PLACES = {exp.Extract: "this", exp.TimestampTrunc: "unit", exp.DateTrunc: "unit", exp.Interval: "unit"}

FENCE = re.compile(r"^```[A-Za-z0-9_-]*[ \t]*\r?\n?(.*?)\r?\n?```$", re.DOTALL)


class Rejected(Exception):
    """The answer is not a safe statement; args[0] is the reject code."""

    @property
    def code(self) -> str:
        return str(self.args[0])


@dataclass(frozen=True)
class Accepted:
    sql: str  # the guard's rendering, executed as is


def _strip(answer: str) -> str:
    text = answer.strip()
    fenced = FENCE.match(text)
    return fenced.group(1).strip() if fenced else text


def _name(identifier: exp.Expression | None) -> str | None:
    """Identifier as PostgreSQL resolves it: unquoted names fold to lower case."""
    if not isinstance(identifier, exp.Identifier):
        return None
    text = identifier.this
    return text if identifier.args.get("quoted") else text.lower()


def _parse(text: str) -> exp.Select:
    try:
        parsed = sqlglot.parse(text, read=DIALECT)
    except Exception as exc:  # ParseError, TokenError, RecursionError on absurd nesting: never accepted
        raise Rejected(PARSE_ERROR) from exc
    # sqlglot yields one entry per `;`-separated part; a single trailing `;` adds none, `;;` adds an empty one (None).
    if not [s for s in parsed if s is not None]:
        raise Rejected(PARSE_ERROR)
    if len(parsed) > 1:
        raise Rejected(MULTIPLE_STATEMENTS)
    return parsed[0]


def _check_shape(tree: exp.Expression) -> None:
    if type(tree) is not exp.Select:
        raise Rejected(NOT_SELECT)
    for node in tree.walk():
        if isinstance(node, (exp.With, exp.CTE, exp.SetOperation, exp.Into, exp.Lock)):
            raise Rejected(NOT_SELECT)
        if type(node) is exp.Select:
            keys = {key for key, value in node.args.items() if value}
            if keys - SELECT_KEYS - {"joins", "laterals"}:
                raise Rejected(NOT_SELECT)
        if type(node) is exp.Subquery and (type(node.this) is not exp.Select or set(
            key for key, value in node.args.items() if value
        ) - {"this", "alias"}):
            raise Rejected(NOT_SELECT)


def _users_table(table: exp.Expression) -> bool:
    if type(table) is not exp.Table:
        return False
    if {key for key, value in table.args.items() if value} - TABLE_KEYS:
        return False  # ONLY, TABLESAMPLE, catalog, pivots, hints, …
    if _name(table.this) != TABLE:
        return False
    if table.args.get("db") is not None and _name(table.args["db"]) != SCHEMA:
        return False
    alias = table.args.get("alias")
    if alias is not None:  # `users AS u` only; a column alias list `u(a, b)` could rename `embedding`
        if type(alias) is not exp.TableAlias or alias.args.get("columns") or _name(alias.this) is None:
            return False
    return True


def _check_tables(tree: exp.Expression) -> None:
    for node in tree.walk():
        if isinstance(node, (exp.Join, exp.Lateral, exp.Values, exp.Unnest, exp.TableSample, exp.Pivot)):
            raise Rejected(TABLE_NOT_ALLOWED)
        if type(node) is exp.Select:
            if node.args.get("joins") or node.args.get("laterals"):
                raise Rejected(TABLE_NOT_ALLOWED)
            source = node.args.get("from_")
            if source is not None and (type(source) is not exp.From or not _users_table(source.this)):
                raise Rejected(TABLE_NOT_ALLOWED)
        if type(node) is exp.Table:
            parent = node.parent
            if type(parent) is not exp.From or node.arg_key != "this" or type(parent.parent) is not exp.Select:
                raise Rejected(TABLE_NOT_ALLOWED)
        if type(node) is exp.From and (type(node.parent) is not exp.Select or node.arg_key != "from_"):
            raise Rejected(TABLE_NOT_ALLOWED)


def _allowed_node(node: exp.Expression) -> bool:
    kind = type(node)
    if kind in STRUCTURE_NODES or kind in OPERATOR_NODES or kind in FUNCTION_NODES:
        return True
    if kind is exp.Anonymous:
        return isinstance(node.this, str) and node.this.lower() in ANONYMOUS_FUNCTIONS
    if kind is exp.Cast:
        return type(node.args.get("to")) is exp.DataType
    if kind is exp.DataType:
        return (
            type(node.parent) is exp.Cast
            and node.this in CAST_TYPES
            and not node.args.get("nested")
            and all(type(param) is exp.DataTypeParam for param in node.expressions)
        )
    if kind is exp.DataTypeParam:
        return type(node.parent) is exp.DataType and type(node.this) is exp.Literal and not node.this.is_string
    if kind is exp.Var:
        parent = node.parent
        if type(parent) is exp.Limit:
            return node.arg_key == "expression" and node.name.upper() == "ALL"
        return parent is not None and VAR_PLACES.get(type(parent)) == node.arg_key
    return False


def _check_functions(tree: exp.Expression) -> None:
    for node in tree.walk():
        if not _allowed_node(node):
            raise Rejected(FUNCTION_NOT_ALLOWED)


def _check_from_present(tree: exp.Expression) -> None:
    for node in tree.walk():
        if type(node) is exp.Select and node.args.get("from_") is None:
            raise Rejected(TABLE_NOT_ALLOWED)


def _table_aliases(tree: exp.Expression) -> set[str]:
    names = {TABLE}
    for table in tree.find_all(exp.Table):
        alias = table.args.get("alias")
        if alias is not None and _name(alias.this):
            names.add(_name(alias.this))  # type: ignore[arg-type]
    return names


def _select_aliases(select: exp.Select) -> set[str]:
    return {_name(item.args.get("alias")) for item in select.expressions if type(item) is exp.Alias} - {None}  # type: ignore[return-value]


def _is_alias_item(column: exp.Column, select: exp.Select) -> bool:
    """True only when the column IS a whole ORDER BY item or a direct GROUP BY element of `select`.

    PostgreSQL resolves a select-list alias only there (as the bare item); inside an expression, and anywhere in HAVING,
    a name refers to an input column or to a whole-row reference (`users`, a table alias), which includes `embedding`.
    """
    parent = column.parent
    if type(parent) is exp.Ordered and column.arg_key == "this":
        order = parent.parent
        return type(order) is exp.Order and parent.arg_key == "expressions" and order.parent is select             and order.arg_key == "order"
    if type(parent) is exp.Group and column.arg_key == "expressions":
        return parent.parent is select and parent.arg_key == "group"
    return False


def _check_columns(tree: exp.Expression) -> None:
    qualifiers = _table_aliases(tree)
    for node in tree.walk():
        if type(node) is exp.Star:
            if not (type(node.parent) is exp.Count and node.arg_key == "this"):
                raise Rejected(COLUMN_NOT_ALLOWED)
        if type(node) is not exp.Column:
            continue
        if type(node.this) is not exp.Identifier or node.args.get("db") or node.args.get("catalog"):
            raise Rejected(COLUMN_NOT_ALLOWED)  # `u.*`, `public.users.id`
        table = node.args.get("table")
        if table is not None and _name(table) not in qualifiers:
            raise Rejected(COLUMN_NOT_ALLOWED)
        name = _name(node.this)
        if name in ALLOWED_COLUMNS:
            continue
        select = node.find_ancestor(exp.Select)
        if (
            table is None
            and select is not None
            and name not in NEVER_ALIASES
            and name not in qualifiers  # the table name or a table alias would be a whole-row reference
            and name in _select_aliases(select)
            and _is_alias_item(node, select)
        ):
            continue
        raise Rejected(COLUMN_NOT_ALLOWED)


def _enforce_limit(tree: exp.Select) -> None:
    limit = tree.args.get("limit")
    value = limit.args.get("expression") if type(limit) is exp.Limit else None
    if type(value) is exp.Literal and not value.is_string and value.this.isdigit() and int(value.this) <= ROW_CAP:
        return
    tree.set("limit", exp.Limit(expression=exp.Literal.number(FETCH_LIMIT)))


def check(answer: str) -> Accepted:
    """Validate the model's answer; return the statement to execute or raise Rejected(<code>)."""
    text = _strip(answer)
    if text == "" or text.upper() == "NONE":
        raise Rejected(NO_QUERY)
    if len(text) > MAX_LENGTH:
        raise Rejected(TOO_LONG)
    tree = _parse(text)
    try:
        _check_shape(tree)
        _check_tables(tree)
        _check_functions(tree)
        _check_from_present(tree)
        _check_columns(tree)
        assert type(tree) is exp.Select
        _enforce_limit(tree)
        sql = tree.sql(dialect=DIALECT, comments=False)
    except Rejected:
        raise
    except Exception as exc:  # any surprise inside the guard rejects the statement
        raise Rejected(PARSE_ERROR) from exc
    return Accepted(sql)
