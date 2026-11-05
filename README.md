# AWS Challenge

Learning project "You Build It, You Run It": a React SPA on Amplify Hosting with a serverless Java backend on AWS
(Lambda in a VPC, RDS Proxy → PostgreSQL + pgvector, later Cognito, HTTP API and Bedrock), structured logs in
CloudWatch.

| Read | For |
|---|---|
| [CLAUDE.md](CLAUDE.md) | rules, tech stack, conventions — for people and AI agents |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | architecture and decisions |
| [docs/PLAN.md](docs/PLAN.md) | current week, tasks and their status |

```
aws_challenge/
├── amplify.yml          Amplify Hosting build spec (monorepo, appRoot = frontend)
├── docker-compose.yml   local PostgreSQL + pgvector
├── backend/             Spring Boot draft (not accepted yet, does not compile — see docs/RISKS.md R-04)
└── frontend/            React SPA
```

## Run locally

```bash
docker compose up -d                       # PostgreSQL + pgvector on :5432

cd frontend
cp .env.example .env.local                 # leave values empty to run without Cognito
npm ci
npm run dev                                # http://localhost:5173
```

Build and test commands per module: [CLAUDE.md §9](CLAUDE.md#9-commands).
