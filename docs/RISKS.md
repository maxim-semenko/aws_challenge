# RISKS.md — Open Decisions and Risk Register

Related: [ARCHITECTURE.md](ARCHITECTURE.md) · [PLAN.md](PLAN.md) · [design/](design/) · [tasks/](tasks/)
Last updated: 2026-11-12

This file has two registers:

1. **Open decisions (`Q-xx`)** — questions that must be answered before some work can start. They **block** tasks.
2. **Risks (`R-xx`)** — things that may go wrong. They do not block tasks by themselves; they carry a mitigation
   and are watched by the tasks listed against them.

## Blocking rules

- A task that lists an **Open** `Q-xx` (or an `R-xx` escalated to *Blocking*) in its `blocked_by` field has status
  **Blocked**. No design detail, code or infrastructure is produced for it until the item is resolved.
- Resolving an item = recording the decision (or the accepted risk) in this file with date and owner, then
  updating every affected task: `Blocked` → `Todo`, scope adjusted to the decision, `Blocked by` cleared.
- New blockers discovered during work are added here first, then referenced from the task. A task is never
  silently paused.
- A risk is escalated to *Blocking* when its trigger occurs and no mitigation is in place.

---

## 1. Open decisions

| ID | Decision needed | Recommendation | Owner | Status | Blocks |
|---|---|---|---|---|---|
| [Q-02](#q-02) | Infrastructure-as-Code tool for the later IaC task | AWS CDK in Python | OWNER + ARCH | Open (deferred by Q-12 C) | T00-03 |
| [Q-05](#q-05) | Chatbot data: what the search runs over | users table per the Week 4 curriculum | OWNER | Deferred (Week 4) | — |
| [Q-14](#q-14) | Registration fields: Cognito attribute schema and validation rules (immutable once the pool exists) | table in Q-14, option A | OWNER | Open | T02-01, T02-04 |
| [Q-15](#q-15) | Vector dimension and model: 1536 (Week 4 curriculum) vs 1024 (ADR-007) | decide when Week 4 is planned | OWNER + ARCH | Open (Week 4, not blocking now) | — |
| [Q-16](#q-16) | Database migrations without Java/Flyway-in-Lambda | A — versioned SQL files + small Python runner | OWNER + ARCH | Open (Week 3, not blocking now) | — |

### <a id="q-02"></a>Q-02 — IaC tool

Deferred by Q-12 (option C): Week 1 and Week 2 resources are created manually / with recorded AWS CLI commands; a
dedicated task (T00-03) codifies them later. The tool should import existing resources (the Cognito pool cannot be
recreated without losing users).

| Option | Pros | Cons |
|---|---|---|
| **AWS CDK, Python (recommended)** | same language as the Lambdas (ADR-015); good L2 constructs (HTTP API, Cognito, RDS Proxy); `cdk import` / `cdk migrate --from-scan` for existing resources; cdk-nag | needs the CDK CLI (Node) and `cdk bootstrap` |
| AWS CDK, TypeScript | same language as the SPA; CDK's primary language | IaC and Lambdas in different languages and toolchains |
| Terraform | industry standard, `import` blocks | second configuration language (HCL), more boilerplate |
| AWS SAM | simple for Lambda | weak for VPC/RDS/Proxy and Cognito details |

### <a id="q-05"></a>Q-05 — Chatbot data

Originally: which documents the chatbot searches. The Week 4 curriculum stores embeddings in `users.embedding` and
Week 5 asks for "users similar to …", so the search most likely runs over users. Confirm or reopen when Week 4 is
planned (the ≥ 1000-record latency check needs a test dataset of users).

### <a id="q-14"></a>Q-14 — Registration fields: Cognito schema and validation

Raised 2026-11-12, still open (the owner has not answered the ranges). The requirements list eight sign-up fields but
no ranges. In Cognito the **sign-in attribute, the set of required standard attributes and every custom attribute
(name, type, min/max) cannot be changed after the User Pool is created** — a wrong choice means a new pool and losing
all users. Custom attributes can never be marked *required*, and Cognito does not validate the value of standard
attributes such as `gender`.

Recommended schema and rules (option A):

| Field (UI) | Cognito attribute | Type / constraint in Cognito | Validation (SPA) |
|---|---|---|---|
| First name | `given_name` (standard, required) | string | trimmed, 1..50 characters, letters, space, `-`, `'` |
| Last name | `family_name` (standard, required) | string | same as first name |
| Email | `email` (standard, required, sign-in attribute, auto-verified) | string | e-mail syntax, ≤ 254 characters |
| Gender | `gender` (standard, required) | string, not validated by Cognito | exactly `F` or `M` |
| Date of birth | `birthdate` (standard, required) | string `YYYY-MM-DD` (OIDC) | input `DD/MM/YYYY`, real calendar date, between 1900-01-01 and today minus 13 years |
| Country of living | `custom:country` | String, min 2, max 2 | ISO 3166-1 alpha-2 code chosen from a list (names rendered with `Intl.DisplayNames`) |
| Height, cm | `custom:height` | Number, min 50, max 250 | integer 50..250 |
| Weight, kg | `custom:weight` | Number, min 20, max 300 | integer 20..300 |

| Option | Server-side enforcement | Pros | Cons |
|---|---|---|---|
| **A (recommended)** | SPA validation + the Cognito constraints above | simple; Cognito rejects out-of-range custom values | a direct call to the Cognito `SignUp` API can bypass the `gender`/`birthdate` rules and omit custom attributes; the Week 3 sync must tolerate such values |
| B | A + a PreSignUp Lambda trigger that validates all fields before the account is created | true server-side validation, clean rejection | one more synchronous trigger (5 s limit), extra function, beyond the week topic |
| C | SPA validation only; custom attributes without min/max in Cognito | ranges can change later without a new pool | no server-side bound at all |

The owner confirms or changes every range (in particular the minimum age and the integer-only height and weight) and
the option before T02-01 creates the pool.

### <a id="q-15"></a>Q-15 — Vector dimension and embedding model (Week 4)

Raised 2026-11-12 from the Week 4 curriculum: "1536-dimensional vectors", `ORDER BY embedding <-> $1` (L2 distance),
"Bedrock Titan Embeddings (or Claude 3.5 Sonnet)". ADR-007 (Proposed) has Titan Text Embeddings v2, 1024 dimensions,
cosine distance. Facts to verify when Week 4 is planned: Titan Text Embeddings v2 outputs 256/512/1024 dimensions;
1536 is the fixed output of the older Titan Embeddings G1 – Text (v1); Claude models do not produce embeddings.
Options: (a) follow the curriculum — Titan G1 Text, `vector(1536)`, `<->`; (b) keep ADR-007 — Titan v2, 1024, cosine,
deviation noted; (c) Titan v2 1024 with `<->` on normalised vectors (same ranking as cosine). Model availability per
region: [R-05](#2-risk-register). Not blocking until Week 4.

### <a id="q-16"></a>Q-16 — Database migrations (Week 3)

Raised 2026-11-12: ADR-008 (Flyway in a Java `migrate` function) no longer fits ADR-015. The database is private
(reachable only from the VPC through the proxy). Not blocking until the first schema (Week 3).

| Option | Meaning | Pros | Cons |
|---|---|---|---|
| **A (recommended)** | Plain versioned SQL files `V<n>__<description>.sql` in the repository, applied by a small Python runner in a `migrate` Lambda (records applied versions in a `schema_migrations` table, one transaction per file, advisory lock) | no new tool; same naming as Flyway, so Flyway can take over later; runs inside the VPC | ~50 lines of own code to test; a fourth function |
| B | Flyway CLI run from AWS CloudShell in a VPC environment (or a temporary SSM bastion) | the standard tool, checksums, repair | Java/Flyway download per session; manual step outside the repo's code |
| C | Alembic (SQLAlchemy) in a `migrate` Lambda | mature Python tool, down-migrations | SQLAlchemy dependency for a few tables; heavier zip |

---

## 2. Risk register

Scale: Likelihood / Impact — Low · Medium · High.

| ID | Risk | L | I | Mitigation | Watched by | Status |
|---|---|---|---|---|---|---|
| R-02 | A synchronous Cognito trigger in the sync chain times out (5 s hard limit) on a cold start → sign-up fails for the user | Medium | High | Decided with the Week 3 wiring: keep the trigger function minimal (only `PutEvents`) or use an asynchronous path; measure the cold start | Week 3 planning | Open |
| R-05 | The embedding model required in Week 4 is unavailable or not enabled in the region of the build | Medium | High | Check model access in the Bedrock console when Week 4 is planned ([Q-15](#q-15)) | Week 4 planning | Open |
| R-06 | Cost of the idle environment (RDS, RDS Proxy, NAT) — figures in [backend-foundation](design/backend-foundation.md) §Cost; a manually built environment cannot be removed and recreated cheaply | High | Medium | AWS Budgets alert (T00-01); stop the RDS instance when idle; record every change as a runbook; IaC task T00-03 | T00-01, T01-06 | Open |
| R-09 | Private subnets without a NAT or VPC endpoint: any AWS service call times out at runtime | Medium | Medium | Relevant only if the Week 1 build has no NAT (T01-06 records the layout); every new AWS dependency checked by ARCH | T01-06 | Open |
| R-10 | Double-wrapped or unparsable logs when Lambda advanced logging (JSON) meets Powertools JSON | Medium | Low | Spike in Week 6 before standardising (ADR-012); until then one stdlib JSON line per invocation | Week 6 planning | Open |
| R-11 | The user is `CONFIRMED` in Cognito but the copy in PostgreSQL is missing or late (sync failure, asynchronous chain) | Medium | Medium | Designed in Week 3: idempotent upsert by `sub`, tolerant of invalid attribute values (Q-14), re-sync runbook, "profile not ready" state where the SPA reads the copy | Week 3 planning | Open |
| R-12 | The user can change own Cognito attributes through the public `UpdateUserAttributes` API (the app client must allow writing them for `SignUp`), bypassing the SPA validation; later also drift against the PostgreSQL copy | Low | Low | Accepted for Week 2 (no edit feature). Week 3: decide whether attribute changes are synced | T02-01, Week 3 planning | Open |
| R-13 | Cognito default e-mail sender is limited to a small daily quota (50 e-mails/day per AWS docs at the time of writing), so sign-up tests can stop receiving codes | Low | Low | Enough for learning; switch to Amazon SES only if the quota is hit (new task) | T02-01, T02-06 | Open |
| R-14 | PostgreSQL 14 (Week 1 build): RDS standard support ends 2027-02-28; from 2027-03-01 RDS Extended Support is charged per vCPU-hour (estimate at the PG 11–13 rate, $0.122/vCPU-h in eu-central-1: ~$178/month for 2 vCPUs, ~13× the instance). Local `docker-compose.yml` runs PostgreSQL 17 | Medium | High | Upgrade to a supported major as a dedicated task, or remove the instance, before 2027-02-28; align `docker-compose.yml` with the RDS major in the first database task (Week 3) | owner, Week 3 planning | Open |
| R-15 | Week 1 resources and Lambda code exist only in AWS (console-built): the code is not in Git, settings are not reproducible, console edits can overwrite code deployed from Git | High | Medium | T01-06 records the settings; T02-02 brings `admin` into Git, `sync` and `chatbot` follow in their weeks; no console code edits of a function once its code is in Git; IaC task T00-03 | T01-06, T02-02 | Open |

---

## 3. Closed items

| ID | Resolution | Date | Decided by |
|---|---|---|---|
| R-07 | Closed: RDS Proxy supports RDS for PostgreSQL 10–18 (AWS docs checked), so it does not limit the version choice | 2026-11-05 | ARCH |
| <a id="q-01"></a>Q-01 | Decided by the Week 1 build: the CloudFront distribution managed by Amplify Hosting; "isolated VPC" refers to the backend. Proof by response headers (AC-01.1); Amplify app id/domain to be recorded by T01-06 | 2026-11-12 | OWNER |
| <a id="q-03"></a>Q-03 | Decided by the Week 1 build (ADR-009); value to be recorded by T01-06 | 2026-11-12 | OWNER |
| <a id="q-04"></a>Q-04 | Decided by the Week 1 build: GitHub (local `origin` remote `github.com/maxim-semenko/aws_challenge`); the Amplify connection to it is recorded by T01-06 | 2026-11-12 | OWNER |
| <a id="q-06"></a>Q-06 | Answered by the curriculum (Week 5): Bedrock Agent, NL→SQL when the query contains "sql", otherwise embedding similarity; designed when Week 5 is planned; ADR-010 superseded | 2026-11-12 | OWNER (curriculum) |
| <a id="q-07"></a>Q-07 | Decided by the Week 1 build; environment(s) and resource names to be recorded by T01-06 | 2026-11-12 | OWNER |
| <a id="q-08"></a>Q-08 | Decided by the Week 1 build; subnet/NAT layout to be recorded by T01-06; ADR-005 superseded | 2026-11-12 | OWNER |
| <a id="q-09"></a>Q-09 | PostgreSQL 14, as in the curriculum and the build; minor version to be recorded by T01-06; consequences in R-14 | 2026-11-12 | OWNER |
| <a id="q-10"></a>Q-10 | The three Week 1 functions were created manually in Python; runtime version, architecture, memory, timeout and the probe's driver to be recorded by T01-06; T01-03 (Java handlers) deleted as obsolete; ADR-015 | 2026-11-12 | OWNER |
| <a id="q-11"></a>Q-11 | Decided by the Week 1 build; which SDK(s) are configured locally (JS SDK v3 / boto3) to be recorded by T01-06 (AC-03.2) | 2026-11-12 | OWNER |
| <a id="q-12"></a>Q-12 | Option C: AWS changes with AWS CLI commands recorded as a replayable runbook in each devops task's Notes; IaC in a separate later task (T00-03, tool per Q-02). Week 1 was built manually by the owner; T01-06 verifies it and records the actual resources; IaC ACs (AC-01.4, AC-02.9) deferred to T00-03 | 2026-11-12 | OWNER |
| <a id="q-13"></a>Q-13 | Closed by ADR-015: Python 3.13 Lambda functions; `sync` and `migrate` moved to Week 3 with the curriculum | 2026-11-12 | OWNER |
| R-01 | Closed: Spring Boot is not used (ADR-015) | 2026-11-12 | OWNER |
| R-03 | Closed: `aws-serverless-java-container` is not used (ADR-015) | 2026-11-12 | OWNER |
| R-04 | Closed: the backend draft was deleted by the owner; the remaining `frontend/src` draft is handled by T00-04 (build), T02-04 (auth screens) and T02-05 (API client sends the access token, ADR-004) | 2026-11-12 | OWNER |
| R-08 | Closed: SnapStart is not used (ADR-015) | 2026-11-12 | OWNER |
