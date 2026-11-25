# RISKS.md — Open Decisions and Risk Register

Related: [ARCHITECTURE.md](ARCHITECTURE.md) · [PLAN.md](PLAN.md) · [design/](design/) · [tasks/](tasks/)
Last updated: 2026-11-18

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

---

## 2. Risk register

Scale: Likelihood / Impact — Low · Medium · High.

| ID | Risk | L | I | Mitigation | Watched by | Status |
|---|---|---|---|---|---|---|
| R-02 | A synchronous Cognito trigger in the sync chain times out (5 s hard limit) on a cold start → confirmation fails | Medium | High | Q-17 A: the trigger is outside the VPC, only `boto3` + one `PutEvents`, never raises on a `PutEvents` failure (logs it, returns the event; R-11 re-sync); memory 256 MB; cold-start duration recorded by T03-05 (AC-07.4) | T03-04, T03-05 | Open |
| R-06 | Cost of the idle environment (RDS, RDS Proxy, NAT if any) — figures in [backend-foundation](design/backend-foundation.md) §Cost; a manually built environment cannot be removed and recreated cheaply | High | Medium | AWS Budgets alert (T00-01); stop the RDS instance when idle; Bedrock interface endpoint only during working sessions (ADR-020); record every change as a console runbook; IaC task T00-03 | owner | Open |
| R-09 | No outbound path from the private subnets: the owner's VPC network map (2026-11-12, [ARCHITECTURE §4](ARCHITECTURE.md#4-network)) shows no NAT gateway (curriculum Week 1 S3 asked for one) and only an S3 gateway endpoint, so calls from private-subnet Lambdas to Secrets Manager, Cognito, EventBridge or Bedrock time out. Not a Week 2 blocker: Week 2 adds no Lambda code (spec 05, reduced 2026-11-13). Open point: the Week 1 `admin` probe reads the DB secret from Secrets Manager — if it works, either a NAT/interface endpoint exists after all, or the function is not in the private subnets, or it does not read Secrets Manager | Medium | Medium | Week 3: [Q-18](#q-18) A (IAM auth to the proxy needs no egress) together with Q-17 A (event carries the attributes; the trigger runs outside the VPC); the open point is answered by the owner facts F1–F5 collected in step 1 of the T03-03 runbook. Week 4–5 (Bedrock): [Q-20](#q-20) A — `bedrock-runtime` interface endpoint created on demand (ADR-020; consequences in R-18); every new AWS dependency of a VPC Lambda checked by ARCH | owner, T03-03, T04-01 | Open |
| R-18 | The `bedrock-runtime` endpoint exists only during working sessions (ADR-020): users confirmed while it is absent get `embedding` NULL (not found by similarity search until back-filled); a forgotten endpoint costs ≈ $8/month; Week 5's `chatbot` needs it for every query | High | Low | `sync` fails fast and never raises on a Bedrock error (spec 10); every Week 4+ runbook that needs Bedrock starts with "create endpoint", runs `embed-missing`, and ends with "delete endpoint" (T04-01 procedure); AWS Budgets alert (T00-01) | T04-01, T04-03, Week 5 planning | Open |
| R-17 | The 1000 synthetic users of the Week 4 latency check (spec 11) sit in `users` next to real users: they appear in the admin table and in Week 5 similarity results | High | Low | Fictitious values only, e-mail domain `seed.invalid` (identifiable, never deliverable), deterministic ids; kept on purpose for Week 5; removal (a `DELETE … WHERE email LIKE '%@seed.invalid'` action) only as a later task if the owner wants it | T04-03, Week 5 planning | Open |
| R-10 | Double-wrapped or unparsable logs when Lambda advanced logging (JSON) meets Powertools JSON | Medium | Low | Spike in Week 6 before standardising (ADR-012); until then one stdlib JSON line per invocation | Week 6 planning | Open |
| R-11 | The user is `CONFIRMED` in Cognito but the copy in PostgreSQL is missing or late (sync failure, asynchronous chain) | Medium | Medium | Designed in Week 3 ([design/user-sync](design/user-sync.md), spec 07): idempotent upsert by `sub`; unparsable values stored as NULL, out-of-range values stored as is; the trigger never blocks confirmation; Lambda async retries; re-sync runbook (owner sends the event from the EventBridge console); users confirmed before the trigger existed are back-filled by the same runbook. With Q-19 A the personal page does not read the copy | T03-04, T03-05 | Open |
| R-12 | The SPA is the only validation of registration values (Q-14 C): a direct call to the public `SignUp` or `UpdateUserAttributes` API (the app client must allow writing the attributes for `SignUp`) can store out-of-range or missing values; later also drift against the PostgreSQL copy | Low | Low | Accepted for Week 2 (no edit feature). Week 3 (proposed in design/user-sync): attribute changes are **not** synced (only confirmation is an event; Cognito has no attribute-change trigger); the admin table may drift from Cognito until a re-sync; revisit if editing is ever added | T02-01, T03-04 | Open |
| R-13 | Cognito default e-mail sender is limited to a small daily quota (50 e-mails/day per AWS docs at the time of writing), so sign-up tests can stop receiving codes | Low | Low | Enough for learning; switch to Amazon SES only if the quota is hit (new task) | T02-01, T02-06 | Open |
| R-14 | PostgreSQL 14 (Week 1 build): RDS standard support ends 2027-02-28; from 2027-03-01 RDS Extended Support is charged per vCPU-hour (estimate at the PG 11–13 rate, $0.122/vCPU-h in eu-central-1: ~$178/month for 2 vCPUs, ~13× the instance). Local `docker-compose.yml` runs PostgreSQL 17 | Medium | High | Upgrade to a supported major as a dedicated task, or remove the instance, before 2027-02-28; T03-02 aligns `docker-compose.yml` with the RDS major (PostgreSQL 14) and keeps the Week 3 SQL valid on 14–17 (no syntax newer than 14) | owner, T03-02 | Open |
| R-15 | Week 1 resources and Lambda code exist only in AWS (console-built): the code is not in Git, settings are not reproducible, console edits can overwrite code deployed from Git | High | Medium | Known settings in ENVIRONMENT.md, the rest supplied by the owner on demand (facts F1–F5, step 1 of the T03-03 runbook); Week 3 brings `sync` (T03-02 runner, T03-04 upsert) and `admin` (T03-06) into Git and adds `post-confirmation` from Git; `chatbot` follows in Week 5; no console code edits of a function once its code is in Git; IaC task T00-03 | T03-03, T03-05, T03-07 | Open |
| R-16 | With Q-18 A every function connects as the one DB user registered with RDS Proxy (the master user as built), so the API function could change the schema or data beyond its needs | Medium | Medium | Accepted for Week 3 by the owner with Q-18 A (2026-11-13; single learning environment): the admin handler runs only parameterised `SELECT`s, the sync handler one upsert per event and the repository's migration files only on the owner's explicit `migrate` invoke (ADR-017 revised); per-function DB roles (each with its own proxy secret) proposed as a later task when the owner wants it | T03-06, T03-04 | Accepted (OWNER, 2026-11-13) |

---

## 3. Closed items

| ID | Resolution | Date | Decided by |
|---|---|---|---|
| <a id="q-15"></a>Q-15 | Embedding model — option c: **Amazon Titan Text Embeddings V2** (`amazon.titan-embed-text-v2:0`) in eu-west-1, in-region, **dimension 1024**, normalised output; column `vector(1024)`. **Deliberate deviation from W4-G2 (1536):** the only 1536-dim Titan model (Titan Embeddings G1 – Text) is not offered in eu-west-1 and would need a NAT gateway plus a cross-region call (≈ $39/month); the curriculum goal G7 names Titan, and V2 is the cheapest model with no Marketplace subscription. Rejected: Cohere Embed v4 at 1536 (third-party, not Titan), Titan G1 in eu-central-1 (NAT). Recorded as ADR-019 (Accepted; supersedes ADR-007, whose original value — Titan V2, 1024 — it matches); options in [design/vectorisation](design/vectorisation.md) §Alternatives. T04-01, T04-02, T04-03 unblocked | 2026-11-18 | OWNER |
| <a id="q-20"></a>Q-20 | Network path to Bedrock — option A, **on demand**: interface endpoint `com.amazonaws.eu-west-1.bedrock-runtime` in one private subnet (private DNS, own SG with TCP 443 from the Lambda SG), created by the owner for a working session and deleted afterwards (≈ $0.011/h instead of ≈ $8/month); while it is absent `sync` fails fast, stores the row with `embedding` NULL and does not raise; `embed-missing` fills the gaps later (R-18). Rejected: NAT gateway (≈ $39/month), embedding in `post-confirmation` (contradicts S2). Recorded as ADR-020 (Accepted). T04-01, T04-03 unblocked | 2026-11-18 | OWNER |
| R-05 | Closed by Q-15 (2026-11-18): the chosen model, Titan Text Embeddings V2, is offered in-region in eu-west-1; the owner confirms access and the model id in T04-01 | 2026-11-18 | OWNER |
| <a id="q-05"></a>Q-05 | Answered by the curriculum (Week 4): embeddings are stored in `users.embedding`, so the search runs over the users table (Week 5); the ≥ 1000-record test dataset is seeded by the `seed` action of spec 11 | 2026-11-17 | OWNER (curriculum) |
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
| <a id="q-13"></a>Q-13 | Closed by ADR-015: Python Lambda functions; `sync` moved to Week 3 with the curriculum. *Amended 2026-11-16 (owner):* runtime Python 3.12 (ADR-015 revised); no `migrate` function (ADR-017 revised) | 2026-11-12 | OWNER |
| <a id="q-14"></a>Q-14 | Registration fields — option C: custom attributes `custom:country` (String), `custom:height`, `custom:weight` (Number) created without min/max constraints in Cognito; all validation in the SPA with the proposed ranges unchanged; required standard attributes `given_name`, `family_name`, `email` (sign-in, auto-verified), `gender`, `birthdate`. Field table (single home): [spec 04 §Inputs](specs/04-user-registration-and-sign-in.md#inputs); decision recorded in [design/authentication](design/authentication.md); consequences in R-11, R-12. T02-01, T02-04 unblocked | 2026-11-12 | OWNER |
| <a id="q-16"></a>Q-16 | Database migrations — option A: versioned SQL files applied by a Python runner inside the VPC, invoked by the owner from the console Test tab; recorded as ADR-017 (Accepted, replaces ADR-008); detail and rejected options in [design/user-sync](design/user-sync.md) §2, §Alternatives; contract in [spec 06](specs/06-users-table-and-migrations.md). T03-02, T03-03 unblocked. *Amended 2026-11-16 (owner):* no function `aws-challenge-migrate`; the runner is a module of `aws-challenge-sync` (files `lambdas/sync/migrations/V<n>__<description>.sql`), reached by the direct invoke `{"action":"status"\|"migrate"}`, while EventBridge `UserConfirmed` events go to the upsert; reason: only the curriculum's functions (plus the ADR-016 trigger); ADR-017 revised | 2026-11-13, amended 2026-11-16 | OWNER |
| <a id="q-17"></a>Q-17 | Sync chain wiring — option A: PostConfirmation trigger `aws-challenge-post-confirmation` (outside the VPC) → `PutEvents` to the custom bus `aws-challenge-events` → rule `aws-challenge-user-confirmed` → `aws-challenge-sync`; recorded as ADR-016 (Accepted); detail and rejected options (CloudTrail + default bus, SQS + Pipes) in [design/user-sync](design/user-sync.md) §3, §Alternatives; contract in [spec 07](specs/07-user-sync.md). T03-04, T03-05 unblocked | 2026-11-13 | OWNER |
| <a id="q-18"></a>Q-18 | Database credentials and network path — option A: IAM authentication to RDS Proxy (local auth token, TLS, `rds-db:connect` on the proxy `dbuser` ARN), no egress from the private subnets in Week 3 ($0; rejected: Secrets Manager interface endpoint ≈ $8/AZ-month, NAT ≈ $39/month); recorded as the revised ADR-006 (Accepted); R-16 accepted. The owner facts F1–F5 are not a blocker: they are collected as step 1 of the T03-03 runbook (fact list there) and recorded in ENVIRONMENT.md. T03-02 … T03-07 unblocked | 2026-11-13 | OWNER |
| <a id="q-19"></a>Q-19 | Personal page source — option A: profile values stay from Cognito (`fetchUserAttributes`, ADR-013 unchanged); `GET /api/me` returns identity and groups from the token claims (no DB call) and drives the role line and the admin-only nav; detail in [design/admin-api](design/admin-api.md), [spec 08](specs/08-admin-api.md), [spec 09](specs/09-admin-page-and-role.md). T03-06, T03-08 unblocked. *Amended 2026-11-17 (owner, ADR-018):* no `GET /api/me`; the role line and the nav read `cognito:groups` from the access token | 2026-11-13 | OWNER |
| R-01 | Closed: Spring Boot is not used (ADR-015) | 2026-11-12 | OWNER |
| R-03 | Closed: `aws-serverless-java-container` is not used (ADR-015) | 2026-11-12 | OWNER |
| R-04 | Closed: the backend draft was deleted by the owner; the remaining `frontend/src` draft is handled by T00-04 (build), T02-04 (auth screens) and T02-05 (API client sends the access token, ADR-004) | 2026-11-12 | OWNER |
| R-08 | Closed: SnapStart is not used (ADR-015) | 2026-11-12 | OWNER |
