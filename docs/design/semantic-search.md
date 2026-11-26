# Design — Semantic search form: `POST /chat` in the Chatbot Lambda (NL → SQL / vector), admin AI page

Status: **Accepted** (owner, 2026-11-25; drafted by the architect 2026-11-25). Owner decisions:
[Q-21](../RISKS.md#q-21) A — direct `Converse` from `chatbot`, no Bedrock Agent (ADR-021);
[Q-22](../RISKS.md#q-22) — Amazon Nova Micro via `eu.amazon.nova-micro-v1:0` (ADR-022);
[Q-23](../RISKS.md#q-23) A — master DB user + SQL guard + read-only transaction, R-19 accepted. The recommended options
written into the Proposed Solution are the decided ones.
Requirements: [week-05](../requirements/week-05-semantic-search.md) W5-G1, W5-G2, S1…S4, project requirement ·
Specs: [12-chat-api](../specs/12-chat-api.md), [13-chat-page](../specs/13-chat-page.md)
Architecture: [ARCHITECTURE.md](../ARCHITECTURE.md) §2, §3.2, §3.3, §3.6, §5.3, §6, ADR-004, ADR-015, ADR-018,
ADR-019, ADR-020, ADR-021, ADR-022, goals G4–G8
Related design: [vectorisation](vectorisation.md) (Titan V2, on-demand endpoint, `<->` query),
[admin-api](admin-api.md) (claims, group check, problem+json, admin page), [user-sync](user-sync.md) (DB access)

## Problem Statement

Week 5 asks for a search component in the SPA that sends a natural-language query to the Chatbot Lambda, which turns
it into SQL or a vector search "through a Bedrock Agent" and returns rows (task); if the query contains the keyword
"sql", Bedrock LLM → SQL, otherwise a Bedrock embedding + pgvector similarity search (S2); a form with a debounced
request and a results table (S1); API Gateway 29 s / Lambda 30 s timeouts (S3); latency and token logging (S4); goals
"relevant rows in < 1 s" (W5-G1) and "which users are similar to …" returns the correct TOP-5 (W5-G2). The project
page adds: only the **administrator** uses this page, for statistics such as "how many users aged 25 to 35 live in
Poland and weigh more than 70 kg". Facts that shape the design:

1. **Agent vs S2.** The task line says "through a Bedrock Agent"; step S2 says "Bedrock LLM → SQL". A Bedrock Agent is a
   managed orchestrator (agent + action group + alias + service role) reached through a second runtime service,
   `bedrock-agent-runtime`; every agent turn runs several model calls (orchestration, tool call, final answer). →
   [Q-21](../RISKS.md#q-21).
2. **Model.** The materials name Claude 3 Sonnet. It is not usable from eu-west-1: the AWS model-lifecycle page
   (checked 2026-11-25) lists Claude 3 Haiku as **EOL in eu-west-1 since 2026-09-10** and has no active eu-west-1 entry
   for Claude 3 Sonnet (Legacy/EOL in the other listed regions); Claude Sonnet 4.5 is Legacy (EOL 2027-04-08). Current
   Anthropic models need a one-time use-case form and are billed through AWS Marketplace. Amazon Nova Micro is offered
   from eu-west-1 **only through the EU geo cross-region inference profile** `eu.amazon.nova-micro-v1:0` (model card,
   2026-11-25: no in-region option in eu-west-1). The owner confirms the model state in the console (T05-01). →
   [Q-22](../RISKS.md#q-22).
3. **Network.** `aws-challenge-chatbot` runs in the private subnets without egress ([R-09](../RISKS.md#2-risk-register));
   the only path to Bedrock is the `bedrock-runtime` interface endpoint that exists only during working sessions
   (ADR-020, [R-18](../RISKS.md#2-risk-register)). Both paths (embedding and LLM) need it.
4. **LLM-generated SQL is untrusted code** that runs against the database as the proxy's only DB user, the master
   `postgres` ([R-16](../RISKS.md#2-risk-register)). → [Q-23](../RISKS.md#q-23), [R-19](../RISKS.md#2-risk-register).
5. **Latency.** < 1 s is realistic for the vector path (one Titan call ≈ 0.1–0.3 s + one proxy connection + an HNSW
   query ≈ 0.5 ms, measured in Week 4), **not** for the LLM path (one model call alone is typically 0.5–3 s).
6. **Keyword vs project example.** The project's example question contains no "sql", so by S2 it would go to the
   similarity search. The page therefore tells the admin to start statistics questions with "sql".
7. **Data.** Real users and the 1000 seeded users use different value forms: `country` is an ISO alpha-2 code for
   real users (spec 04) but an English name for seeded users (spec 11); `gender` is `F`/`M` for real users (spec 04,
   stored as given — spec 07) but `female`/`male` for seeded users. The LLM prompt must cover both forms.
8. **Code.** `lambdas/chatbot/` is empty (the Week 1 placeholder lives only in the console, R-15). The Titan client and
   text template are in `lambdas/sync/embeddings.py`; claims, group parsing and problem+json are in
   `lambdas/admin/lambda_function.py` — both must be reused, not copied.

## Proposed Solution

```mermaid
sequenceDiagram
    participant B as SPA /chat (admin)
    participant G as HTTP API aws-challenge-api<br/>JWT authorizer, integration timeout 29 s
    participant C as Lambda chatbot (VPC, 30 s)
    participant E as bedrock-runtime endpoint<br/>(on demand, ADR-020)
    participant P as RDS Proxy → PostgreSQL
    B->>G: POST /chat {"query": "..."} (Bearer access token)
    G->>C: payload 2.0 + jwt claims
    C->>C: token_use = access? group admin? body valid?
    alt query contains the keyword "sql"
        C->>E: Converse (Nova Micro via EU inference profile) → one SELECT
        C->>C: SQL guard (parse, allowlists, LIMIT)
        C->>P: BEGIN READ ONLY; SET LOCAL statement_timeout; SELECT …; ROLLBACK
    else otherwise
        C->>E: InvokeModel Titan V2 (query text) → vector(1024)
        C->>P: BEGIN READ ONLY; … ORDER BY embedding <-> $1 LIMIT 5; ROLLBACK
    end
    C-->>B: 200 {mode, columns, rows, sql, timings, tokens} | problem+json
```

### 1. Bedrock Agent vs direct model call *(decided: Q-21 A — ADR-021 Accepted)*

`chatbot` calls the model **directly** with the `bedrock-runtime` **Converse** API: one request per question, system
prompt = schema + rules, temperature 0, `maxTokens` 300. This matches S2 ("Bedrock LLM → SQL") literally and reuses the
endpoint of ADR-020. **Deviation from the task line** ("through a Bedrock Agent"), recorded in ARCHITECTURE §2: no agent,
no action group, no agent alias, no `bedrock-agent-runtime` endpoint. Reasons: fewer console resources (no agent, alias,
agent service role, second endpoint), one model call instead of an orchestration loop (lower latency and tokens),
deterministic control of the SQL in code, no agent model restrictions. Options in §Alternatives and Q-21.

### 2. LLM model *(decided: Q-22 Amazon Nova Micro — ADR-022 Accepted)*

| Setting | Value |
|---|---|
| Model | Amazon Nova Micro, text-only, called from eu-west-1 through the **EU geo cross-region inference profile** `eu.amazon.nova-micro-v1:0` (code constant; the owner confirms the exact id in the console, T05-01). Destinations when the source is eu-west-1: eu-central-1, eu-north-1, eu-west-1, eu-west-3 (model card, 2026-11-25) |
| API | `bedrock-runtime` `Converse`, `inferenceConfig` `{"maxTokens": 300, "temperature": 0}`; `usage.inputTokens` / `usage.outputTokens` logged (S4) |
| Output contract | exactly one PostgreSQL `SELECT` statement, or the word `NONE` when the question cannot be answered from the table |
| Fallback | Nova Lite (`eu.amazon.nova-lite-v1:0`) if Nova Micro's SQL is not good enough in T05-03 — code constant + IAM ARNs only, no design change |

Cross-region inference is routed by Bedrock behind the regional `bedrock-runtime` endpoint: the Lambda talks only to
eu-west-1 through the interface endpoint; no NAT, no cross-region network path in the VPC (§3).

### 3. Network (ADR-020 unchanged — confirmed)

The chatbot uses the same subnets and security groups as `sync`, so the same on-demand interface endpoint
`aws-challenge-vpce-bedrock-runtime` (private DNS; SG `aws-challenge-vpce-sg` admits 443 from the Lambda default SG)
serves both the Titan `InvokeModel` and the Nova `Converse` call; the boto3 default endpoint resolves to it. No new
endpoint, SG or route. While the endpoint is absent every `POST /chat` ends with **502 within a few seconds** (2 s
connect timeout, one attempt) — expected between sessions (R-18).

### 4. Request handling in `aws-challenge-chatbot` (`lambdas/chatbot/`)

Order (same as `admin`): claims present and `token_use == "access"` (401) → route `POST /chat` (404) → `admin` in
`cognito:groups` (403, no Bedrock or DB call) → body (400) → mode → Bedrock → DB → 200. Field-level contract, errors and
log line: [spec 12](../specs/12-chat-api.md).

- **Body:** JSON object with exactly one field `query` (string, 1…500 characters after trimming); unknown fields → 400.
- **Mode (S2):** `sql` if the query contains the word `sql` (case-insensitive, whole word), else `vector`.
- **Vector path:** a leading "which users are similar to" phrase is stripped (spec 12 §Behaviour) and the rest is
  embedded with the shared Titan helper (same model, 1024 dims, normalised, same fail-fast client); then the curriculum
  query `ORDER BY embedding <-> CAST(:q AS vector) LIMIT 5` returns the five nearest users with their profile columns
  and the distance (never the vector). A query written in the profile template of spec 10 (e.g. `gender: female; birth
  year: 1990; country: Poland; height: 170 cm; weight: 60 kg`) yields the same vector as the stored profile, so the
  matching user comes first with distance ≈ 0 — this is how W5-G2 "correct TOP-5" is judged: the TOP-5 equals the
  `similar` action's TOP-5 for that user (spec 11).
- **SQL path:** Converse with the prompt of spec 12 (schema without `embedding`, value conventions incl. country code
  *or* English name, age from `birthdate`, rules) → **SQL guard** (§5) → execution → rows.
- **Response:** one shape for both modes — `mode`, `columns`, `rows` (arrays of JSON scalars), `rowCount`, `truncated`,
  `sql` (the executed statement, SQL mode only), `timings` (`embedMs`, `llmMs`, `dbMs`, `totalMs`), `tokens`
  (`input`, `output`), `modelId`. The admin sees the generated SQL (transparency; it is logged only as a hash).
- **Errors:** problem+json; guard rejection, model answer `NONE`, invalid SQL or statement timeout → 400 with a fixed
  "rephrase" detail; Bedrock throttling → 429; other Bedrock failure (endpoint absent, access denied, timeout) → 502;
  DB connection or unexpected error → 500.

### 5. SQL safety (critical) *(decided: Q-23 A; R-19 accepted)*

LLM output is treated as untrusted code. Layers, all in code or per-transaction settings (no console work):

1. **Parse, don't regex:** the statement is parsed with `sqlglot` (PostgreSQL dialect; pure-Python wheel, pinned in
   `lambdas/chatbot/requirements.txt`). Rejected unless: exactly **one** statement; the root is a plain `SELECT` (no
   `WITH`, `UNION`/`INTERSECT`/`EXCEPT`, `SELECT … INTO`, `FOR UPDATE/SHARE`); every table reference (also in
   subqueries) is `users`; every column is in the allowlist (all columns of spec 06 **except `embedding`**); `*` only
   inside `count(*)`; every function is in the allowlist of spec 12 (aggregates, rounding, string case, `age`,
   `date_part`/`extract`, `coalesce` …; e.g. `set_config`, `pg_sleep`, `pg_read_file`, `dblink`, `lo_*` are rejected);
   `FROM` is exactly `users` (optionally aliased; no derived table, join to another table, `VALUES` or table function);
   scalar subqueries in `WHERE`/`SELECT` follow the same rules; a name in `ORDER BY`/`GROUP BY`/`HAVING` may also be an
   alias defined in the select list; `CAST` only to plain types (numbers, text, date, timestamp, interval, boolean —
   no `regclass`/`regproc`-style catalog types); at most 2000 characters.
2. **Bounded result:** the guard sets `LIMIT 101` when the statement has no `LIMIT` or one above 100; at most 100 rows
   are returned, `truncated` = a 101st row existed. The **executed text is the guard's re-rendered AST**, so what runs is
   exactly what was validated.
3. **Database-enforced read-only and time bound:** `BEGIN READ ONLY` → `SET LOCAL statement_timeout = '4s'` → the
   statement → `ROLLBACK` (always). A write, DDL or `nextval` fails in PostgreSQL even if the guard missed it.
4. **Least data in the prompt:** the model sees the schema and the question, never rows.
5. **Who:** only members of the group `admin` (who already see every user in `GET /admin`), so the confidentiality
   impact of a guard gap is bounded; the integrity impact is blocked by layers 1 and 3.

Remaining risk: the DB user is still the master (R-16) — a guard bypass combined with a PostgreSQL feature that writes
despite `READ ONLY` (e.g. an unsafe function) is theoretically possible; per-function DB roles stay a later task
(Q-23 options B/C; R-19).

### 6. Timeouts (S3)

| Layer | Value | Why |
|---|---|---|
| HTTP API integration of `POST /chat` | **29 s** (S3; HTTP API maximum 30 s) | curriculum |
| `aws-challenge-chatbot` timeout | **30 s** (S3) | curriculum |
| Titan embedding (shared client) | connect 2 s, read 5 s, 1 attempt (spec 10, unchanged) | fail fast without the endpoint |
| Converse client | connect 2 s, read 10 s, 1 attempt | an LLM answer of ≤ 300 tokens takes ≈ 1–3 s; no retry storms |
| DB socket (connect and each read) | 5 s | proxy connect is sub-second when healthy |
| `statement_timeout` | 4 s (both paths) | generated SQL on ~1000 rows needs milliseconds |

Worst case: SQL path 2 + 10 + 5 + 5 ≈ 22 s, vector path 2 + 5 + 5 + 5 ≈ 17 s, plus a cold start (VPC Lambda, `sqlglot`
import, ≈ 1–3 s) — below the 29 s integration timeout, so API Gateway never cuts off a running request. Memory **512 MB** (faster CPU for the cold start with `sqlglot`;
cost ≈ $0 at learning volume).

**Latency targets (honest):** W5-G1 "< 1 s" is defined for the **vector path, warm** (spec 12 AC-12.8: median of five
consecutive searches in the deployed SPA). The SQL path is expected at ≈ 1–4 s (one LLM call) and gets no < 1 s
target — recorded as a deviation in ARCHITECTURE §2. Cold starts (first request after idle, VPC Lambda + imports) are
excluded and reported separately.

### 7. Logging (S4)

One JSON line per request (log group `/aws/lambda/aws-challenge-chatbot`, retention 14 days): correlation
(`awsRequestId`, `apiRequestId`, `userSub`), `route`, `status`, `outcome`, `durationMs`, `mode`, `queryLength`,
`queryHash`, `embedMs`, `llmMs`, `dbMs`, `inputTokens`, `outputTokens`, `modelId`, `rowCount`, `truncated`, `sqlHash`,
`guardResult`, `errorClass`. **Never** the query text, the generated SQL text, row values, the vector or the token
(CLAUDE.md §7: length/hash only). Hash = first 16 hex characters of SHA-256.

### 8. SPA `/chat` (S1)

Admin-only page (Chat link shown only to the group `admin`, like Admin; non-admins see "You do not have access to this
page." without a request; the API enforces). One text field (max 500) with **Search** button and a hint with both
example forms. **Debounce rule (cheap and literal):** typing triggers an automatic request **800 ms** after the last
keystroke only when the trimmed query has ≥ 3 characters **and no keyword "sql"** (a Titan call costs ≈ $0.000001);
a query with "sql" runs **only on Enter / Search**, so half-typed sentences never reach the LLM. Results: one generic
table rendering `columns` × `rows`, a meta line (mode, rows, `totalMs`), the executed SQL in SQL mode, "first 100 rows"
when truncated; loading / 400 / 403 / 429 / 502 ("AI service not available — switched on only during working
sessions") / error states. No retry of `POST /chat`. UI contract: [spec 13](../specs/13-chat-page.md).

### 9. Code reuse

- `lambdas/sync/embeddings.py` → **`lambdas/shared/embeddings.py`** (the packager already copies `shared/*.py` to each
  zip root, so `import embeddings` keeps working in `sync`); gains `embed_with_usage(text)` → `(vector, inputTokens)`
  for S4; `embed()` keeps its behaviour. The `StubBedrock` test double moves to `lambdas/shared/tests/` (the `sync`
  and `chatbot` test `conftest.py` add that directory to `sys.path`; it is never packaged).
- Claims, `token_use`/`exp` check, `parse_groups` and the problem+json / JSON response helpers move from
  `lambdas/admin/lambda_function.py` to **`lambdas/shared/http_api.py`**; `admin` imports them unchanged in behaviour
  (spec 08 tests stay green).
- Consequence: the `sync` and `admin` zips change (moved modules), so the T05-03 session re-uploads them with the new
  `chatbot` zip (Git = deployed, CLAUDE.md §7). The `post-confirmation` zip would only gain unused modules; it is not
  re-uploaded.

## Alternatives Considered

| Topic | Option | Pros | Cons | Verdict |
|---|---|---|---|---|
| Orchestration (Q-21) | A: direct `Converse` from `chatbot` | matches S2 literally; one model call (≈ 1–3 s); same endpoint as ADR-020; SQL fully controlled in code; no new AWS resource | deviates from the task line "through a Bedrock Agent" | **chosen** (owner 2026-11-25) |
| Orchestration (Q-21) | B: Bedrock Agent + action group Lambda executing the SQL | the task line literally; "agent" experience | agent, alias, agent service role, action group schema, Lambda permission for the agent; `chatbot` becomes both caller and action handler; second on-demand endpoint `bedrock-agent-runtime` (≈ $0.011/h per session); orchestration = several model calls per question (≈ 3–10 s, 3–5× tokens); generated SQL still needs the same guard | alternative |
| Orchestration (Q-21) | C: Bedrock Agent with *return of control* (no action-group Lambda) | agent in the loop, chatbot keeps execution | same console set-up and second endpoint as B; still several model calls; more complex response parsing | alternative |
| Orchestration | Bedrock Knowledge Base structured-data (text-to-SQL) | managed NL→SQL | supports Amazon Redshift only, not PostgreSQL | impossible |
| Model (Q-22) | Nova Micro via `eu.` profile | cheapest text model (US list price $0.035 / $0.14 per 1 M input/output tokens; EU slightly higher — re-check); fast; Amazon model, no Marketplace, no form | weakest reasoning; cross-region only (destination regions in IAM) | **chosen** (owner 2026-11-25) |
| Model (Q-22) | Nova Lite via `eu.` profile | still cheap (≈ 2× Micro); better instruction following | cross-region only | fallback (code constant + IAM ARNs only) |
| Model (Q-22) | Claude Haiku 4.5 via `eu.` profile | strong SQL | ≈ 25–35× Nova Micro ($1 / $5 per 1 M in the US, re-check); Marketplace billing; one-time Anthropic use-case form; more console work | alternative |
| Model | Claude 3 Sonnet / Claude 3 Haiku (materials) | named by the materials | Claude 3 Haiku EOL in eu-west-1 (2026-09-10); Claude 3 Sonnet no active eu-west-1 offering (lifecycle page, 2026-11-25) | impossible |
| Model | Claude Sonnet 4.x via `eu.` profile | best quality | ≈ 100× Nova Micro; Marketplace + form; Sonnet 4.5 already Legacy | rejected (cost) |
| SQL privileges (Q-23) | A: master user + guard + `READ ONLY` tx + `statement_timeout` (R-16 extended) | $0, no console work, layered | DB user can write in principle; relies on guard + PostgreSQL read-only | **chosen** (owner 2026-11-25) |
| SQL privileges (Q-23) | B: A + migration V3 with a `NOLOGIN` role `chat_reader` (SELECT on `users` only), `SET LOCAL ROLE chat_reader` in the transaction | DB-enforced table/column privileges | sync zip + migrate run; `SET ROLE` can be undone by SQL the guard must still block; small gain over A | alternative |
| SQL privileges (Q-23) | C: separate login DB user for `chatbot` (own Secrets Manager secret registered in RDS Proxy, own `rds-db:connect` ARN) | real least privilege | most console work (secret, proxy auth, proxy role, password set by hand), secret cost ≈ $0.40/month | deferred |
| SQL validation | parse with `sqlglot` + allowlists | robust to comments, quoting, nesting | one new pure-Python dependency | **chosen** |
| SQL validation | regex / keyword blacklist | no dependency | bypassable (comments, casing, functions) | rejected |
| SQL validation | only `READ ONLY` transaction | simplest | functions with side effects, unbounded reads, other tables | rejected (insufficient alone) |
| Network | same on-demand `bedrock-runtime` endpoint (ADR-020) | $0 extra; already proven | chat works only during sessions (R-18) | **chosen** |
| Network | endpoint always on | chat always available | ≈ $8/month | rejected (cost) |
| Auto-request | debounce 800 ms only without "sql"; "sql" on Enter/Search | literal S1; no LLM calls for partial text | two behaviours to explain (hint text) | **chosen** |
| Auto-request | debounce for every query | simplest | LLM calls (and junk SQL) on half-typed sentences | rejected |
| Auto-request | explicit submit only | cheapest | not "debounced" (S1) | rejected |
| Access | admin only (group check in the handler) | project requirement; same pattern as `GET /admin` | — | **chosen** |
| Response | one shape (`columns` + `rows`) for both modes | one table component; arbitrary SQL columns | column labels in SQL mode are whatever the query names them | **chosen** |
| Code reuse | move `embeddings.py` and the HTTP helpers to `lambdas/shared/` | no duplication | `sync` and `admin` re-uploaded once | **chosen** |
| Code reuse | copy into `chatbot` | no re-upload | duplication bug (CLAUDE.md §7) | rejected |

## API Design

Conventions: CLAUDE.md §6 (ADR-018: route of the curriculum diagram, no new route). Field-level contract (single home):
[spec 12](../specs/12-chat-api.md) §Inputs/§Outputs.

| Method | Path | Auth | Body | 200 response | Errors |
|---|---|---|---|---|---|
| POST | `/chat` | JWT (access token) + group `admin` | `{ "query": string (1..500) }`, no other field | `{ mode: "sql"\|"vector", columns: string[], rows: scalar[][], rowCount, truncated, sql: string\|null, timings: {embedMs, llmMs, dbMs, totalMs}, tokens: {input, output}, modelId }` | 400, 401, 403, 404, 429, 500, 502 |

No pagination (bounded: 5 rows vector, ≤ 100 rows SQL). No data is created or updated.

## Affected Components

- **Tasks:** T05-01 (devops, console set-up), T05-02 (backend, `chatbot` code + shared modules), T05-03 (devops,
  endpoint session: uploads and checks), T05-04 (frontend, `/chat` page), T05-05 (tester, acceptance) —
  [PLAN.md](../PLAN.md).
- **AWS (owner, runbooks):** T05-01 — model check (Nova Micro EU profile; access), `aws-challenge-chatbot` role inline
  policies (`bedrock:InvokeModel` on Titan + profile + destination foundation models; `rds-db:connect`), function
  configuration (timeout 30 s, memory 512 MB, env `DB_PROXY_ENDPOINT`/`DB_NAME`/`DB_USER`, Python 3.12), log retention 14
  days, `POST /chat` integration timeout 29 s. T05-03 — endpoint session: upload `chatbot`, `sync`, `admin` zips,
  checks, endpoint deleted. No new resource.
- **Repository:** `lambdas/chatbot/` (handler, LLM client and prompt, SQL guard, vector search, tests,
  `requirements.txt` with `sqlglot`), `lambdas/shared/embeddings.py`, `lambdas/shared/http_api.py`, `lambdas/admin`
  and `lambdas/sync` imports; `frontend/src` chat page, client, view logic, header link.
- **Skills (ownership rule):** new `chatbot-api` (handler, prompt, guard, modes, log line, tests); updates
  `bedrock-embeddings` (shared module, chatbot use, inference-profile IAM), `python-lambda` (layout, shared modules),
  `admin-api` (helpers moved), `http-api-jwt` (integration timeout), `spa-api-client` (`POST /chat`).
- **Docs:** ARCHITECTURE §2, §3.2, §3.3, §3.6, §5.3, §6, §10, ADR-021/022; ENVIRONMENT.md (chatbot settings, role
  policies, model id, integration timeout); notes in spec 04 (Behaviour 7/9) and spec 09 (Header): the Chat link and
  `/chat` become admin-only and `/chat` calls the API (spec 13).

## Security Considerations

- **AuthN/AuthZ:** JWT authorizer at the edge (unchanged); the handler rejects ID tokens (`token_use`) and non-admins
  (403) before any Bedrock or DB call. Claims only from `requestContext.authorizer.jwt.claims`.
- **LLM SQL:** §5 layers; the guard is unit-tested against a fixed list of hostile statements (spec 12 AC-12.2).
- **Prompt injection:** the admin can steer the model, but the model's only output channel is a SQL text that passes the
  guard; the model never sees row data, credentials or other tables.
- **IAM least privilege (chatbot role):** `rds-db:connect` on the proxy `dbuser` ARN (as `sync`); `bedrock:InvokeModel`
  (also required for `Converse`) only on: the Titan V2 foundation-model ARN in eu-west-1; the inference profile
  `arn:aws:bedrock:eu-west-1:<account-id>:inference-profile/eu.amazon.nova-micro-v1:0`; and the foundation model
  `amazon.nova-micro-v1:0` in **each destination region** of that profile (eu-central-1, eu-north-1, eu-west-1,
  eu-west-3), restricted with the condition `bedrock:InferenceProfileArn` = that profile ARN so the foundation models are
  usable only through the profile. A corporate SCP that denies Bedrock in one of the destination regions makes calls
  fail ([R-20](../RISKS.md#2-risk-register)); no `bedrock:*`, no `aws-marketplace:*` (Amazon model). No
  `bedrock:InvokeAgent` (Q-21 A).
- **No public exposure:** no new endpoint, route or security-group rule; Bedrock only through the private interface
  endpoint.
- **Data protection:** the question text goes to Bedrock (EU geography only via the `eu.` profile); Bedrock does not
  store prompts or use them for training (AWS Bedrock data protection; re-check wording). Logs: length and hash only.
- **Responses:** `Cache-Control: no-store`; personal data (names, e-mail) only to admins, as in `GET /admin`.
- **Abuse/cost:** no stage throttling until Week 6 (ADR-018); every call needs an admin token; one LLM call ≤ 300 output
  tokens; no retries; AWS Budgets alert (T00-01).

## Cost

eu-west-1; re-check on the AWS pricing pages before executing. **No new always-on resource.**

| Item | Cost |
|---|---|
| `bedrock-runtime` endpoint (existing, on demand, ADR-020) | ≈ $0.011/h per session — unchanged |
| Nova Micro (EU profile; billed at the source-region price): ≈ 700 input + 100 output tokens per SQL question | ≈ $0.00004 per question; 1 000 questions ≈ $0.04–0.05 |
| Titan V2 query embedding: ≈ 20 tokens | ≈ $0.0000004 per question |
| Lambda 512 MB, ≈ 1–3 s per request; CloudWatch Logs | ≈ $0 at learning volume |
| Rejected: endpoint always on | ≈ $8/month |
| Q-21 B/C: second endpoint `bedrock-agent-runtime` | + ≈ $0.011/h per session; agent itself no fee, 3–5× tokens |
| Q-22 Claude Haiku 4.5 instead of Nova Micro | ≈ $0.0013 per question (≈ $1.3 per 1 000) |
| Q-23 C: one more Secrets Manager secret | ≈ $0.40/month |

## Open Questions

None open. Answered by the owner on 2026-11-25:

| ID | Question | Decision |
|---|---|---|
| [Q-21](../RISKS.md#q-21) | Bedrock Agent (task line) or direct model call (S2)? | A — direct `Converse`; deviation recorded (ADR-021 Accepted) |
| [Q-22](../RISKS.md#q-22) | Which LLM for NL → SQL in eu-west-1? | Amazon Nova Micro via `eu.amazon.nova-micro-v1:0`; Nova Lite as fallback (ADR-022 Accepted) |
| [Q-23](../RISKS.md#q-23) | DB privileges for LLM-generated SQL | A — master user + guard + `READ ONLY` + `statement_timeout`; R-16 extended, R-19 accepted |

Not blocking, decided here (owner may override on acceptance): the keyword rule is literal (whole word "sql",
case-insensitive) and the page explains it; vector results are 5 users with profile columns; the generated SQL is shown
to the admin; the SQL path has no < 1 s target. To re-check during the tasks: exact inference-profile id and destination
regions in the owner's console (T05-01); EU token prices; whether Converse through the interface endpoint reaches the
`eu.` profile without extra settings (T05-03, first call).
