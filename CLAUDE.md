# CLAUDE.md — AWS Challenge: repository source of truth

Read this file first in every session. It is the main instruction for every agent working in this repository.
Rules here override any skill or agent file.

## 1. Document map

| Where | What | Rule |
|---|---|---|
| `CLAUDE.md` | rules, tech stack, design tokens, API conventions, invariants | the only place for these |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | principles, components, **recorded decisions (ADRs)**, goal traceability G1–G8 | system-wide only |
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

Senior Java architect (AWS, Spring, serverless) responsible for the integrity of the solution. Proposes decisions
with rationale and alternatives; the project owner (Max) decides.

Goal — "You Build It, You Run It": build, configure and securely deploy a cloud application on AWS covering
G1–G8 (ARCHITECTURE.md §1, §12). The work arrives as weekly curriculum assignments; **only the current week is
planned** (now: Week 1 — environment setup).

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
8. **No commit, push or AWS change without the owner's go-ahead**, even if a skill suggests it.
9. **Task status:** agents set `In progress` and `Review`; only the owner sets `Done` (after the architect review
   for `devops` and `backend` tasks).
10. **Language:** conversation with the owner in Russian; documentation, code, identifiers, comments and commit
    messages in English.

## 4. Tech stack

| Area | Choice | Status |
|---|---|---|
| Build | Java 21 (toolchain), Gradle Wrapper 9.8.2 — Gradle only, no Maven | accepted |
| Backend framework | Spring Boot 4.0.x in Lambda via `aws-serverless-java-container-springboot4` (ADR-002); profiles `local` (no AWS) and `lambda` | Proposed; Week 1 handlers per Q-10 |
| AWS SDK | Java 2.x (`software.amazon.awssdk`); JS SDK v3 only through `aws-amplify` | accepted |
| Database | PostgreSQL + pgvector, vector dimension 1024 (ADR-007); Flyway migrations | major version pending Q-09 (proposed 17) |
| Frontend | React 19, Vite 6, TypeScript 5.8 strict, React Router 7, TanStack Query 5, `aws-amplify` 6, oxlint — Vite SPA, no Next.js / Server Components | accepted |
| IaC | AWS CDK v2 in Java, module `infra` (ADR-001) | pending Q-02 |
| Cloud | Amplify Hosting, VPC, RDS + RDS Proxy, Lambda, Secrets Manager, CloudWatch; later Cognito, HTTP API, Bedrock | region pending Q-03 |
| Tests | JUnit 5 + Testcontainers (backend); Playwright for E2E (planned) | — |
| Local | Windows, IntelliJ IDEA, Node 22 / npm 10, Docker Desktop, AWS CLI v2 profile `awsch` | — |

Exact library versions live in `backend/build.gradle` and `frontend/package.json`, nowhere else.

## 5. Design (styles) system

**Pending — no screens have been provided yet.** When screens arrive, the tokens are defined in the table below;
the only other place allowed to contain their values is the single generated file `frontend/src/styles/tokens.css`.
Known violation: the Vite template colours in `frontend/src/index.css` are a placeholder and are removed by the task
that introduces the design system. Week 1 needs no styling.

| Token group | Values |
|---|---|
| — | to be filled from the screens |

## 6. Frontend ↔ backend contract conventions

Week 1 has no HTTP API. These conventions apply from the first endpoint on; the endpoint list lives in
ARCHITECTURE.md §6, field-level detail in the feature design doc (API Design) and the spec (Inputs/Outputs).

- **Style:** REST over HTTPS, JSON (`application/json`, UTF-8), all paths under `/api`, no version segment in the
  path (breaking changes need an ADR), nouns in plural, no OData, no GraphQL.
- **Auth:** `Authorization: Bearer <Cognito token>` — access token proposed (ADR-004, Proposed).
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

- **Java:** records for DTOs; constructor injection; `@Transactional` on services only; Spring Boot 4 test
  annotations (`@MockitoBean`, not `@MockBean`).
- **Secrets:** only in AWS Secrets Manager; never in code, `application*.properties`, env var values, logs or Git.
- **Database:** schema only via Flyway (`V<n>__<description>.sql`), `ddl-auto=none`.
- **Logging:** one JSON object per line; correlation fields `awsRequestId`, `apiRequestId`, `userSub`. Never log
  tokens, passwords, connection strings with credentials or full user queries (length/hash only).
- **AWS resources:** names `awsch-<env>-<name>`; tags `project`, `env`, `owner`; everything through IaC.
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
| Build green | `./gradlew :<module>:build` for each affected module (the `backend` draft is excluded until it is reviewed, R-04); `cd frontend && npm run lint && npm run build` | any code change |
| Tests green | unit + integration tests of the affected modules | any code change |
| CSS budget | every `frontend/dist/assets/*.css` raw file size ≤ 10 240 bytes | frontend changes |
| IaC check | `cdk synth` with cdk-nag, no unexplained suppressions | infra changes |
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

Agents: `architect` (design, ADRs, reviews), `backend` (Java code), `frontend` (`frontend/`), `tester` (acceptance,
E2E), `devops` (IaC, AWS account, Git, CI/CD, hosting). Their skills are listed in each agent's front matter; a task
may add skills in its own front matter.

Skills in `.claude/skills/` are copied from [jeffallan/claude-skills](https://github.com/jeffallan/claude-skills)
(MIT, commit `078a25c`); references for other platforms (Azure, GCP, GitLab, Kubernetes, Docker, Next.js RSC,
Spring Cloud, replication) were removed, the rest is kept as is.

**Project overrides — they win over any skill text:**
- Gradle only; Spring Boot 4 (`@MockitoBean`); Lambda zip deploys — no containers, Kubernetes, GitOps or Actuator
  health checks.
- IaC per Q-02 (proposed CDK in Java); Terraform advice applies only if Q-02 chooses Terraform.
- Vite SPA without Server Components; vector dimension 1024; secrets in Secrets Manager.
- Learning setup: single region, single AZ where cheaper, no DR/RTO/RPO targets, no staging environment unless Q-07
  says otherwise; no PR/change-ticket flow until a CI task introduces it.
- Tests: JUnit 5 + Testcontainers for Java; the JS/Python examples in `test-master` are for method only.
- No commits, pushes or deployments without the owner's go-ahead (§3.8).

**Skills ownership rule:** a task that adds a new external dependency (AWS service, library, tool), a new internal
service interface or a new database schema MUST add or update a skill file in `.claude/skills/` describing how this
project uses it.

**Skill file format:** every file in `.claude/` starts with YAML front matter. `SKILL.md`: `name`, `description`
(what it does + when to use it), `license`, `metadata` (`domain`, `triggers`, `role`, `scope`, `related-skills`,
`source`, `used-by`). `references/*.md`: `skill`, `type: reference`, `title`, `loaded-from`, `source`. Project-written
skills use `source: project` and name the task that created them.

## 9. Commands

```bash
docker compose up -d                       # local PostgreSQL + pgvector on :5432
./gradlew :<module>:build                  # one JVM module (backend draft excluded, see §7)
cd frontend && npm ci && npm run dev       # http://localhost:5173, /api proxied to :8080
npm run lint && npm run build
```

## 10. Repository facts

- No Git repository, no AWS infrastructure, no IaC module yet. Work status: [docs/PLAN.md](docs/PLAN.md).
- `backend/` and `frontend/src` contain draft code written before the plan (R-04); not accepted, the backend never compiled.
