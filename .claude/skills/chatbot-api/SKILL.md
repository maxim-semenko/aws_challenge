---
name: chatbot-api
description: How the API handler aws-challenge-chatbot (lambdas/chatbot) serves POST /chat for administrators — check order (401/404/403/400 before any Bedrock or DB call), body rules, the "sql" keyword mode rule and the similarity-prefix strip, the vector path (shared Titan helper + pgvector top-5), the SQL path (Nova Micro Converse prompt, the sqlglot SQL guard with its reject codes, LIMIT rewrite, read-only transaction with statement_timeout), value mapping, error mapping (429/502/400/500), the one-JSON-line log without query/SQL text, the pytest doubles and how to change an allowlist or the model. Use when changing lambdas/chatbot, reviewing the SQL guard, writing the runbook that deploys the chatbot, or reviewing evidence for spec 12.
license: MIT
metadata:
  domain: backend
  triggers: lambdas/chatbot, aws-challenge-chatbot, POST /chat, Converse, Nova Micro, eu.amazon.nova-micro-v1:0, sqlglot, SQL guard, NL to SQL, guardResult, NO_QUERY, NOT_SELECT, TABLE_NOT_ALLOWED, COLUMN_NOT_ALLOWED, FUNCTION_NOT_ALLOWED, BEGIN READ ONLY, statement_timeout, queryHash, sqlHash, similar to
  role: specialist
  scope: implementation
  related-skills: python-lambda, bedrock-embeddings, admin-api, http-api-jwt, postgres-pro, test-master
  source: project (created by T05-02)
  used-by: [backend, tester, devops, architect]
---

# Chat API handler (`lambdas/chatbot`)

Contract (single home — link, never copy field tables, error texts or ACs): [spec 12](../../../docs/specs/12-chat-api.md);
design [semantic-search](../../../docs/design/semantic-search.md) §4–§7, §9; decisions ADR-021 (direct `Converse`, no
Bedrock Agent), ADR-022 (Nova Micro via the EU inference profile), Q-23 A / R-19 (master DB user + guard + read-only
transaction). Layout, packaging, DB helper: [python-lambda](../python-lambda/SKILL.md); claims and problem+json:
`lambdas/shared/http_api.py` (shared with `admin`, [admin-api](../admin-api/SKILL.md)); Titan client:
[bedrock-embeddings](../bedrock-embeddings/SKILL.md); route, authorizer, integration timeout:
[http-api-jwt](../http-api-jwt/SKILL.md). Deployed settings: [ENVIRONMENT.md](../../../docs/ENVIRONMENT.md).

## Code map

| File | What |
|---|---|
| `lambda_function.py` | handler: check order, `parse_query` (body), `mode_of`, `strip_similarity_prefix`, `_vector` / `_sql`, response, `_log` |
| `llm.py` | `MODEL_ID`, `INFERENCE_CONFIG`, `SYSTEM_PROMPT`, lazy client `_bedrock()` (connect 2 s, read 10 s, 1 attempt), `ask(query)` → `Answer(text, input_tokens, output_tokens)` or `LlmError(<errorClass>)` |
| `sql_guard.py` | `check(answer)` → `Accepted(sql)` or `Rejected(<code>)`; allowlists as module constants |
| `search.py` | `similar_users(vector)` (vector query), `run_statement(sql)` (guarded statement), `_read_only`, `to_json` (value mapping), `StatementError` |
| shared `embeddings.py` | `embed_with_usage(text)` → `(vector, inputTextTokenCount)` (same request and vector as `embed`) |
| shared `http_api.py` | `claims`, `authorized`, `parse_groups`, `is_admin`, `problem`, `json_response`, `ApiError` |
| `requirements.txt` | pg8000 pins as `sync` + `sqlglot` (plain wheel, no `sqlglotc`/`sqlglotrs` extras) |

## Request flow

1. 401 (`http_api.authorized`) → 404 (`routeKey != "POST /chat"`) → 403 (`http_api.is_admin`) → 400 (`parse_query`).
   Nothing touches Bedrock or the DB before all four pass. Query parameters, base64 bodies, the 4096-byte limit and
   the `query` rules are in `parse_query`; 400 details are fixed texts that never echo a value.
2. Mode: `\bsql\b` case-insensitive → `sql`, else `vector`. Vector mode strips the spec's similarity prefix first; an
   empty remainder is 400 (no Bedrock call).
3. Bedrock always before `db.connect()`; nothing is retried. One connection per request, `db.connect(timeout=5)`,
   closed in `finally`.
4. Every statement: `BEGIN READ ONLY` → `SET LOCAL statement_timeout = '4s'` → statement → `ROLLBACK` (always; a
   failing rollback is ignored, the connection is closed anyway).
5. SQL mode executes the guard's rendering with `conn.execute_unnamed(sql)` — the **extended protocol**, so
   PostgreSQL itself refuses a second statement (defence in depth behind the guard). The vector query uses
   `conn.run(SQL_VECTOR, q=<vector text>)` (parameter, never formatted).
6. Error mapping: Bedrock `ThrottlingException` → 429; any other Bedrock class (`UNREACHABLE`, `TIMEOUT`, AWS code,
   `BAD_RESPONSE`) → 502; guard rejection or `StatementError` (pg8000 `DatabaseError` whose SQLSTATE is not class
   `08`, incl. `57014` statement timeout and `25006` read-only violation) → 400 rephrase; `DbConnectError`, connection
   errors (`08xxx`, `InterfaceError`, `OSError`), a failing vector query or anything unexpected → 500.

## SQL guard (`sql_guard.py`) — review line by line on every change

- Order of checks = order of reject codes: `NO_QUERY` (after trimming and removing **one** surrounding Markdown fence)
  → `TOO_LONG` (> 2000 chars) → `PARSE_ERROR` (sqlglot `postgres`; any parser exception, also `RecursionError`) →
  `MULTIPLE_STATEMENTS` (one trailing `;` is allowed; `;;` is rejected) → `NOT_SELECT` → `TABLE_NOT_ALLOWED` (FROM items)
  → `FUNCTION_NOT_ALLOWED` (every node) → `TABLE_NOT_ALLOWED` (SELECT without FROM) → `COLUMN_NOT_ALLOWED`. Any
  other exception inside the checks or the rendering → `PARSE_ERROR` (reject, never accept).
- **Allowlist of node classes, not a blocklist.** Every node of the tree must be in `STRUCTURE_NODES`,
  `OPERATOR_NODES`, `FUNCTION_NODES`, an allowlisted `exp.Anonymous` name, a `Cast` to `CAST_TYPES`, or a unit `Var`
  in `VAR_PLACES` (`LIMIT ALL` too). Comparison is `type(node) is X` — a subclass (e.g. `TryCast` of `Cast`) is never
  accepted by accident.
- `NOT_SELECT`: root not `exp.Select`; any `With`/`CTE`/`SetOperation`/`Into`/`Lock` anywhere; a Select arg outside
  `SELECT_KEYS` (window clause, qualify, …); a `Subquery` that wraps anything but a Select.
- `TABLE_NOT_ALLOWED`: every `exp.Table` must be the `this` of the `from_` of a Select, named `users` (unquoted names
  fold to lower case, PostgreSQL rule), schema none or `public`, optional alias **without a column alias list**
  (`users u(a, b, …)` could rename `embedding` to an allowlisted name), no other Table arg (`ONLY`, `TABLESAMPLE`, …);
  no `Join`/`Lateral`/`Values`/`Unnest`/`TableSample`/`Pivot`; every Select (also subqueries) needs a FROM.
- `COLUMN_NOT_ALLOWED`: column name in `ALLOWED_COLUMNS` (spec 06 columns minus `embedding`); qualifier `users` or an
  alias of a `users` table in the statement; no schema/catalog part, no `u.*`; `*` only as `count(*)`. Exception
  (`_is_alias_item`): a select-list alias of the same Select is accepted only when the column **is** a whole
  `ORDER BY` item (`Ordered.this`) or a direct `GROUP BY` element — never inside an expression (`ORDER BY n + 1`),
  never in `HAVING`, never for the table name or a table alias (`users`, `u` there are whole-row references that
  include `embedding` — ARCH review B1, 2026-11-26) and never for `NEVER_ALIASES` (`embedding`, system columns;
  GROUP BY resolves input columns first in PostgreSQL).
- On acceptance: `LIMIT` of the root is kept when it is an integer literal ≤ 100, otherwise set to `101` (also
  `LIMIT ALL`, expressions); subquery limits and `OFFSET` are kept. The executed and returned `sql` is
  `tree.sql(dialect="postgres", comments=False)` — comments and the model's original text never reach the DB. sqlglot
  may normalise the text (upper-case function names, `now()` → `CURRENT_TIMESTAMP`, `::numeric` →
  `CAST(… AS DECIMAL)`, `round(avg(x), 1)` gets a cast) — what runs is exactly what was validated.
- The `sqlglot` logger is disabled at import: its warnings quote SQL text, which must never reach CloudWatch.

### Changing an allowlist

1. Spec 12 §SQL guard first (architect + owner), then the constant in `sql_guard.py`.
2. Find the sqlglot class: `sqlglot.parse_one("SELECT f(x) FROM users", read="postgres")` and print
   `type(node).__name__` for every node of `.walk()`; a function sqlglot does not know is `exp.Anonymous` → add its
   lower-case name to `ANONYMOUS_FUNCTIONS`. Prefer the typed class when it exists (its rendering is the function
   name sqlglot generates, not the model's spelling).
3. Add an accepted case and a hostile neighbour to `tests/test_sql_guard.py`; run the optional integration test
   against local PostgreSQL 14 (the rendering must run there).
4. A `sqlglot` upgrade can rename node classes or arg keys (e.g. `from_`, `with_` in 30.x): re-run every guard test;
   pin only versions with a `py3-none-any` wheel supporting Python 3.12.

## Prompt and model

- `llm.SYSTEM_PROMPT` follows spec 12 §Inputs "LLM prompt"; it lists exactly `ALLOWED_COLUMNS` (never `embedding`),
  both value forms of `gender` and `country`, the age expression and the rules (one SELECT on `users`, `LIMIT` ≤ 100,
  aggregates for "how many / average", `NONE`, no Markdown). The guard is the safety boundary, not the prompt.
- `MODEL_ID` is a code constant (`eu.amazon.nova-micro-v1:0`, confirmed by T05-01); the fallback Nova Lite
  (`eu.amazon.nova-lite-v1:0`) is a constant change plus the IAM ARNs of the role (design §2) — no other code change.
- `Converse` exists in boto3/botocore ≥ 1.34.116 (May 2024); the Lambda Python 3.12 runtime ships a newer boto3, so
  nothing is packaged. If a runtime ever lacked it, the call fails as `AttributeError` → 502 with that `errorClass`.
- Token usage: Converse `usage.inputTokens`/`outputTokens`; vector mode Titan `inputTextTokenCount`, output 0 (missing
  or invalid counts are 0, never an error).

## Log line

Exactly the fields of spec 12 §Outputs "Log line", always all keys (null when not reached), one line from `finally`.
`queryHash` = first 16 hex of SHA-256 of the trimmed query, `sqlHash` = the same of the executed SQL; `errorClass` =
Bedrock class (429/502), DB exception class name (400 from SQL, 500; for `DbConnectError` the class of its cause).
`message`: `request completed` (2xx/4xx incl. 429), `BEDROCK_FAILED` (502), `DB_CONNECT_FAILED` or `INTERNAL_ERROR`
(500). Never the query text, the model's answer, the SQL text, row values, the vector, headers or the token.

## Tests

```powershell
.venv\Scripts\python -m pip install -r lambdas/requirements-dev.txt -r lambdas/chatbot/requirements.txt
.venv\Scripts\python -m pytest lambdas/shared lambdas/chatbot
```

- `tests/conftest.py` puts `lambdas/chatbot`, `lambdas/shared` and `lambdas/shared/tests` (shared `bedrock_stub`) on
  `sys.path` (zip layout).
- `tests/doubles.py`: `StubConverse` (records `converse` kwargs; answers text, a raw dict or raises real botocore
  exceptions), `FakeConnection` (records `run`/`execute_unnamed`; vector rows, statement rows/columns, injected
  `DatabaseError`/`OSError`), `db_error(sqlstate)`.
- `test_sql_guard.py` (every hostile statement of spec 12 with its code, accepted statements, LIMIT, rendering,
  fences, logger), `test_llm.py` (request, prompt, client config, errors), `test_search.py` (transaction sequence,
  vector query, row cap, value mapping incl. intervals), `test_chatbot_api.py` (check order with a shared call log,
  body edge cases, modes, both paths, error mapping, log fields and forbidden values).
- `test_chatbot_integration.py`: optional, real PostgreSQL 14 + pgvector (`docker compose up -d`,
  `MIGRATE_TEST_DATABASE_URL` as for sync/admin): every accepted guard rendering runs, a write fails with `25006`,
  vector query order and NULL-distance drop.

## Deploy (runbook building blocks for devops; owner executes, CLAUDE.md §3.11)

Build `py -3.13 lambdas/package.py chatbot` → `build/lambdas/chatbot.zip` (record the SHA-256 in the task), upload to
`aws-challenge-chatbot` (Code → Upload from → .zip file). Settings (runtime 3.12, handler
`lambda_function.lambda_handler`, timeout 30 s, memory 512 MB, env `DB_PROXY_ENDPOINT`/`DB_NAME`/`DB_USER` only),
role policies and the 29 s integration timeout: spec 12 §Inputs, design §Security, T05-01 runbook. Bedrock works only
while the on-demand endpoint exists (ADR-020): without it every request is 502 `UNREACHABLE` after ≈ 2 s, no DB call.
