# Spec 12 — Chat API: `POST /chat` in the Chatbot Lambda (NL → SQL / vector similarity)

Requirements: [week-05](../requirements/week-05-semantic-search.md) task, W5-G1, W5-G2, S2, S3, S4, project
requirement · Design: [semantic-search](../design/semantic-search.md) §1–§7, §9 · ADR-018, ADR-019, ADR-020,
ADR-021, ADR-022
Tasks: T05-01, T05-02, T05-03, T05-05

Based on the owner's answers of 2026-11-25: [Q-21](../RISKS.md#q-21) A (direct `Converse`, no Bedrock Agent),
[Q-22](../RISKS.md#q-22) (Amazon Nova Micro via the EU inference profile) and [Q-23](../RISKS.md#q-23) A (master DB
user + guard + read-only transaction). Conventions:
CLAUDE.md §6; claims and group handling as [spec 08](08-admin-api.md); Titan request and client: [spec 10](10-embeddings.md);
column list: [spec 06](06-users-table-and-migrations.md) §Outputs.

## Purpose

An administrator sends a natural-language question to `POST /chat`. The handler `aws-challenge-chatbot` answers with
rows from PostgreSQL: if the question contains the keyword "sql", an LLM on Bedrock writes one read-only `SELECT` that
is validated and executed; otherwise the question is embedded with Titan V2 and the five most similar users are
returned. Every request writes one JSON log line with latencies and token counts.

## Inputs

**Common:** header `Authorization: Bearer <access token>` (ADR-004), JWT authorizer of spec 05; claims only from
`requestContext.authorizer.jwt.claims`: `sub`, `token_use`, `exp`, `cognito:groups` — rules exactly as spec 08
(401/403 conditions, group string formats).

**`POST /chat` body** — `Content-Type: application/json`, UTF-8, a JSON object (base64-encoded payloads are decoded
first); every field the SPA sends:

| Field | Type | Valid range | Required |
|---|---|---|---|
| `query` | string | 1 … 500 characters after trimming leading/trailing whitespace | yes |

Any other field, a non-object body, invalid JSON, a body above 4096 bytes, or `query` of another type → 400. No query
parameters are accepted (any → 400).

**Mode:** `sql` when the trimmed query matches `\bsql\b` case-insensitively; otherwise `vector`.

**Lambda configuration** (T05-01): runtime Python 3.12, handler `lambda_function.lambda_handler`, timeout **30 s**,
memory 512 MB, VPC as built; env `DB_PROXY_ENDPOINT`, `DB_NAME`, `DB_USER` (spec 06 §Inputs); no other env var (model
ids are code constants). HTTP API integration of `POST /chat`: Lambda `aws-challenge-chatbot`, payload 2.0, timeout
**29 s**.

**Code constants:**

| Constant | Value |
|---|---|
| Embedding model / dims | as spec 10 (`amazon.titan-embed-text-v2:0`, 1024, normalised), via `shared/embeddings.py` |
| LLM model id | `eu.amazon.nova-micro-v1:0` (EU geo inference profile; confirmed by T05-01 evidence) |
| LLM call | `Converse`, `inferenceConfig` `{"maxTokens": 300, "temperature": 0}`; client connect 2 s, read 10 s, `retries` `{"mode": "standard", "total_max_attempts": 1}` |
| DB | socket timeout 5 s; `statement_timeout` 4 s; one connection per request, closed in `finally` |
| Row cap | 100 rows (SQL mode), 5 rows (vector mode) |

**LLM prompt** (system prompt, code constant; the user message is the trimmed query):
- table `users` with the allowed columns and types of §SQL guard, meaning and units (`height_cm` cm, `weight_kg` kg,
  `birthdate` date; age in years = `date_part('year', age(birthdate))`);
- value conventions (real users vs seeded users store different forms, spec 04 / spec 11): `gender` is **either**
  `F`/`M` **or** `female`/`male` — a gender filter must match both forms (e.g. `gender IN ('F','female')`); `country`
  is **either** an ISO 3166-1 alpha-2 code (e.g. `PL`) **or** an English country name (e.g. `Poland`) — a country
  filter must match both forms;
- rules: answer with exactly one PostgreSQL `SELECT` on `users` only, no other table, no `embedding` column, no
  semicolon-separated statements, no data changes, `LIMIT` at most 100 for row lists, aggregate when the question asks
  "how many / average …"; the word "sql" in the question only selects this mode; answer exactly `NONE` when the question
  cannot be answered from this table; no explanation, no Markdown.

## Outputs

All bodies UTF-8 JSON, header `Cache-Control: no-store`; field names camelCase.

**200** `application/json`:

| Field | Type | Meaning |
|---|---|---|
| `mode` | `"sql"` \| `"vector"` | path taken |
| `columns` | string[] | column labels in row order. Vector mode: `id`, `email`, `givenName`, `familyName`, `gender`, `birthdate`, `country`, `heightCm`, `weightKg`, `distance`. SQL mode: the labels PostgreSQL returns for the executed statement (data, not API field names) |
| `rows` | (string \| number \| boolean \| null)[][] | one array per row, values in `columns` order |
| `rowCount` | integer | number of rows in `rows` (vector ≤ 5, SQL ≤ 100) |
| `truncated` | boolean | SQL mode: a 101st row existed; vector mode: `false` |
| `sql` | string \| null | SQL mode: the executed statement (the guard's rendering); vector mode: `null` |
| `timings` | `{ embedMs, llmMs, dbMs, totalMs }` integers; `embedMs` null in SQL mode, `llmMs` null in vector mode | server-side latencies |
| `tokens` | `{ input: integer, output: integer }` | SQL mode: Converse `usage.inputTokens`/`outputTokens`; vector mode: Titan `inputTextTokenCount`, `output` 0 |
| `modelId` | string | model id used (LLM profile id or the Titan id) |

**Value mapping:** integer → number; `numeric`/float → number when finite, else string; `date` → `YYYY-MM-DD`;
`timestamptz` → ISO-8601 UTC `YYYY-MM-DDTHH:MM:SSZ`; `uuid` → string; `interval` and any other type → its PostgreSQL
text form; `NULL` → `null`. Vector mode `distance`: float (L2 on unit vectors, 0 … 2).

**Errors** — `application/problem+json` `{ "type": "about:blank", "title", "status", "detail" }`, `detail` a fixed
text (never the query, SQL, SQLSTATE, model text or exception text):

| Status | When | `detail` |
|---|---|---|
| 400 | body/query invalid (see §Inputs); query empty after stripping the similarity prefix | names the problem (`query must be 1 to 500 characters`, `unknown field`, `body must be a JSON object`) without echoing values |
| 400 | SQL mode: model answered `NONE`, guard rejected the statement, the statement failed in PostgreSQL (any SQLSTATE except connection errors) or hit `statement_timeout` | `The question could not be turned into a safe query. Rephrase it.` |
| 401 | claims missing, `token_use` ≠ `access`, `sub`/`exp` invalid | as spec 08 |
| 403 | `admin` not in groups (no Bedrock or DB call) | `Membership in the group admin is required.` |
| 404 | route key other than `POST /chat` | as spec 08 |
| 429 | Bedrock `ThrottlingException` | `The AI service is busy. Try again shortly.` |
| 502 | any other Bedrock failure: `UNREACHABLE`, `TIMEOUT`, AWS error code (e.g. `AccessDeniedException`, `ValidationException`, `ResourceNotFoundException`), `BAD_RESPONSE` | `The AI service is not available.` |
| 500 | DB connection failure or unexpected error | `The request could not be completed.` |

Fixed API Gateway bodies stay (authorizer 401, unknown route 404; ARCHITECTURE §3.3); an integration timeout would be
503 `{"message":"Service Unavailable"}` from API Gateway (prevented by the time budget of §Behaviour).

**SQL guard** (applied to the model's answer; outcome `guardResult` in the log):

| Rule | Reject code |
|---|---|
| answer after trimming and removing one surrounding Markdown code fence is `NONE` (case-insensitive) or empty | `NO_QUERY` |
| longer than 2000 characters | `TOO_LONG` |
| does not parse (PostgreSQL dialect, `sqlglot`) | `PARSE_ERROR` |
| more than one statement (a single trailing `;` is allowed) | `MULTIPLE_STATEMENTS` |
| root is not a plain `SELECT`: `WITH`, set operations (`UNION`, `INTERSECT`, `EXCEPT`), `SELECT … INTO`, locking clause (`FOR UPDATE/SHARE`), or any non-SELECT statement | `NOT_SELECT` |
| a `FROM` item (in the statement or any subquery) other than the table `users` / `public.users` with an optional alias: joins, derived tables (`FROM (SELECT …)`), table functions, `VALUES` lists; a `SELECT` without `FROM` | `TABLE_NOT_ALLOWED` |
| any column outside the allowlist `id`, `email`, `given_name`, `family_name`, `gender`, `birthdate`, `country`, `height_cm`, `weight_kg`, `confirmed_at`, `created_at`, `updated_at` (so `embedding` is always rejected); a qualifier other than `users` or its alias; `*` except inside `count(*)`. Exception: a bare name in `ORDER BY`, `GROUP BY` or `HAVING` that equals an alias defined in the same select list | `COLUMN_NOT_ALLOWED` |
| any function outside the allowlist `count`, `sum`, `avg`, `min`, `max`, `round`, `floor`, `ceil`, `abs`, `lower`, `upper`, `trim`, `length`, `coalesce`, `nullif`, `date_part`, `extract`, `date_trunc`, `age`, `current_date`, `now`, `to_char` (plus `CASE`, comparison/arithmetic/logical operators, `LIKE`/`ILIKE`, `IN`, `BETWEEN`, `IS NULL`, `DISTINCT`); a `CAST`/`::` to a type outside `smallint`, `integer`, `bigint`, `numeric`/`decimal`, `real`, `double precision`, `text`, `varchar`, `date`, `timestamp`, `timestamptz`, `interval`, `boolean` | `FUNCTION_NOT_ALLOWED` |
| accepted | `ACCEPTED` |

On acceptance the guard sets `LIMIT 101` when the statement has no `LIMIT` or a `LIMIT` above 100 (an existing
`LIMIT` ≤ 100 and `OFFSET` are kept) and renders the statement from the parsed tree; this rendering is executed and
returned as `sql`.

**Vector query** (curriculum form, vector as a parameter):
`SELECT id, email, given_name, family_name, gender, birthdate, country, height_cm, weight_kg, embedding <-> CAST(:q AS vector) AS distance FROM users ORDER BY embedding <-> CAST(:q AS vector) LIMIT 5`;
rows with a NULL distance are dropped.

**Log line** (one JSON object per request, log group `/aws/lambda/aws-challenge-chatbot`, retention 14 days):
`level`, `message`, `function`, `awsRequestId`, `apiRequestId`, `userSub`, `route`, `status`, `outcome`
(`success` / `client_error` / `failure`), `durationMs`, `mode` (null before mode selection), `queryLength`,
`queryHash` (first 16 hex of SHA-256 of the trimmed query), `embedMs`, `llmMs`, `dbMs`, `inputTokens`, `outputTokens`,
`modelId`, `rowCount`, `truncated`, `sqlHash` (first 16 hex of SHA-256 of the executed SQL), `guardResult` (reject code
or `ACCEPTED`), `errorClass` (Bedrock error class of spec 10 / DB exception class name on 4xx-from-SQL, 429, 5xx).
Never: the token, headers, the query text, the model's answer or the SQL text, row values, the vector.

## Behaviour

1. API Gateway answers the CORS preflight, applies the JWT authorizer, invokes `aws-challenge-chatbot` (payload 2.0,
   integration timeout 29 s).
2. The handler starts the timer; claims/`token_use`/`exp` → 401; `routeKey` ≠ `POST /chat` → 404; `admin` ∉ groups →
   403; body → 400 (in this order; no Bedrock or DB call before a 2xx path is certain).
3. **Vector mode:** strip a leading similarity phrase — regex
   `^\s*(?:which|what|find|show(?:\s+me)?)?\s*(?:users?|people)\s+(?:are\s+|is\s+)?similar\s+to\s*[:\-]?\s*`
   (case-insensitive) — empty remainder → 400; embed the remainder with `embeddings.embed_with_usage` (spec 10 request,
   client and checks); then open the DB connection, `BEGIN READ ONLY`, `SET LOCAL statement_timeout = '4s'`, the vector
   query, `ROLLBACK`.
4. **SQL mode:** one `Converse` call with the prompt of §Inputs; the answer goes through the SQL guard; rejected → 400
   (no DB call); accepted → DB connection, `BEGIN READ ONLY`, `SET LOCAL statement_timeout = '4s'`, the guard's
   rendering, fetch at most 101 rows, `ROLLBACK`.
5. Bedrock is always called **before** the DB connection is opened. Nothing is retried. The connection is closed in
   `finally`; exactly one log line is printed in `finally`; the response is a payload-v2 dict with explicit
   `statusCode`, headers, body.

## Edge Cases / Failure Modes

| Case | Expected result |
|---|---|
| ID token, missing claims, non-admin | 401 / 401 / 403 problem+json; no Bedrock or DB call |
| `{"query": ""}`, `"   "`, 501 characters, `{"query": 5}`, `{"query":"x","mode":"sql"}`, `[]`, invalid JSON, query parameter `?a=1` | 400 |
| "SQL", "Sql:", "my sql question" | `sql` mode (whole word); "mysql", "sqlite" → `vector` mode |
| "which users are similar to" (nothing after) | 400 |
| Model answers `NONE` or prose | 400 `NO_QUERY` / `PARSE_ERROR` |
| Model answers `DELETE FROM users`, `DROP TABLE users`, `SELECT 1; DELETE FROM users`, `SELECT * FROM users`, `SELECT embedding FROM users`, `SELECT * FROM pg_shadow`, `SELECT set_config('role','x',true)`, `SELECT pg_sleep(10)`, `WITH x AS (…) SELECT …`, `SELECT … UNION SELECT …`, `SELECT … FOR UPDATE`, `SELECT … INTO t FROM users`, `SELECT n FROM (SELECT count(*) AS n FROM users) t`, `SELECT current_user`, `SELECT 'users'::regclass FROM users`, `SELECT u.id FROM users u JOIN pg_user p ON true` | 400, matching reject code, no DB call |
| `SELECT country, count(*) AS n FROM users GROUP BY country ORDER BY n DESC` (alias in `ORDER BY`) | accepted |
| Accepted statement fails in PostgreSQL (e.g. type error) or exceeds 4 s | 400 rephrase detail; `errorClass` = DB exception class; transaction rolled back |
| A write slipped through the guard | PostgreSQL rejects it (`READ ONLY` transaction) → 400; nothing changed |
| Statement without `LIMIT` returning 1000 rows | 100 rows, `truncated` true |
| Aggregate with no rows (`count` 0) | 200, one row `[0]` |
| Endpoint absent (between sessions) | 502 within ≈ 2–6 s (`errorClass` `UNREACHABLE`), no DB call |
| Inference-profile permission missing / SCP blocks a destination region | 502 (`AccessDeniedException`) |
| Throttling | 429 |
| Proxy unreachable / IAM auth failure | 500, `errorClass` = cause class |
| Fewer than 5 rows with a vector | `rowCount` < 5 |
| Seeded and real users mixed | both are returned (R-17); seeded rows recognisable by `@seed.invalid` |

## Acceptance Criteria

AC-12.1 … AC-12.3 are verified locally (pytest, zip builds); the rest from owner evidence (console screenshots, the
deployed SPA, DevTools, log events — account id masked, no token values). Agents have no AWS access (CLAUDE.md §3.11).

- [ ] AC-12.1 `pytest` for `lambdas/chatbot` passes and covers: 401/403/404/400 order with no Bedrock/DB call before the
  body is valid; every body edge case of §Edge Cases; mode detection; prefix stripping; vector path (Titan request via
  the shared helper, query text with the vector as a parameter, NULL distances dropped, columns and value mapping); SQL
  path (Converse request: model id, inference config, client config; `NONE`; token usage); `READ ONLY` +
  `statement_timeout` + `ROLLBACK` around every query; row cap and `truncated`; error mapping (Bedrock classes → 429/502,
  SQL errors → 400, DB connect → 500); one log line with the fields of §Outputs and none of the forbidden values
- [ ] AC-12.2 The SQL guard unit tests reject every hostile statement listed in §Edge Cases with the listed code and
  accept at least: `SELECT count(*) FROM users WHERE country IN ('PL','Poland') AND weight_kg > 70 AND date_part('year', age(birthdate)) BETWEEN 25 AND 35`,
  a grouped average, a grouped count ordered by its select-list alias, a gender filter `gender IN ('F','female')`, and
  a row list with `ORDER BY`; `LIMIT` enforcement (none → 101, 500 → 101, 10 → 10); the executed text is the guard's
  rendering (a comment or a second statement in the model answer never reaches the DB)
- [ ] AC-12.3 Shared code: `embeddings.py` and the HTTP helpers live in `lambdas/shared/` only (no copy in a function
  directory); `pytest` for `lambdas/shared`, `lambdas/sync`, `lambdas/admin`, `lambdas/post-confirmation` and
  `lambdas/tests` pass unchanged in count or larger; `package.py` builds `chatbot`, `sync`, `admin` (hashes recorded);
  the chatbot zip contains only pure-Python packages
- [ ] AC-12.4 `aws-challenge-chatbot` runs Python 3.12 with the zip built from Git, timeout 30 s, memory 512 MB, env
  `DB_PROXY_ENDPOINT`/`DB_NAME`/`DB_USER` only; role policies: `rds-db:connect` on the proxy `dbuser` ARN and
  `bedrock:InvokeModel` only on the ARNs of the design §Security (Titan V2 model, the `eu.` inference profile, the
  Nova Micro model in the profile's destination regions with the `bedrock:InferenceProfileArn` condition); log group
  retention 14 days (owner screenshots)
- [ ] AC-12.5 HTTP API: `POST /chat` route with the JWT authorizer, integration `aws-challenge-chatbot`, payload 2.0,
  **timeout 29 s**; still no other route than `GET /admin` and `POST /chat` (owner screenshot) (S3)
- [ ] AC-12.6 Deployed: `POST /chat` without a token → 401; as a non-admin → 403 problem+json; as the admin with
  `{"query":""}` → 400 problem+json (status codes from DevTools or `curl`)
- [ ] AC-12.7 W5-G2: as the admin, `which users are similar to <profile text of seeded user k in the spec 10
  template>` → 200 `mode` `vector`, 5 rows, the first is user k with `distance` < 0.01, and the set of the 5 ids equals
  the `items` of `{"action":"similar","userId":"<id of user k>"}` on the sync Test tab (spec 11)
- [ ] AC-12.8 W5-G1: five consecutive vector-mode searches in the deployed SPA (warm, after one discarded first
  request): median request time in DevTools < 1000 ms, and the log lines show `totalMs`/`durationMs`, `embedMs`, `dbMs`;
  cold-start time of the discarded request recorded separately
- [ ] AC-12.9 SQL mode: `sql how many users aged 25 to 35 live in Poland and weigh more than 70 kg` → 200 `mode` `sql`,
  one row with a count; the returned `sql` is one `SELECT` on `users` filtering age 25–35 from `birthdate`, Poland (name
  and/or `PL`) and `weight_kg > 70`; latency (`timings`) and tokens recorded — no < 1 s target for this path (design §6)
- [ ] AC-12.10 Safety on AWS: `sql delete all users` and `sql drop the users table` → 400 (or 200 with a harmless
  `SELECT`), and the `GET /admin` `total` is unchanged afterwards
- [ ] AC-12.11 The log lines of AC-12.7 … AC-12.10 each have one JSON line with `mode`, `embedMs`/`llmMs`, `dbMs`,
  `inputTokens`, `outputTokens`, `queryLength`, `queryHash`, `apiRequestId`, `userSub`; none contains the query text,
  the SQL text, a row value or a token (owner screenshot) (S4)
- [ ] AC-12.12 With the endpoint absent: a vector-mode request → 502 problem+json within 10 s (DevTools), log
  `errorClass` `UNREACHABLE`, no DB call (`dbMs` null)
