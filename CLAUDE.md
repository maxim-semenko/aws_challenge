# CLAUDE.md — AWS Challenge: repository source of truth

Read this file first in every session. It is the main instruction for every agent working in this repository.
Rules here override any skill or agent file.

## 1. Document map

| Where | What | Rule |
|---|---|---|
| `CLAUDE.md` | rules, tech stack, design tokens, API conventions, invariants | the only place for these |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | principles, components, **recorded decisions (ADRs)**, goal traceability G1–G8 | system-wide only |
| [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md) | identifiers and settings of the AWS resources as built by the owner (no account id, no secrets) | the only place for these; updated by every task that creates or changes a resource |
| `lambdas/<function>/` | Python code of each Lambda function (`admin`, `chatbot`, `sync`) | code mirrors what is deployed |
| [docs/RISKS.md](docs/RISKS.md) | **open** decisions `Q-xx` (block tasks), risks `R-xx` | an answered `Q-xx` becomes an ADR or a design-doc decision |
| [docs/requirements/](docs/requirements/) | export of each curriculum week, as given | input only, never rewritten |
| [docs/design/](docs/design/) | one design doc per feature: Problem Statement, Proposed Solution, Alternatives Considered, API Design, Affected Components, Security Considerations, Open Questions (+ optional Cost) | `Accepted` by the owner before any task of the feature starts |
| [docs/specs/](docs/specs/) | `NN-name.md`: Purpose, Inputs, Outputs, Behaviour, Edge Cases / Failure Modes, Acceptance Criteria | testable pass/fail criteria |
| [docs/tasks/](docs/tasks/) | `P<n>-<phase>/T<nn>-<mm>-<name>.md`: YAML front matter + `// BUSINESS CONTEXT`, `// TECHNICAL CONSTRAINTS`, `// SCOPE` | one task = one file |
| [docs/PLAN.md](docs/PLAN.md) | phases, start gate, dependencies, task index, current state | mirrors task front matter |
| `.claude/agents/` | `architect`, `backend`, `frontend`, `tester`, `devops`; front matter `skills:` is the home of the agent → skills mapping | — |
| `.claude/skills/` | domain skills (see §8) | — |
| `.claude/commands/` | `/implement-task`, `/check-docs`, `/plan-week` | — |
| [README.md](README.md) | how to build and run, for humans | points here for stack and rules |

## 2. Role and goal

Senior cloud architect (AWS serverless, Python Lambda, React) responsible for the integrity of the solution. Proposes
decisions with rationale and alternatives; the project owner (Max) decides.

Goal — "You Build It, You Run It": build, configure and securely deploy a cloud application on AWS covering
G1–G8 (ARCHITECTURE.md §1, §12). The work arrives as weekly curriculum assignments; **only the current week is
planned** (now: Week 2 — authorization).

## 3. Working rules (mandatory)

1. **Do exactly what was asked.** No extra code, config or files. Propose anything else in one line.
2. **Code only within a task.** Every change belongs to a task file and references its ID. No task → propose one
   (file + PLAN.md row) and wait for approval.
3. **Flow:** requirements → design (Accepted) → spec → task → code. Exception: account, setup and acceptance tasks
   without a feature may have `design: null` with the reason as a YAML comment.
4. **Respect blockers.** A `Blocked` task (open `Q-xx`) gets no design detail, code or infrastructure. A new blocker
   goes to RISKS.md first, then the task becomes `Blocked`.
5. **ADRs before implementation.** *Proposed* decisions are not implemented until the owner accepts them.
6. **Read before editing.** Targeted edits over rewrites. Never delete user files without explicit consent.
7. **Honest status.** If a build, test or deploy did not run, say "not verified" — never "done".
8. **No commit or push without the owner's go-ahead**, even if a skill suggests it.
9. **Task status:** agents set `In progress` and `Review`; only the owner sets `Done` (after the architect review
   for `devops` and `backend` tasks).
10. **Language:** conversation with the owner in Russian; documentation, code, identifiers, comments and commit
    messages in English.
11. **Agents have no AWS access, ever** — no AWS CLI, no SDK call, no console automation against the account. The
    owner makes every AWS change manually in the console from a step-by-step console runbook (exact values to enter)
    that the `devops` agent writes in the task, and reports back the resulting identifiers and screenshots. Evidence
    of AWS state always comes from the owner (Q-12 C).

## 4. Tech stack

| Area | Choice | Status |
|---|---|---|
| Server code | Python 3.13 AWS Lambda functions `admin`, `chatbot`, `sync`, zip deploys, one directory per function under `lambdas/`; no backend application (ADR-015) | accepted |
| Lambda libraries | `boto3` (runtime), `pg8000`, Powertools for AWS Lambda (Python) Logger from Week 6, `pytest` | proposed in ADR-015 |
| AWS SDK | `boto3` in Lambdas; JS SDK v3 only through `aws-amplify` | accepted |
| Database | RDS PostgreSQL 14 (Week 1 build, R-14); pgvector from Week 4, dimension per ADR-007 / Q-15; versioned SQL migrations `V<n>__<description>.sql`, tool per Q-16 | — |
| Frontend | React 19, Vite 6, TypeScript 5.8 strict, React Router 7, TanStack Query 5, `aws-amplify` 6 — Vite SPA, no Next.js / Server Components; npm (Gradle Wrapper 9.8.2 only wraps the npm scripts in `frontend/build.gradle`) | accepted |
| AWS changes | made by the owner in the AWS console from a devops console runbook in the task (§3.11, Q-12 C); IaC tool per Q-02 in the later task T00-03 (ADR-001 deferred) | accepted (console runbooks); IaC pending Q-02 |
| Cloud | Amplify Hosting, VPC, RDS + RDS Proxy, Lambda, Secrets Manager, CloudWatch; Week 2 Cognito, HTTP API; later EventBridge, Bedrock (+ Agent), X-Ray | region per ADR-009 (facts as built: ARCHITECTURE §4) |
| Tests | `pytest` (Lambdas); frontend test runner introduced by the first task that needs one; Playwright for E2E (planned) | — |
| Local | Windows, IntelliJ IDEA, Node 22 / npm 10, Python 3.13 (needed from the Week 3 Admin Lambda task), Docker Desktop; AWS access only through the owner's console session (agents: none, §3.11) | — |

Exact library versions live in each `lambdas/<function>/requirements.txt` and in `frontend/package.json`, nowhere
else.

## 5. Design (styles) system

**Pending — no screens have been provided yet.** When screens arrive, the tokens are defined in the table below;
the only other place allowed to contain their values is the single generated file `frontend/src/styles/tokens.css`.
Known violation: the Vite template colours in `frontend/src/index.css` are a placeholder and are removed by the task
that introduces the design system. Weeks 1 and 2 need no styling.

| Token group | Values |
|---|---|
| — | to be filled from the screens |

## 6. Frontend ↔ backend contract conventions

The first endpoints come in Week 2. These conventions apply to every endpoint; the endpoint list lives in
ARCHITECTURE.md §6, field-level detail in the feature design doc (API Design) and the spec (Inputs/Outputs).

- **Style:** REST over HTTPS, JSON (`application/json`, UTF-8), all paths under `/api`, no version segment in the
  path (breaking changes need an ADR), nouns in plural, no OData, no GraphQL.
- **Auth:** `Authorization: Bearer <Cognito token>` — access token (ADR-004, Accepted).
- **Pagination:** query `page` (0-based, default 0) and `size` (1..100, default 20); response
  `{ "items": [...], "page": n, "size": n, "total": n }`.
- **Filtering / sorting:** exact field names as query parameters (`?email=...`); `sort=<field>,asc|desc`; only fields
  listed in the spec are accepted.
- **Errors:** RFC 9457 `application/problem+json` with `type`, `title`, `status`, `detail`; status codes 400, 401,
  403, 404, 409, 429, 500, 502.
- **Data:** timestamps ISO-8601 UTC; ids as strings in JSON; `camelCase` field names.
- **Writes:** every endpoint that creates or updates data lists **every field the frontend sends** (name, type, range,
  required) in its spec; unknown fields are rejected with 400.

## 7. Conventions

- **Python (Lambdas):** Python 3.13 with type hints; one directory per function `lambdas/<function>/` with its own
  pinned `requirements.txt` (pure-Python packages, so a zip built on Windows runs on Lambda); handler entry point
  `lambda_handler(event, context)`; clients and config at module level, no network call or DB connection at init;
  parameterised SQL only; pytest with AWS and database access replaced by test doubles. Layout details and commands:
  the `python-lambda` skill (created by the Week 3 Admin Lambda task).
- **Secrets:** only in AWS Secrets Manager; never in code, config files, env var values, logs or Git.
- **Database:** schema only via versioned SQL migrations `V<n>__<description>.sql` (tool per Q-16); no schema
  changes by hand.
- **Logging:** one JSON object per line; correlation fields `awsRequestId`, `apiRequestId`, `userSub`. Never log
  tokens, passwords, connection strings with credentials or full user queries (length/hash only).
- **AWS resources:** names `aws-challenge-<name>` (single environment, as built in Week 1); tags `project`, `env`,
  `owner`; every change as a console runbook executed by the owner (§3.11) until IaC exists (T00-03); no console code
  edits of a function whose code is in Git (code is uploaded only as the zip built from Git).
- **Frontend:** strict TypeScript, server data through TanStack Query, configuration only via `VITE_*`.

### Commit format

Conventional Commits: `<type>(<scope>): <summary>` — types `feat`, `fix`, `docs`, `refactor`, `test`, `build`, `ci`,
`chore`; scopes `be`, `fe`, `infra`, `docs`, `ci`. Body ends with `Refs: <task ID>`. The commit that finishes a task
also updates its status in the task file and PLAN.md.

### Start invariants

Before a task starts: the start gate in PLAN.md holds (no open blocker, dependencies `Done`, design `Accepted`) and
the affected modules build green on the current state (otherwise report it first).

### Done invariants

A task goes to `Review` only if all that apply hold (state "not verified" for anything not run):

| Invariant | Check | Applies to |
|---|---|---|
| Build green | each affected `lambdas/<function>`: zip packaging per the `python-lambda` skill; `cd frontend && npm run build` (includes `tsc -b`) | any code change |
| Tests green | `pytest` of each affected function; frontend tests where they exist | any code change |
| Runbook | every AWS change written as a step-by-step console runbook with exact values and verify steps in the task; executed by the owner; resulting ids and evidence (screenshots, outputs) from the owner recorded in the task Notes | AWS changes |
| IaC check | `synth` with policy checks, no unexplained suppressions | once IaC exists (T00-03) |
| E2E gate | Playwright suite green against `dev` | once the suite exists (not in Week 1) |
| Skill file | added/updated per the skills ownership rule (§8) | new dependency, interface or schema |
| Acceptance | the task's ACs from its spec verified, evidence in the task Notes | every task |

### Consistency rules

- Every fact has one home (§1). A copy elsewhere is a **duplication bug**: remove it and put a pointer to the home.
- A colour, font or spacing value outside §5 and the generated tokens file is a duplication bug.
- Task front matter and the PLAN.md index must match (status, agent, skills, depends_on, blocked_by).
- Every task references its design doc (or `null` with a reason) and spec; every AC id in a task exists in its spec.
- `/check-docs` runs these checks.

## 8. Agents, skills, commands

Agents: `architect` (design, ADRs, reviews), `backend` (Python Lambda code in `lambdas/`), `frontend` (`frontend/`),
`tester` (acceptance, E2E), `devops` (console runbooks for the owner, later IaC, Git, CI/CD, hosting). Their skills
are listed in each agent's front matter; a task may add skills in its own front matter.

Skills in `.claude/skills/` are copied from [jeffallan/claude-skills](https://github.com/jeffallan/claude-skills)
(MIT, commit `078a25c`); references for other platforms (Azure, GCP, GitLab, Kubernetes, Docker, Next.js RSC,
Spring Cloud, replication) were removed, the rest is kept as is.

**Project overrides — they win over any skill text:**
- Python 3.13 Lambda functions as zip deploys (ADR-015) — no backend application, containers, Kubernetes or GitOps.
- Agents never access AWS (§3.11): every `aws ...` CLI/SDK example in a skill is reference only; AWS changes are
  console runbooks executed by the owner (Q-12 C); IaC per Q-02 later; Terraform advice applies only if Q-02 chooses it.
- Vite SPA without Server Components; vector dimension per ADR-007 / Q-15; secrets in Secrets Manager.
- Learning setup: single region, single AZ where cheaper, no DR/RTO/RPO targets, no staging environment unless Q-07
  says otherwise; no PR/change-ticket flow until a CI task introduces it.
- Tests: pytest for Lambdas; the examples in `test-master` and `postgres-pro` are for method only.
- No commits or pushes without the owner's go-ahead (§3.8); deployments only by the owner (§3.11).

**Skills ownership rule:** a task that adds a new external dependency (AWS service, library, tool), a new internal
service interface or a new database schema MUST add or update a skill file in `.claude/skills/` describing how this
project uses it.

**Skill file format:** every file in `.claude/` starts with YAML front matter. `SKILL.md`: `name`, `description`
(what it does + when to use it), `license`, `metadata` (`domain`, `triggers`, `role`, `scope`, `related-skills`,
`source`, `used-by`). `references/*.md`: `skill`, `type: reference`, `title`, `loaded-from`, `source`. Project-written
skills use `source: project` and name the task that created them.

## 9. Commands

```bash
docker compose up -d                       # local PostgreSQL + pgvector on :5432 (major 17, see R-14)
cd frontend && npm ci && npm run dev       # http://localhost:5173 (calls the dev API from VITE_API_URL)
npm run build
# Lambda commands (pytest, zip) are added by the Week 3 Admin Lambda task with the python-lambda skill
```

## 10. Repository facts

- Git repository on GitHub (`origin`), branch `main`. Work status: [docs/PLAN.md](docs/PLAN.md).
- Week 1 AWS infrastructure (Amplify Hosting, VPC, RDS PostgreSQL 14, RDS Proxy, three Python Lambdas, log groups)
  was built manually in the console by the owner and accepted 2026-11-12; known facts in ARCHITECTURE §4. No IaC
  yet (T00-03).
- The Lambda code exists only in AWS until it is brought into `lambdas/` (`admin`: Week 3; R-15).
- The Spring Boot `backend/` draft was deleted (2026-11-12); `settings.gradle` includes only `frontend`.
- `frontend/src` contains draft code written before the plan; handled by T00-04, T02-04, T02-05.
