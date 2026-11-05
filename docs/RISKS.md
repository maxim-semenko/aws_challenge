# RISKS.md — Open Decisions and Risk Register

Related: [ARCHITECTURE.md](ARCHITECTURE.md) · [PLAN.md](PLAN.md) · [design/](design/) · [tasks/](tasks/)
Last updated: 2026-11-05

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
| [Q-01](#q-01) | Meaning of "CloudFront inside an isolated VPC" (G2) | CloudFront from Amplify Hosting + private subnets for backend | OWNER | Open | T01-05 |
| [Q-02](#q-02) | Infrastructure-as-Code tool | AWS CDK (Java) | OWNER + ARCH | Open | T00-03 |
| [Q-03](#q-03) | AWS region | `eu-central-1` (or `us-east-1`) | OWNER | Open | T00-01, T00-03 |
| [Q-04](#q-04) | Git hosting | GitHub | OWNER | Open | T00-02 |
| [Q-05](#q-05) | Chatbot knowledge base: source, volume, language | define a sample dataset | OWNER | Deferred (not needed in Week 1) | — |
| [Q-06](#q-06) | Stage 2: LLM answers / Bedrock Agent / NL→SQL | decide after semantic search works | OWNER | Deferred (not needed in Week 1) | — |
| [Q-07](#q-07) | Environments | single `dev` environment | OWNER | Open | T00-03 |
| [Q-08](#q-08) | Network layout: curriculum (public subnet + NAT) vs ADR-005 (isolated, no NAT) | A — follow the curriculum | OWNER | Open | T01-01 |
| [Q-09](#q-09) | PostgreSQL major version: 14 (curriculum) vs newest supported | 17 (same as local Docker), deviation noted | OWNER | Open | T01-02 |
| [Q-10](#q-10) | Code of the Week 1 "empty" Lambda functions | A — plain-Java handlers in a separate module | OWNER + ARCH | Open | T01-03 |
| [Q-11](#q-11) | Meaning of "AWS SDK v3 configured locally" | JS SDK v3 + Java SDK 2.x, same profile | OWNER | Open | T00-01 |

### <a id="q-01"></a>Q-01 — "CloudFront inside an isolated VPC"

Goal G2 reads "configure global content delivery via Amazon CloudFront inside an isolated VPC". CloudFront is a
global edge service and is never deployed inside a VPC.

| Option | Meaning | Effort |
|---|---|---|
| **A (recommended)** | CloudFront is the one Amplify Hosting manages for the SPA; "isolated VPC" refers to the backend (Lambda, RDS Proxy, RDS in private isolated subnets) | none extra |
| B | Own CloudFront distribution in front of both SPA and API Gateway (single domain, WAF in one place) | +1–2 days |
| C | CloudFront **VPC origins** to a private ALB/EC2 origin | does not fit the serverless design; not recommended |

Note (2026-11-05): with option A the CloudFront distribution belongs to Amplify and is not visible or manageable in our
account (re:Post, not official docs). The proof of G2 is then the response headers (`Via: … cloudfront.net`,
`X-Cache`, `X-Amz-Cf-Id`) — spec 01 AC-01.1. If the owner wants a distribution visible in the account, choose B.

### <a id="q-02"></a>Q-02 — IaC tool

| Option | Pros | Cons |
|---|---|---|
| **AWS CDK, Java (recommended)** | same language as backend, good L2 constructs (VPC, RDS Proxy, HTTP API, Cognito), cdk-nag for checks | needs CDK CLI (Node) and `cdk bootstrap` |
| Terraform | industry standard, provider-agnostic | second language (HCL), more boilerplate |
| AWS SAM | simple for Lambda | weak for VPC/RDS/Proxy |
| Console clicks | fast to start | not reproducible; against "You Build It, You Run It" |

### <a id="q-03"></a>Q-03 — Region

Must offer Bedrock `amazon.titan-embed-text-v2:0`, RDS Proxy for the chosen PostgreSQL version, Lambda SnapStart
on arm64, Amplify Hosting. Candidates: `eu-central-1` (closer to the team) or `us-east-1` (widest Bedrock catalog).
Verify model availability in the Bedrock console before deciding (see R-05).

### <a id="q-04"></a>Q-04 — Git hosting

Amplify Hosting supports GitHub, GitLab, Bitbucket and CodeCommit. The choice also defines the CI platform
(e.g. GitHub Actions with OIDC to AWS). The project is not under version control yet.

### <a id="q-05"></a>Q-05 — Chatbot knowledge base

What documents does the chatbot search? Needed: source and format (PDF, Markdown, web pages, DB rows), approximate
size (documents / total text), language(s), update frequency. Drives chunking and the ≥ 10k-vector dataset for
the HNSW / IVFFlat experiments. If no real data exists, approve a public sample dataset.

### <a id="q-06"></a>Q-06 — Stage 2: LLM

The architecture diagram shows a Bedrock Agent (Claude 3) doing NL→SQL / vector search. Goals G1–G8 only require
embeddings and vector search. Options: (a) no LLM; (b) RAG answers with Claude via Bedrock Converse API;
(c) Bedrock Agent with action groups. Recommendation: decide after semantic search works.

### <a id="q-07"></a>Q-07 — Environments

Single `dev` environment (recommended for a learning project and cost) or `dev` + `prod`. Affects naming, CI/CD
promotion and cost.

### <a id="q-08"></a>Q-08 — Network layout

Source: [Week 1 requirements](requirements/week-01-environment.md) step S3 asks for 1 public subnet, 2 private subnets and a NAT
Gateway. ADR-005 (Proposed) has isolated subnets only, no NAT, with interface endpoints.

| Option | Layout | Pros | Cons |
|---|---|---|---|
| **A (recommended)** | 1 public subnet (NAT Gateway, 1 AZ) + 2 private-with-egress subnets (2 AZs) for Lambda, RDS, Proxy | matches the curriculum and its checks; any AWS service reachable without one endpoint per service (removes R-09); simple | NAT cost runs 24/7; outbound internet path exists; single-AZ NAT is a single point of failure (acceptable for learning) |
| B | Keep ADR-005: isolated subnets + `secretsmanager` / `bedrock-runtime` endpoints | no internet path, closest to "isolated VPC" in G2 | deviates from the curriculum; every new AWS service needs an endpoint |
| C | A for Lambda + separate isolated subnets for RDS/Proxy | data tier has no route out; still matches the curriculum | 4 private subnets, slightly more config |

If A or C is accepted, ADR-005 is rewritten and ARCHITECTURE.md §4 updated before T01-01 starts.

Cost (AWS Price List API, 2026-11-05, 730 h/month, without data transfer):

| Item | eu-central-1 | us-east-1 |
|---|---|---|
| NAT Gateway, 1 AZ | ~$38 + $0.052/GB | ~$33 + $0.045/GB |
| Interface endpoint, 2 AZs (per service) | ~$17.5 | ~$14.6 |
| Option B with `secretsmanager` + `bedrock-runtime` | ~$35 | ~$29 |

Options A and B cost about the same; the difference is behaviour, not price. Note: a Lambda in a VPC needs NAT or an
endpoint to reach Secrets Manager and Bedrock; whether Lambda's own log delivery needs anything is not documented
for standard functions and must be checked in the account.

### <a id="q-09"></a>Q-09 — PostgreSQL version

Curriculum step S4 says PostgreSQL 14. ARCHITECTURE.md §3.5 says "newest major supported by RDS Proxy"; local
`docker-compose.yml` runs 17.

Facts (checked 2026-11-05, AWS docs and Price List API):

- RDS Proxy supports RDS for PostgreSQL 10–18, so the proxy does not restrict the choice (R-07 is not a constraint).
- PostgreSQL 14: community end of life 2026-11-12; RDS standard support ends **2027-02-28**; from 2027-03-01 RDS
  Extended Support is charged per vCPU-hour. The PG 14 rate is not published yet; at the PG 11–13 rate
  ($0.122/vCPU-h in eu-central-1) a 2-vCPU `db.t4g.micro` would cost ~$178/month extra, about 13× the instance.
- PostgreSQL 17: standard support until 2030-02-28. pgvector with HNSW is available on all current 14.x and 17.x
  minors (0.8.x).
- CDK has `PostgresEngineVersion.VER_14` … `VER_18`.

Options: (a) 14 exactly as written — fine for Week 1, but the stack must be destroyed or upgraded before 2027-03-01;
(b) **17 (recommended)** — same major as local Docker and Testcontainers, no support deadline during the project,
deviation noted in the Week 1 report; (c) 14 now, major upgrade as a separate task later (extra work that teaches
RDS upgrades). Whatever is chosen, local Docker and Testcontainers use the same major.

### <a id="q-10"></a>Q-10 — Code of the Week 1 Lambda functions

Curriculum step S5 asks for three *empty* functions (Admin, Chatbot, Sync) and S6 for `SELECT 1` from Admin.
The planned code is one Spring Boot artifact with SnapStart (ADR-002), but the draft has never compiled (R-04).

| Option | Meaning |
|---|---|
| **A (recommended)** | Week 1 handlers are small plain-Java classes (no Spring context) in a separate small Gradle module, so the uncompiled draft in `backend` does not block Week 1: `admin` runs `SELECT 1` via JDBC with credentials from Secrets Manager; `chatbot` and `sync` only log and return. Replaced by the Spring handlers later |
| A2 | Same as A, but inside `backend` — then a green build of the draft becomes a Week 1 prerequisite (new task) |
| B | Review the draft first and deploy the Spring artifact with all three handlers from the start |
| C | Inline/placeholder code defined in IaC only; `SELECT 1` in a separate throw-away function |

### <a id="q-11"></a>Q-11 — "AWS SDK v3 configured locally"

"AWS SDK v3" is the AWS SDK for JavaScript. The backend uses the AWS SDK for Java 2.x (no Java v3 exists); the
frontend uses Amplify, which uses the JS SDK v3 internally. Recommendation: accept W1-G3 as (1) AWS CLI v2 profile
works and (2) both SDKs resolve the same profile — a one-off check with the Java SDK default credential chain and
with `@aws-sdk/client-sts` (Node), recorded in T00-01. Alternative: Java SDK only, deviation noted.

---

## 2. Risk register

Scale: Likelihood / Impact — Low · Medium · High.

| ID | Risk | L | I | Mitigation | Watched by | Status |
|---|---|---|---|---|---|---|
| R-01 | Spring Boot cold start in Lambda is 4–8 s | High | Medium | SnapStart, arm64, priming hooks, lazy beans; measure before/after | later phase (Spring in Lambda) | Open |
| R-02 | Cognito PostConfirmation trigger times out (5 s hard limit) on a cold start → sign-up fails for the user | High | High | SnapStart on `sync` and trigger bound to the published alias; minimal Spring context; fallback: plain handler without Spring or provisioned concurrency = 1 | later phase (Cognito) | Open |
| R-03 | Version incompatibility: `aws-serverless-java-container-springboot4` 3.0.x is built for Spring Boot 4.0.x | Medium | Medium | Pin Spring Boot 4.0.x (ADR-002); upgrade only as a dedicated task | later phase (Spring in Lambda) | Open |
| R-04 | Draft code was written before the plan and never compiled (no Maven access at authoring time) | High | Medium | Treat as untrusted draft; review with a green build before any use. Known issue for that review: `frontend/src/api/client.ts` sends the ID token, ADR-004 proposes the access token | T00-04 (frontend); backend draft — later phase | Open |
| R-05 | Titan Text Embeddings v2 unavailable or not enabled in the chosen region | Medium | High | Check model access when choosing the region (Q-03) | later phase (Bedrock) | Open |
| R-06 | Cost of an idle stack (RDS, RDS Proxy, NAT or interface endpoints) — figures in [backend-foundation](design/backend-foundation.md) §Cost | High | Medium | AWS Budgets alert before the first deploy; destroy stacks when idle | T00-01, T01-02, T01-06 | Open |
| R-08 | SnapStart restores stale state (open DB connections, cached credentials, random seeds) | Medium | High | No DB connections during init (Hikari `minimum-idle=0`), refresh secrets after restore, CRaC `afterRestore` hooks | later phase (SnapStart) | Open |
| R-09 | Isolated subnets have no internet: any AWS service without a VPC endpoint times out at runtime | Medium | Medium | Every new AWS dependency requires an endpoint (ARCH review); integration test in dev for each call path | T01-01 (only if Q-08 = B) | Open |
| R-10 | Double-wrapped or unparsable logs when Lambda JSON log format meets app-level JSON | Medium | Low | Spike before standardising the log format (ADR-012); Week 1 handlers print plain JSON lines | T01-03 | Open |

---

## 3. Closed items

| ID | Resolution | Date | Decided by |
|---|---|---|---|
| R-07 | Closed: RDS Proxy supports RDS for PostgreSQL 10–18 (AWS docs checked), so it does not limit the version choice (see Q-09) | 2026-11-05 | ARCH |
