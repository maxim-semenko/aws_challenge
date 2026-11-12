# PLAN.md — Delivery Plan

Related: [CLAUDE.md](../CLAUDE.md) · [ARCHITECTURE.md](ARCHITECTURE.md) · [RISKS.md](RISKS.md) ·
[requirements/](requirements/) · [design/](design/) · [specs/](specs/) · [tasks/](tasks/)
Last updated: 2026-11-12

## How the plan works

- **Flow per curriculum week:** requirements export (`requirements/`) → feature design doc (`design/`, Accepted by the
  owner) → specs (`specs/NN-name.md`) → tasks (`tasks/P<n>-<phase>/T<nn>-<mm>-<name>.md`) → this index.
  Only the current week is planned; nothing is written for weeks whose requirements have not arrived.
- **Task file** = YAML front matter (`id`, `title`, `phase`, `status`, `agent`, `skills`, `depends_on`, `blocked_by`,
  `design`, `spec`, `acceptance`) + three layers `// BUSINESS CONTEXT`, `// TECHNICAL CONSTRAINTS`, `// SCOPE`
  + Definition of Done + Notes. The front matter is the source of truth; this index mirrors it.
- **Statuses:** `Todo` · `In progress` · `Review` · `Done` · `Blocked`. `Blocked` only for an open item in
  [RISKS.md](RISKS.md); waiting for a dependency is `Todo`.
- **Start gate:** a task starts when its `blocked_by` is empty, all `depends_on` are `Done` and its design doc is
  `Accepted`. The `agent` named in the task does the work with the listed `skills`; `architect` reviews every
  `devops` and `backend` result before `Done`.
- **AWS changes** are AWS CLI commands recorded as a replayable runbook in the task Notes, shown to the owner before
  they run (Q-12 C, CLAUDE.md §3.8); IaC comes with T00-03.
- A status change goes to the task file and this index in the same commit. New work = new task file + a row here.

## Phases

| Phase | Week | Outcome | Design | Specs |
|---|---|---|---|---|
| **P0-foundation** | 1 | account and local access, Git repository, SPA that builds and renders without config; later: IaC import (T00-03) | [spa-hosting](design/spa-hosting.md), [backend-foundation](design/backend-foundation.md) | [01](specs/01-spa-delivery.md), [02](specs/02-database-connectivity.md), [03](specs/03-local-aws-access.md) |
| **P1-environment** | 1 | SPA on Amplify/CloudFront; VPC, RDS, RDS Proxy; three Python Lambdas with logs; `SELECT 1` through the proxy — built manually by the owner | same | same |
| **P2-authorization** | 2 | Cognito User Pool + own Amplify Auth screens, personal page from Cognito attributes, HTTP API with JWT authorizer, `admin` group, Admin Lambda code in Git | [authentication](design/authentication.md), [api-gateway-auth](design/api-gateway-auth.md) | [04](specs/04-user-registration-and-sign-in.md), [05](specs/05-protected-api.md) |
| P3+ | 3+ | planned when the next week's requirements arrive (curriculum overview: ARCHITECTURE §1.1) | — | — |

Week 1 (built manually; T01-06 verifies and records the build):

```mermaid
flowchart LR
    T0101[T01-01 network] --> T0102[T01-02 RDS + Proxy]
    T0102 --> T0104[T01-04 Lambdas + logs]
    T0002[T00-02 Git] --> T0105[T01-05 Amplify hosting]
    T0004[T00-04 SPA build] --> T0105
    T0106[T01-06 acceptance + record of the build] --> T0003[T00-03 IaC import, later]
```

Week 2:

```mermaid
flowchart LR
    T0001[T00-01 account] --> T0201[T02-01 User Pool]
    T0104[T01-04 Lambdas] --> T0202[T02-02 admin handler in Git]
    T0104 --> T0203
    T0201 --> T0203[T02-03 HTTP API + JWT, deploy, first admin]
    T0202 --> T0203
    T0004[T00-04 SPA build] --> T0204[T02-04 auth screens]
    T0201 --> T0204
    T0203 --> T0205[T02-05 personal page + API client]
    T0204 --> T0205
    T0203 --> T0206[T02-06 acceptance]
    T0205 --> T0206
```

Lanes: **devops** T02-01 → T02-03 · **backend** T02-02 · **frontend** T02-04 → T02-05 · **tester** T02-06 at the end.

## Current state (2026-11-12)

**Week 1** was built manually in the AWS console by the owner. The build tasks are in `Review`; T01-06 (tester,
read-only) verifies specs 01–03 and records the actual values that the closed decisions Q-01, Q-03, Q-04, Q-07,
Q-08, Q-09, Q-10, Q-11 refer to. IaC ACs (AC-01.4, AC-02.9) are deferred to T00-03. The owner sets `Done` from that
evidence. T00-04 (SPA build) is still `In progress` (see its Notes). T01-03 (Java
handlers) was deleted as obsolete (ADR-015).

**Week 2** is re-scoped to authorization only (owner decisions 2026-11-12): 6 tasks in P2-authorization, both design
docs `Draft`. To start: the owner accepts [authentication](design/authentication.md) and
[api-gateway-auth](design/api-gateway-auth.md) (with ADR-004, still Proposed), answers Q-14 (blocks T02-01, T02-04),
and sets the Week 1 dependencies T00-01, T00-04, T01-04 to `Done`. User sync to PostgreSQL, the users table and
migrations moved to Week 3 with the curriculum.

## Task index

### P0-foundation

| ID | Task | Agent | Skills | Depends on | Blocked by | Design | Spec | Status |
|---|---|---|---|---|---|---|---|---|
| [T00-01](tasks/P0-foundation/T00-01-aws-account-and-local-access.md) | AWS account, budget and local CLI/SDK access | devops | cloud-architect | — | — | — | 03 | Review |
| [T00-02](tasks/P0-foundation/T00-02-git-repository.md) | Put the project under Git and push to the remote | devops | devops-engineer | — | — | spa-hosting | 01 | Review |
| [T00-03](tasks/P0-foundation/T00-03-iac-skeleton.md) | Codify the manually built resources in IaC | devops | cloud-architect, devops-engineer | T01-06 | Q-02 | backend-foundation | 01, 02 | Blocked |
| [T00-04](tasks/P0-foundation/T00-04-spa-build.md) | SPA builds and renders without Cognito/API configuration | frontend | react-expert | — | — | spa-hosting | 01 | In progress |

### P1-environment

| ID | Task | Agent | Skills | Depends on | Blocked by | Design | Spec | Status |
|---|---|---|---|---|---|---|---|---|
| [T01-01](tasks/P1-environment/T01-01-network.md) | Network stack: VPC, subnets, NAT, security groups | devops | cloud-architect | — | — | backend-foundation | 02 | Review |
| [T01-02](tasks/P1-environment/T01-02-database-and-proxy.md) | Data stack: RDS PostgreSQL, secret, RDS Proxy | devops | cloud-architect, postgres-pro | T01-01 | — | backend-foundation | 02 | Review |
| [T01-04](tasks/P1-environment/T01-04-lambda-functions.md) | Compute: three functions, roles, log groups | devops | cloud-architect | T01-02 | — | backend-foundation | 02 | Review |
| [T01-05](tasks/P1-environment/T01-05-spa-hosting.md) | Hosting stack: Amplify app connected to Git | devops | cloud-architect, devops-engineer | T00-02, T00-04 | — | spa-hosting | 01 | Review |
| [T01-06](tasks/P1-environment/T01-06-week-1-acceptance.md) | Week 1 acceptance check and record of the manual build | tester | test-master | — | — | — | 01, 02, 03 | Todo |

### P2-authorization

| ID | Task | Agent | Skills | Depends on | Blocked by | Design | Spec | Status |
|---|---|---|---|---|---|---|---|---|
| [T02-01](tasks/P2-authorization/T02-01-cognito-user-pool.md) | Cognito User Pool, SPA app client and group admin | devops | cloud-architect | T00-01 | Q-14 | authentication | 04 | Blocked |
| [T02-02](tasks/P2-authorization/T02-02-admin-api-handler.md) | Admin Lambda in Git (Python): GET /api/me and GET /api/admin/ping | backend | test-master | T01-04 | — | api-gateway-auth | 05 | Todo |
| [T02-03](tasks/P2-authorization/T02-03-http-api-jwt.md) | HTTP API with Cognito JWT authorizer, routes, CORS, access logs; deploy admin; first admin | devops | cloud-architect | T01-04, T02-01, T02-02 | — | api-gateway-auth | 05, 04 | Todo |
| [T02-04](tasks/P2-authorization/T02-04-auth-screens.md) | Amplify Auth config, sign-up / confirm / sign-in / sign-out screens, route guard | frontend | react-expert | T00-04, T02-01 | Q-14 | authentication | 04 | Blocked |
| [T02-05](tasks/P2-authorization/T02-05-personal-page.md) | Personal page from Cognito attributes; API client with the access token; role from GET /api/me | frontend | react-expert | T02-03, T02-04 | — | authentication | 04, 05 | Todo |
| [T02-06](tasks/P2-authorization/T02-06-week-2-acceptance.md) | Week 2 acceptance check | tester | test-master | T02-03, T02-05 | — | — | 04, 05 | Todo |

## Change log

| Date | Change |
|---|---|
| 2026-10-22 | First version with 48 tasks inline |
| 2026-10-23 | One file per task in `docs/tasks/`, open questions moved to RISKS.md |
| 2026-11-05 | Restructured to the Agentic Coding layout (requirements → design → specs → phased tasks). Only Week 1 is planned: 10 tasks in P0/P1. The 48 speculative tasks for later milestones were deleted; backup of the old `docs/` in `%TEMP%\aws_challenge_backup_2026-11-05\docs-before-restructure.zip` |
| 2026-11-12 | Week 2 (Authorization) planned: design docs authentication, api-gateway-auth; specs 04–06; 9 tasks in P2-authorization; Q-12…Q-14, R-11…R-13, ADR-013, ADR-014 added |
| 2026-11-12 | Owner decisions applied. **D1** ADR-015 (Accepted): Python 3.13 Lambdas, no backend application; ADR-002 superseded; Q-10, Q-13 closed. **D2** backend draft deleted by the owner; R-04 closed; CLAUDE.md, README, agents updated. **D3** Q-12 = C (AWS CLI runbooks, IaC later in T00-03); Week 1 recorded as built manually: Q-01, Q-03, Q-04, Q-07, Q-08, Q-09, Q-10, Q-11 closed "decided by the build" (values recorded by T01-06), Q-02 deferred; Week 1 build tasks → `Review`; T01-03 deleted; T00-03 re-scoped to the IaC import. **D4** curriculum Weeks 3–6 recorded in ARCHITECTURE §1.1; ADR-011 rejected (EventBridge required), ADR-010 superseded, Q-06 closed; Q-15 (1536 dims) and Q-16 (migrations) added; R-14, R-15 added. **D5** Week 2 re-scoped: spec 06 and the sync/migrate/schema tasks deleted (moved to Week 3); tasks renumbered T02-01…T02-06; ADR-003, ADR-013 (revised), ADR-014 Accepted |
