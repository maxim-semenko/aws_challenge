# RISKS.md — Open Decisions and Risk Register

Related: [ARCHITECTURE.md](ARCHITECTURE.md) · [PLAN.md](PLAN.md) · [tasks/](tasks/)
Last updated: 2026-11-05

This file has two registers:

1. **Open decisions (`Q-xx`)** — questions that must be answered before some work can start. They **block** tasks.
2. **Risks (`R-xx`)** — things that may go wrong. They do not block tasks by themselves; they carry a mitigation
   and are watched by the tasks listed against them.

## Blocking rules

- A task that lists an **Open** `Q-xx` (or an `R-xx` escalated to *Blocking*) in its `Blocked by` field has status
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
| [Q-01](#q-01) | Meaning of "CloudFront inside an isolated VPC" (G2) | CloudFront from Amplify Hosting + isolated VPC for backend | OWNER | Open | INF-08 |
| [Q-02](#q-02) | Infrastructure-as-Code tool | AWS CDK (Java) | OWNER + ARCH | Open | INF-00 |
| [Q-03](#q-03) | AWS region | `eu-central-1` (or `us-east-1`) | OWNER | Open | ARCH-02, INF-01 |
| [Q-04](#q-04) | Git hosting | GitHub | OWNER | Open | OPS-01, OPS-02, INF-08 |
| [Q-05](#q-05) | Chatbot knowledge base: source, volume, language | define a sample dataset | OWNER | Open | BE-08, DB-02, DB-03 |
| [Q-06](#q-06) | Stage 2: LLM answers / Bedrock Agent / NL→SQL | defer until M4 is done | OWNER | Open | BE-11 |
| [Q-07](#q-07) | Environments | single `dev` environment | OWNER | Open | INF-01, OPS-03 |
| [Q-08](#q-08) | Network layout: curriculum (public subnet + NAT) vs ADR-005 (isolated, no NAT) | follow the curriculum, see below | OWNER | Open | INF-02, INF-03, INF-05 |
| [Q-09](#q-09) | PostgreSQL major version: 14 (curriculum) vs newest supported | 17 (same as local Docker), deviation noted | OWNER | Open | INF-03 |
| [Q-10](#q-10) | Code of the Week 1 "empty" Lambda functions | minimal plain-Java handlers in `backend` | OWNER + ARCH | Open | INF-05, BE-13 |
| [Q-11](#q-11) | Meaning of "AWS SDK v3 configured locally" | JS SDK v3 for Node tooling + Java SDK 2.x for backend | OWNER | Open | OPS-05 |

### <a id="q-01"></a>Q-01 — "CloudFront inside an isolated VPC"

Goal G2 reads "configure global content delivery via Amazon CloudFront inside an isolated VPC". CloudFront is a
global edge service and is never deployed inside a VPC.

| Option | Meaning | Effort |
|---|---|---|
| **A (recommended)** | CloudFront is the one Amplify Hosting manages for the SPA; "isolated VPC" refers to the backend (Lambda, RDS Proxy, RDS in private isolated subnets) | none extra |
| B | Own CloudFront distribution in front of both SPA and API Gateway (single domain, WAF in one place) | +1–2 days |
| C | CloudFront **VPC origins** to a private ALB/EC2 origin | does not fit the serverless design; not recommended |

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
size (documents / total text), language(s), update frequency. Drives chunking (BE-08) and the ≥ 10k-vector
dataset for index experiments (DB-02, DB-03). If no real data exists, approve a public sample dataset.

### <a id="q-06"></a>Q-06 — Stage 2: LLM

The architecture diagram shows a Bedrock Agent (Claude 3) doing NL→SQL / vector search. Goals G1–G8 only require
embeddings and vector search. Options: (a) no LLM; (b) RAG answers with Claude via Bedrock Converse API;
(c) Bedrock Agent with action groups. Recommendation: decide after M4.

### <a id="q-07"></a>Q-07 — Environments

Single `dev` environment (recommended for a learning project and cost) or `dev` + `prod`. Affects naming, CI/CD
promotion and cost.

### <a id="q-08"></a>Q-08 — Network layout

Source: [Week 1 spec](specs/week-01-environment.md) step S3 asks for 1 public subnet, 2 private subnets and a NAT
Gateway. ADR-005 (Proposed) has isolated subnets only, no NAT, with interface endpoints.

| Option | Layout | Pros | Cons |
|---|---|---|---|
| **A (recommended)** | 1 public subnet (NAT Gateway, 1 AZ) + 2 private-with-egress subnets (2 AZs) for Lambda, RDS, Proxy | matches the curriculum and its checks; any AWS service reachable without one endpoint per service (removes R-09); simple | NAT cost runs 24/7; outbound internet path exists; single-AZ NAT is a single point of failure (acceptable for learning) |
| B | Keep ADR-005: isolated subnets + `secretsmanager` / `bedrock-runtime` endpoints | no internet path, closest to "isolated VPC" in G2 | deviates from the curriculum; every new AWS service needs an endpoint |
| C | A for Lambda + separate isolated subnets for RDS/Proxy | data tier has no route out; still matches the curriculum | 4 private subnets, slightly more config |

If A or C is accepted, ADR-005 is rewritten and ARCHITECTURE.md §4 updated before INF-02 starts.

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
`docker-compose.yml` runs 17. Version 14 is the oldest supported major on RDS and is the first to leave standard
support (paid Extended Support afterwards — dates to be confirmed in ARCH-01). Options: (a) 14 exactly as written;
(b) newest version supported by RDS Proxy and pgvector, deviation noted in the Week 1 report; (c) 14 now, upgrade as
a separate task later. Whatever is chosen, local Docker and Testcontainers use the same major.

### <a id="q-10"></a>Q-10 — Code of the Week 1 Lambda functions

Curriculum step S5 asks for three *empty* functions (Admin, Chatbot, Sync) and S6 for `SELECT 1` from Admin.
The planned code is one Spring Boot artifact with SnapStart (ADR-002), but the draft has never compiled (R-04,
BE-00 in review).

| Option | Meaning |
|---|---|
| **A (recommended)** | Week 1 handlers are small plain-Java classes in `backend` (no Spring context): `admin` runs `SELECT 1` via JDBC with credentials from Secrets Manager; `chatbot` and `sync` only log and return. Replaced by the Spring handlers in M1/M3 |
| B | Wait for BE-00 and deploy the Spring artifact with all three handlers from the start |
| C | Inline/placeholder code defined in IaC only; `SELECT 1` in a separate throw-away function |

### <a id="q-11"></a>Q-11 — "AWS SDK v3 configured locally"

"AWS SDK v3" is the AWS SDK for JavaScript. The backend uses the AWS SDK for Java 2.x (no Java v3 exists); the
frontend uses Amplify, which uses the JS SDK v3 internally. Recommendation: accept W1-G3 as (1) AWS CLI v2 profile
works and (2) both SDKs resolve the same profile — a one-off check with the Java SDK default credential chain and
with `@aws-sdk/client-sts` (Node), recorded in OPS-05. Alternative: Java SDK only, deviation noted.

---

## 2. Risk register

Scale: Likelihood / Impact — Low · Medium · High.

| ID | Risk | L | I | Mitigation | Watched by | Status |
|---|---|---|---|---|---|---|
| R-01 | Spring Boot cold start in Lambda is 4–8 s | High | Medium | SnapStart, arm64, priming hooks, lazy beans; measure before/after | BE-12, INF-05 | Open |
| R-02 | Cognito PostConfirmation trigger times out (5 s hard limit) on a cold start → sign-up fails for the user | High | High | SnapStart on `sync` and trigger bound to the published alias; minimal Spring context; fallback: plain handler without Spring or provisioned concurrency = 1 | BE-04, BE-12, INF-05, OPS-03 | Open |
| R-03 | Version incompatibility: `aws-serverless-java-container-springboot4` 3.0.x is built for Spring Boot 4.0.x | Medium | Medium | Pin Spring Boot 4.0.x (ADR-002); upgrade only as a dedicated task | BE-00 | Open |
| R-04 | Draft code was written before the plan and never compiled (no Maven access at authoring time) | High | Medium | Treat as untrusted draft; BE-00 / FE-00 review with green build before any use | BE-00, FE-00 | Open |
| R-05 | Titan Text Embeddings v2 unavailable or not enabled in the chosen region | Medium | High | Check model access during Q-03/ARCH-02 before M1 starts | ARCH-02, INF-07, BE-07 | Open |
| R-06 | Cost of an idle stack (RDS Proxy, interface endpoints, RDS) | High | Medium | AWS Budgets alert; stop/destroy scripts; estimate monthly cost | ARCH-02, OPS-04, INF-03 | Open |
| R-07 | RDS Proxy may not support the newest PostgreSQL major version | Medium | Medium | Verify supported engine versions before INF-03; fall back to the newest supported major (e.g. 16) | INF-03 | Open |
| R-08 | SnapStart restores stale state (open DB connections, cached credentials, random seeds) | Medium | High | No DB connections during init (Hikari `minimum-idle=0`), refresh secrets after restore, CRaC `afterRestore` hooks | BE-03, BE-12, INF-05 | Open |
| R-09 | Isolated subnets have no internet: any AWS service without a VPC endpoint times out at runtime | Medium | Medium | Every new AWS dependency requires an endpoint (ARCH review); integration test in dev for each call path | INF-02, INF-07 | Open |
| R-10 | Double-wrapped or unparsable logs when Lambda JSON log format meets app-level JSON | Medium | Low | Spike OBS-01 before standardising the log format (ADR-012) | OBS-01 | Open |

---

## 3. Closed items

| ID | Resolution | Date | Decided by |
|---|---|---|---|
| — | — | — | — |
