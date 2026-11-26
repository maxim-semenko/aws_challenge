"""SQL guard (spec 12 §Outputs "SQL guard", §Edge Cases; AC-12.2)."""

import logging

import pytest
import sqlglot

import sql_guard
from sql_guard import Rejected, check


def code_of(answer):
    with pytest.raises(Rejected) as raised:
        check(answer)
    return raised.value.code


# --- every hostile statement of spec 12 §Edge Cases, with its reject code ----------------------------------------------

HOSTILE = [
    ("DELETE FROM users", "NOT_SELECT"),
    ("DROP TABLE users", "NOT_SELECT"),
    ("SELECT 1; DELETE FROM users", "MULTIPLE_STATEMENTS"),
    ("SELECT * FROM users", "COLUMN_NOT_ALLOWED"),
    ("SELECT embedding FROM users", "COLUMN_NOT_ALLOWED"),
    ("SELECT * FROM pg_shadow", "TABLE_NOT_ALLOWED"),
    ("SELECT set_config('role','x',true)", "FUNCTION_NOT_ALLOWED"),
    ("SELECT pg_sleep(10)", "FUNCTION_NOT_ALLOWED"),
    ("WITH x AS (SELECT id FROM users) SELECT id FROM x", "NOT_SELECT"),
    ("SELECT id FROM users UNION SELECT id FROM users", "NOT_SELECT"),
    ("SELECT id FROM users FOR UPDATE", "NOT_SELECT"),
    ("SELECT id INTO t FROM users", "NOT_SELECT"),
    ("SELECT n FROM (SELECT count(*) AS n FROM users) t", "TABLE_NOT_ALLOWED"),
    ("SELECT current_user", "FUNCTION_NOT_ALLOWED"),
    ("SELECT 'users'::regclass FROM users", "FUNCTION_NOT_ALLOWED"),
    ("SELECT u.id FROM users u JOIN pg_user p ON true", "TABLE_NOT_ALLOWED"),
]


@pytest.mark.parametrize(("answer", "code"), HOSTILE, ids=[a for a, _ in HOSTILE])
def test_hostile_statements_of_the_spec_are_rejected_with_their_code(answer, code):
    assert code_of(answer) == code


@pytest.mark.parametrize(
    ("answer", "code"),
    [
        ("NONE", "NO_QUERY"),
        ("  none  ", "NO_QUERY"),
        ("", "NO_QUERY"),
        ("```\nNONE\n```", "NO_QUERY"),
        ("I cannot answer that question.", "PARSE_ERROR"),
        ("Here is the query: SELECT id FROM users", "PARSE_ERROR"),
        (";", "PARSE_ERROR"),
        ("SELECT id FROM users WHERE email = '" + "x" * 2000 + "'", "TOO_LONG"),
        ("SELECT id FROM users; SELECT email FROM users", "MULTIPLE_STATEMENTS"),
        ("INSERT INTO users (id) VALUES ('x')", "NOT_SELECT"),
        ("UPDATE users SET email = 'x'", "NOT_SELECT"),
        ("TRUNCATE users", "NOT_SELECT"),
        ("COPY users TO '/tmp/x'", "NOT_SELECT"),
        ("SET ROLE postgres", "NOT_SELECT"),
        ("VALUES (1)", "NOT_SELECT"),
        ("SELECT id FROM users EXCEPT SELECT id FROM users", "NOT_SELECT"),
        ("SELECT id FROM users INTERSECT SELECT id FROM users", "NOT_SELECT"),
        ("SELECT id FROM users FOR SHARE", "NOT_SELECT"),
        ("SELECT id FROM users WHERE id IN (SELECT id FROM users UNION SELECT id FROM users)", "NOT_SELECT"),
        ("SELECT id FROM users, pg_user", "TABLE_NOT_ALLOWED"),
        ("SELECT id FROM users u2 CROSS JOIN users", "TABLE_NOT_ALLOWED"),
        ("SELECT * FROM generate_series(1, 3)", "TABLE_NOT_ALLOWED"),
        ("SELECT id FROM pg_catalog.users", "TABLE_NOT_ALLOWED"),
        ("SELECT id FROM ONLY users", "TABLE_NOT_ALLOWED"),
        ("SELECT id FROM users TABLESAMPLE SYSTEM (10)", "TABLE_NOT_ALLOWED"),
        ("SELECT a FROM users AS u(a, b)", "TABLE_NOT_ALLOWED"),  # a column alias list could rename `embedding`
        ("SELECT 1", "TABLE_NOT_ALLOWED"),
        ("SELECT id FROM users WHERE id = (SELECT 1)", "TABLE_NOT_ALLOWED"),
        ("SELECT id FROM users WHERE EXISTS (SELECT 1 FROM pg_user)", "TABLE_NOT_ALLOWED"),
        ("SELECT pg_read_file('/etc/passwd') FROM users", "FUNCTION_NOT_ALLOWED"),
        ("SELECT dblink('x', 'y') FROM users", "FUNCTION_NOT_ALLOWED"),
        ("SELECT lo_import('/etc/passwd') FROM users", "FUNCTION_NOT_ALLOWED"),
        ("SELECT nextval('s') FROM users", "FUNCTION_NOT_ALLOWED"),
        ("SELECT pg_catalog.count(*) FROM users", "FUNCTION_NOT_ALLOWED"),
        ("SELECT count(*) OVER () FROM users", "FUNCTION_NOT_ALLOWED"),
        ("SELECT id::oid FROM users", "FUNCTION_NOT_ALLOWED"),
        ("SELECT CAST(id AS json) FROM users", "FUNCTION_NOT_ALLOWED"),
        ("SELECT CAST(height_cm AS int[]) FROM users", "FUNCTION_NOT_ALLOWED"),
        ("SELECT try_cast(id AS int) FROM users", "FUNCTION_NOT_ALLOWED"),
        ("SELECT id FROM users WHERE email = $1", "FUNCTION_NOT_ALLOWED"),
        ("SELECT id FROM users FETCH FIRST 5 ROWS ONLY", "FUNCTION_NOT_ALLOWED"),
        ("SELECT \"embedding\" FROM users", "COLUMN_NOT_ALLOWED"),
        ("SELECT EMBEDDING FROM users", "COLUMN_NOT_ALLOWED"),
        ("SELECT u.* FROM users u", "COLUMN_NOT_ALLOWED"),
        ("SELECT users FROM users", "COLUMN_NOT_ALLOWED"),  # whole-row reference
        ("SELECT ctid FROM users", "COLUMN_NOT_ALLOWED"),
        ("SELECT p.id FROM users u", "COLUMN_NOT_ALLOWED"),
        ("SELECT public.users.id FROM users", "COLUMN_NOT_ALLOWED"),
        ("SELECT count(*) FROM users WHERE embedding IS NULL", "COLUMN_NOT_ALLOWED"),
        ("SELECT id FROM users ORDER BY embedding <-> embedding", "FUNCTION_NOT_ALLOWED"),
        ("SELECT count(*) AS embedding FROM users GROUP BY embedding", "COLUMN_NOT_ALLOWED"),
        ("SELECT count(*) AS n FROM users WHERE n > 1", "COLUMN_NOT_ALLOWED"),  # alias only in ORDER/GROUP/HAVING
        ("SELECT count(*) AS n FROM users ORDER BY users.n", "COLUMN_NOT_ALLOWED"),
        ("SELECT id FROM users;;", "MULTIPLE_STATEMENTS"),  # only one trailing `;` is allowed
        ("SELECT id FROM users; ;", "MULTIPLE_STATEMENTS"),
    ],
)
def test_more_hostile_or_unusable_answers_are_rejected(answer, code):
    assert code_of(answer) == code


# ARCH review B1 (2026-11-26): a select-list alias named like the table or a table alias must not reach a whole-row
# reference (`u`, `users` include `embedding`); the alias exception applies only to a bare ORDER BY item or a direct
# GROUP BY element, never inside an expression and never in HAVING.
ALIAS_PROBES = [
    "SELECT id, count(*) AS u FROM users u GROUP BY id HAVING max(CAST(u AS text)) LIKE '%[0.0%'",
    "SELECT id, count(*) AS users FROM users GROUP BY id HAVING max(CAST(users AS text)) LIKE '%'",
    "SELECT id AS u FROM users u ORDER BY length(CAST(u AS text)) DESC",
    "SELECT id AS u FROM users u ORDER BY u",
    "SELECT id AS users FROM users GROUP BY users",
    "SELECT count(*) AS n FROM users GROUP BY country HAVING n > 1",
    "SELECT count(*) AS n FROM users GROUP BY country ORDER BY n + 1",
    "SELECT count(*) AS n FROM users GROUP BY country ORDER BY -n",
    "SELECT height_cm AS h FROM users GROUP BY h + 1",
    "SELECT count(*) AS n FROM users WHERE id IN (SELECT id FROM users ORDER BY n)",
]


@pytest.mark.parametrize("answer", ALIAS_PROBES)
def test_alias_exception_only_for_bare_order_by_items_and_group_by_elements(answer):
    assert code_of(answer) == "COLUMN_NOT_ALLOWED"


@pytest.mark.parametrize(
    "answer",
    [
        "SELECT country, count(*) AS n FROM users GROUP BY country ORDER BY n DESC NULLS LAST",
        "SELECT height_cm / 10 AS band, count(*) FROM users GROUP BY band ORDER BY band",
        "SELECT country AS c, count(*) FROM users GROUP BY c",
    ],
)
def test_alias_exception_still_works_for_bare_items(answer):
    check(answer)

# --- accepted statements (AC-12.2) ------------------------------------------------------------------------------------

ACCEPTED = [
    "SELECT count(*) FROM users WHERE country IN ('PL','Poland') AND weight_kg > 70 "
    "AND date_part('year', age(birthdate)) BETWEEN 25 AND 35",
    "SELECT gender, avg(weight_kg) AS avg_weight FROM users GROUP BY gender",
    "SELECT country, count(*) AS n FROM users GROUP BY country ORDER BY n DESC",
    "SELECT count(*) FROM users WHERE gender IN ('F','female')",
    "SELECT email, given_name, family_name FROM users ORDER BY created_at DESC LIMIT 10",
    "SELECT u.email FROM public.users AS u WHERE u.height_cm > 180 ORDER BY u.height_cm DESC",
    "SELECT round(avg(height_cm)::numeric, 1) FROM users WHERE lower(country) LIKE 'po%'",
    "SELECT CASE WHEN weight_kg > 80 THEN 'heavy' ELSE 'light' END AS band, count(*) FROM users GROUP BY band",
    "SELECT extract(year FROM birthdate) AS y, count(DISTINCT gender) FROM users GROUP BY y HAVING count(*) > 1",
    "SELECT date_trunc('month', created_at) AS m, count(*) FROM users WHERE created_at > now() - interval '30 days' "
    "GROUP BY m ORDER BY m",
    "SELECT to_char(confirmed_at, 'YYYY-MM') FROM users WHERE confirmed_at IS NOT NULL AND current_date > birthdate",
    "SELECT coalesce(nullif(trim(country), ''), 'unknown'), max(weight_kg), min(weight_kg), sum(height_cm) FROM users "
    "GROUP BY 1",
    "SELECT email FROM users WHERE height_cm = (SELECT max(height_cm) FROM users)",
    "SELECT email FROM users WHERE id IN (SELECT id FROM users WHERE gender ILIKE 'f%') AND NOT (weight_kg < 50)",
    "SELECT abs(height_cm - 170), floor(weight_kg / 10.0), ceil(1.5), length(email), upper(family_name) FROM users",
    "SELECT CAST(birthdate AS text), height_cm::double precision, weight_kg::varchar(5), created_at::date, "
    "updated_at::timestamptz, id::text, (weight_kg > 70)::boolean, '1 day'::interval FROM users",
    "SELECT email FROM users WHERE EXISTS (SELECT 1 FROM users u2 WHERE u2.email = users.email)",
    "SELECT \"email\" FROM \"users\"",
    "SELECT Email FROM Users",
]


@pytest.mark.parametrize("answer", ACCEPTED)
def test_reasonable_statements_are_accepted(answer):
    accepted = check(answer)
    assert sqlglot.parse_one(accepted.sql, read="postgres") is not None


def test_alias_in_order_by_is_accepted_and_rendered():
    accepted = check("SELECT country, count(*) AS n FROM users GROUP BY country ORDER BY n DESC")
    assert accepted.sql == "SELECT country, COUNT(*) AS n FROM users GROUP BY country ORDER BY n DESC LIMIT 101"


# --- LIMIT enforcement and rendering ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("answer", "limit"),
    [
        ("SELECT email FROM users", "LIMIT 101"),
        ("SELECT email FROM users LIMIT 500", "LIMIT 101"),
        ("SELECT email FROM users LIMIT 101", "LIMIT 101"),
        ("SELECT email FROM users LIMIT 100", "LIMIT 100"),
        ("SELECT email FROM users LIMIT 10", "LIMIT 10"),
        ("SELECT email FROM users LIMIT 0", "LIMIT 0"),
        ("SELECT email FROM users LIMIT ALL", "LIMIT 101"),
        ("SELECT email FROM users LIMIT 2 + 3", "LIMIT 101"),
    ],
)
def test_limit_is_at_most_101(answer, limit):
    assert check(answer).sql.endswith(limit)


def test_offset_is_kept_with_a_small_limit():
    assert check("SELECT email FROM users ORDER BY email LIMIT 10 OFFSET 20").sql.endswith("LIMIT 10 OFFSET 20")


def test_inner_limit_is_not_changed_outer_limit_is_set():
    sql = check("SELECT email FROM users WHERE id IN (SELECT id FROM users LIMIT 500)").sql
    assert sql == "SELECT email FROM users WHERE id IN (SELECT id FROM users LIMIT 500) LIMIT 101"


def test_executed_text_is_the_rendering_comments_and_trailing_semicolon_never_reach_the_db():
    answer = "SELECT email /* hidden */ FROM users -- DROP TABLE users\n;"
    sql = check(answer).sql
    assert sql == "SELECT email FROM users LIMIT 101"
    assert "--" not in sql and "/*" not in sql and ";" not in sql and "DROP" not in sql


def test_one_markdown_fence_is_removed():
    assert check("```sql\nSELECT email FROM users LIMIT 5\n```").sql == "SELECT email FROM users LIMIT 5"
    assert check("  ```\nSELECT email FROM users LIMIT 5;\n```  ").sql == "SELECT email FROM users LIMIT 5"


def test_rendering_is_a_single_statement_without_semicolon():
    for answer in ACCEPTED:
        sql = check(answer).sql
        statements = [s for s in sqlglot.parse(sql, read="postgres") if s is not None]
        assert len(statements) == 1 and ";" not in sql.replace("';'", "")


def test_2000_characters_are_allowed_2001_are_too_long():
    base = "SELECT email FROM users WHERE email = ''"
    exact = base[:-1] + "x" * (2000 - len(base)) + "'"
    assert len(exact) == 2000
    check(exact)
    assert code_of(exact[:-1] + "x'") == "TOO_LONG"


def test_absurd_nesting_is_rejected_not_raised():
    answer = "SELECT " + "(" * 900 + "1" + ")" * 900 + " FROM users"
    assert code_of(answer) in {"PARSE_ERROR", "TOO_LONG"}


def test_sqlglot_logger_never_writes_sql_text(caplog):
    caplog.set_level(logging.DEBUG)
    code_of("SELECT try_cast(id AS int) FROM users")  # sqlglot would warn "TRY_CAST is unsupported"
    check("SELECT email FROM users")
    assert logging.getLogger("sqlglot").disabled is True
    assert not [r for r in caplog.records if r.name.startswith("sqlglot")]


def test_allowlist_matches_the_spec():
    assert sql_guard.ALLOWED_COLUMNS == {
        "id", "email", "given_name", "family_name", "gender", "birthdate", "country", "height_cm", "weight_kg",
        "confirmed_at", "created_at", "updated_at",
    }
    assert "embedding" not in sql_guard.ALLOWED_COLUMNS


@pytest.mark.parametrize(
    "function_call",
    ["count(id)", "sum(height_cm)", "avg(height_cm)", "min(height_cm)", "max(height_cm)", "round(1.5)",
     "floor(1.5)", "ceil(1.5)", "abs(-1)", "lower(email)", "upper(email)", "trim(email)", "length(email)",
     "coalesce(email, 'x')", "nullif(email, 'x')", "date_part('year', birthdate)", "extract(year FROM birthdate)",
     "date_trunc('month', created_at)", "age(birthdate)", "current_date", "now()", "to_char(created_at, 'YYYY')"],
)
def test_every_function_of_the_spec_allowlist_is_accepted(function_call):
    check(f"SELECT {function_call} FROM users")
