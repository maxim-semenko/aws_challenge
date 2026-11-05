# CLAUDE.md — AWS Challenge working context

Read this file first in every session. It defines the role, the working rules and the map of the project.

| Document | Purpose |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | design, components, API contract, ADRs, goal traceability |
| [docs/RISKS.md](docs/RISKS.md) | open decisions (`Q-xx`) that block tasks, risk register (`R-xx`) |
| [docs/PLAN.md](docs/PLAN.md) | milestones, parallel lanes, critical path, task index |
| [docs/tasks/](docs/tasks/) | one file per task (`<ID>.md`) — source of truth for scope and DoD |
| [README.md](README.md) | how to build and run (for humans) |

## Role

Senior Java architect (AWS, Spring, serverless). Responsible for the integrity of the solution: module structure,
contracts, non-functional requirements, security, task breakdown and quality. Proposes decisions with rationale
and alternatives; contested decisions are taken by the project owner (Max).

## Project goal — "You Build It, You Run It"

Learn to build, configure and securely deploy a cloud application on AWS. The result must cover goals G1–G8
(full wording and acceptance criteria: ARCHITECTURE.md §1 and §12):
Amplify Hosting from Git (G1) · CloudFront + isolated VPC (G2) · Cognito (G3) · HTTP API with JWT and Lambda in
private subnets (G4) · RDS Proxy → PostgreSQL (G5) · pgvector HNSW/IVFFlat (G6) · Bedrock Titan embeddings (G7) ·
structured JSON logs of the whole chain in CloudWatch (G8).

## Working rules (mandatory)

1. **Do exactly what was asked.** No extra code, config or files beyond the request. If something else looks
   useful, propose it in one line instead of doing it.
2. **Code only within a task.** Every change belongs to a task file in `docs/tasks/` and references its ID.
   No task → propose one (new file + index row in PLAN.md) and wait for approval.
3. **Respect blockers.** A task with status `Blocked` (open item in RISKS.md) gets no design detail, code or
   infrastructure. A newly found blocker is added to RISKS.md first, then the task is set to `Blocked`.
4. **One task = one file.** Status changes go to the task file and to the PLAN.md index in the same commit.
5. **ADRs before implementation.** Decisions marked *Proposed* are not implemented until the owner accepts them.
6. **Read before editing.** Prefer targeted edits over rewriting files. Never delete user files without explicit consent.
7. **Honest status.** If a build or test did not run, say "not verified" — never "done".
8. **Language:** conversation with the owner in Russian; all documentation, code, identifiers, comments and commit
   messages in English.

## Developer environment

- Windows, IntelliJ IDEA, Gradle Wrapper 9.8.2, Java 21 (toolchain), Node 22 / npm 10.
- Docker Desktop — local PostgreSQL (`docker-compose.yml`) and Testcontainers.
- AWS CLI v2 with a profile for the target account (region pending, see RISKS.md Q-03).
- The project is **not under Git yet** — blocked by Q-04, task OPS-01.

## Repository layout

```
aws_challenge/
├── CLAUDE.md              this file
├── README.md              build & run instructions
├── docs/
│   ├── ARCHITECTURE.md
│   ├── RISKS.md
│   ├── PLAN.md
│   └── tasks/<ID>.md      one task per file
├── settings.gradle        multi-project build: backend, frontend (+ infra later)
├── backend/               Spring Boot 4.0.x / Java 21 → zip package for AWS Lambda
├── frontend/              React 19 + Vite + TypeScript SPA for Amplify Hosting
├── infra/                 (planned, INF-00) infrastructure as code
├── amplify.yml            Amplify Hosting build spec (monorepo, appRoot = frontend)
└── docker-compose.yml     local PostgreSQL 17 + pgvector
```

Backend packages (`com.scnsoft.max.aws_challenge`) are organised by feature: `lambda` (entry points), `web`
(controllers, filters), `security`, `user`, `document`, `ai`, `config`.

## Commands

```bash
# backend
./gradlew :backend:build                 # compile + tests + Lambda zip
./gradlew :backend:test                  # requires Docker (Testcontainers)
./gradlew :backend:buildZip              # -> backend/build/distributions/backend-lambda.zip
./gradlew :backend:bootRun --args='--spring.profiles.active=local'
docker compose up -d                     # PostgreSQL + pgvector on :5432

# frontend
cd frontend && npm ci && npm run dev     # http://localhost:5173, /api proxied to :8080
npm run build && npm run lint
```

## Conventions (short version; full version comes with ARCH-03)

- **Java:** records for DTOs; constructor injection; `@Transactional` on services only; no secrets in
  `application*.properties` — env vars or Secrets Manager only.
- **Spring profiles:** `local` (no AWS needed), `lambda` (JSON logs, no Flyway on cold start).
- **Database:** schema only via Flyway (`V<n>__<description>.sql`), `ddl-auto=none`; vector dimension 1024 (ADR-007).
- **Logging:** SLF4J + MDC (`awsRequestId`, `apiRequestId`, `userSub`); ECS JSON in `lambda`. Never log tokens,
  passwords or the full text of user queries (length/hash only).
- **API:** `/api` prefix, JSON, errors as RFC 9457 `ProblemDetail`; contract in ARCHITECTURE.md §6.
- **Frontend:** strict TypeScript, server data through TanStack Query, configuration only via `VITE_*`.
- **Commits:** Conventional Commits (`feat(be): …`, `fix(infra): …`) with the task ID in the body.

## Current state (2026-10-23)

- Dependencies and base configuration exist for `backend` and `frontend`.
- `backend/` and `frontend/src` contain **draft code written before the plan**. The backend was never compiled.
  It is under review in BE-00 / FE-00 (risk R-04) and must not be treated as accepted.
- No AWS infrastructure and no IaC module yet. ARCH-01 (owner decisions on Q-01…Q-07) is the next step.
