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
| [Q-15](#q-15) | Vector dimension and model: 1536 (Week 4 curriculum) vs 1024 (ADR-007) | decide when Week 4 is planned | OWNER + ARCH | Open (Week 4, not blocking now) | — |
| [Q-16](#q-16) | Database migrations without Java/Flyway-in-Lambda | A — versioned SQL files + small Python runner | OWNER + ARCH | Open (Week 3, not blocking now) | — |

### <a id="q-02"></a>Q-02 — IaC tool

Deferred by Q-12 (option C): Week 1 and Week 2 resources are created manually by the owner in the console (from
devops console runbooks); a dedicated task (T00-03) codifies them later. The tool should import existing resources
(the Cognito pool cannot be recreated without losing users). Agents have no AWS access (CLAUDE.md §3.11), so the owner
runs the IaC tool's deploy/import commands.

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
| R-06 | Cost of the idle environment (RDS, RDS Proxy, NAT if any) — figures in [backend-foundation](design/backend-foundation.md) §Cost; a manually built environment cannot be removed and recreated cheaply | High | Medium | AWS Budgets alert (T00-01); stop the RDS instance when idle; record every change as a console runbook; IaC task T00-03 | owner | Open |
| R-09 | No outbound path from the private subnets: the owner's VPC network map (2026-11-12, [ARCHITECTURE §4](ARCHITECTURE.md#4-network)) shows no NAT gateway (curriculum Week 1 S3 asked for one) and only an S3 gateway endpoint, so calls from private-subnet Lambdas to Secrets Manager, Cognito, EventBridge or Bedrock time out. Not a Week 2 blocker: the `admin` API routes read JWT claims only (spec 05). Open point: the Week 1 `admin` probe reads the DB secret from Secrets Manager — if it works, either a NAT/interface endpoint exists after all, or the function is not in the private subnets, or it does not read Secrets Manager | Medium | Medium | Owner confirms whether a NAT gateway (or a Secrets Manager interface endpoint) exists; before Week 3 (Secrets Manager from `admin`/`sync`, EventBridge) and Week 4–5 (Bedrock) the architect proposes NAT gateway (approx. $35/month + data) vs interface VPC endpoints per service (approx. $8/month each per AZ), re-priced for eu-west-1 at that time; every new AWS dependency of a Lambda checked by ARCH | owner, Week 3 planning | Open |
| R-10 | Double-wrapped or unparsable logs when Lambda advanced logging (JSON) meets Powertools JSON | Medium | Low | Spike in Week 6 before standardising (ADR-012); until then one stdlib JSON line per invocation | Week 6 planning | Open |
| R-11 | The user is `CONFIRMED` in Cognito but the copy in PostgreSQL is missing or late (sync failure, asynchronous chain) | Medium | Medium | Designed in Week 3: idempotent upsert by `sub`, tolerant of missing or out-of-range attribute values (Q-14 C: Cognito stores whatever a direct `SignUp` call sends), re-sync runbook, "profile not ready" state where the SPA reads the copy | Week 3 planning | Open |
| R-12 | The SPA is the only validation of registration values (Q-14 C): a direct call to the public `SignUp` or `UpdateUserAttributes` API (the app client must allow writing the attributes for `SignUp`) can store out-of-range or missing values; later also drift against the PostgreSQL copy | Low | Low | Accepted for Week 2 (no edit feature). Week 3: decide whether attribute changes are synced | T02-01, Week 3 planning | Open |
| R-13 | Cognito default e-mail sender is limited to a small daily quota (50 e-mails/day per AWS docs at the time of writing), so sign-up tests can stop receiving codes | Low | Low | Enough for learning; switch to Amazon SES only if the quota is hit (new task) | T02-01, T02-06 | Open |
| R-14 | PostgreSQL 14 (Week 1 build): RDS standard support ends 2027-02-28; from 2027-03-01 RDS Extended Support is charged per vCPU-hour (estimate at the PG 11–13 rate, $0.122/vCPU-h in eu-central-1: ~$178/month for 2 vCPUs, ~13× the instance). Local `docker-compose.yml` runs PostgreSQL 17 | Medium | High | Upgrade to a supported major as a dedicated task, or remove the instance, before 2027-02-28; align `docker-compose.yml` with the RDS major in the first database task (Week 3) | owner, Week 3 planning | Open |
| R-15 | Week 1 resources and Lambda code exist only in AWS (console-built): the code is not in Git, settings are not reproducible, console edits can overwrite code deployed from Git | High | Medium | Known settings in ARCHITECTURE §4, the rest supplied by the owner on demand; T02-02 brings `admin` into Git, `sync` and `chatbot` follow in their weeks; no console code edits of a function once its code is in Git; IaC task T00-03 | T02-02 | Open |

---

## 3. Closed items

| ID | Resolution | Date | Decided by |
|---|---|---|---|
| R-07 | Closed: RDS Proxy supports RDS for PostgreSQL 10–18 (AWS docs checked), so it does not limit the version choice | 2026-11-05 | ARCH |
| <a id="q-01"></a>Q-01 | Decided by the Week 1 build: the CloudFront distribution managed by Amplify Hosting; "isolated VPC" refers to the backend. Proof by response headers (AC-01.1); Amplify app id/domain not recorded yet (ARCHITECTURE §4) | 2026-11-12 | OWNER |
| <a id="q-03"></a>Q-03 | Decided by the Week 1 build: `eu-west-1` (ADR-009, ARCHITECTURE §4) | 2026-11-12 | OWNER |
| <a id="q-04"></a>Q-04 | Decided by the Week 1 build: GitHub (local `origin` remote `github.com/maxim-semenko/aws_challenge`), connected to Amplify Hosting (Week 1 accepted by the owner) | 2026-11-12 | OWNER |
| <a id="q-06"></a>Q-06 | Answered by the curriculum (Week 5): Bedrock Agent, NL→SQL when the query contains "sql", otherwise embedding similarity; designed when Week 5 is planned; ADR-010 superseded | 2026-11-12 | OWNER (curriculum) |
| <a id="q-07"></a>Q-07 | Decided by the Week 1 build: a single environment, resource names `aws-challenge-<name>` (CLAUDE.md §7, ARCHITECTURE §4) | 2026-11-12 | OWNER |
| <a id="q-08"></a>Q-08 | Decided by the Week 1 build: 2 public + 2 private subnets in 2 AZs, S3 gateway endpoint, NAT not confirmed (ARCHITECTURE §4, R-09); ADR-005 superseded | 2026-11-12 | OWNER |
| <a id="q-09"></a>Q-09 | PostgreSQL 14, as in the curriculum and the build; minor version not recorded yet; consequences in R-14 | 2026-11-12 | OWNER |
| <a id="q-10"></a>Q-10 | The three Week 1 functions were created manually in Python; runtime version, architecture, memory, timeout and the probe's driver not recorded yet (the owner supplies them for T02-02); T01-03 (Java handlers) deleted as obsolete; ADR-015 | 2026-11-12 | OWNER |
| <a id="q-11"></a>Q-11 | Decided by the Week 1 build (local SDK set-up on the owner's machine); agents use no SDK against AWS (CLAUDE.md §3.11) | 2026-11-12 | OWNER |
| <a id="q-12"></a>Q-12 | Option C, amended 2026-11-12: **agents have no AWS access**; the owner performs every AWS change manually in the console; the `devops` agent prepares a step-by-step console runbook (with the exact values to enter) in the task, the owner executes it and reports back the resulting identifiers and screenshots; evidence of AWS state comes from the owner; the `tester` verifies AWS-side ACs from that evidence and local ACs (SPA build, pytest) itself (CLAUDE.md §3.11). IaC in a separate later task (T00-03, tool per Q-02). Week 1 built manually and accepted by the owner; IaC ACs (AC-01.4, AC-02.9) deferred to T00-03 | 2026-11-12 | OWNER |
| <a id="q-13"></a>Q-13 | Closed by ADR-015: Python 3.13 Lambda functions; `sync` and `migrate` moved to Week 3 with the curriculum | 2026-11-12 | OWNER |
| <a id="q-14"></a>Q-14 | Registration fields — option C: custom attributes `custom:country` (String), `custom:height`, `custom:weight` (Number) created without min/max constraints in Cognito; all validation in the SPA with the proposed ranges unchanged; required standard attributes `given_name`, `family_name`, `email` (sign-in, auto-verified), `gender`, `birthdate`. Field table (single home): [spec 04 §Inputs](specs/04-user-registration-and-sign-in.md#inputs); decision recorded in [design/authentication](design/authentication.md); consequences in R-11, R-12. T02-01, T02-04 unblocked | 2026-11-12 | OWNER |
| R-01 | Closed: Spring Boot is not used (ADR-015) | 2026-11-12 | OWNER |
| R-03 | Closed: `aws-serverless-java-container` is not used (ADR-015) | 2026-11-12 | OWNER |
| R-04 | Closed: the backend draft was deleted by the owner; the remaining `frontend/src` draft is handled by T00-04 (build), T02-04 (auth screens) and T02-05 (API client sends the access token, ADR-004) | 2026-11-12 | OWNER |
| R-08 | Closed: SnapStart is not used (ADR-015) | 2026-11-12 | OWNER |
