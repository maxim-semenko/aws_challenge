# AWS Challenge

Learning project "You Build It, You Run It": a React SPA on Amplify Hosting with serverless Python Lambda functions
on AWS (Lambda in a VPC, RDS Proxy → PostgreSQL, Cognito, HTTP API; later EventBridge, pgvector and Bedrock),
structured logs in CloudWatch.

| Read | For |
|---|---|
| [CLAUDE.md](CLAUDE.md) | rules, tech stack, conventions — for people and AI agents |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | architecture and decisions |
| [docs/PLAN.md](docs/PLAN.md) | current week, tasks and their status |

```
aws_challenge/
├── amplify.yml          Amplify Hosting build spec (monorepo, appRoot = frontend)
├── docker-compose.yml   local PostgreSQL + pgvector
├── frontend/            React SPA
└── lambdas/             Python Lambda functions (from T02-02; until then the code lives only in AWS)
```

## Run locally

```bash
docker compose up -d                       # PostgreSQL + pgvector on :5432

cd frontend
# optional: .env.local with the VITE_* variables (names: docs/specs/04, values: docs/ENVIRONMENT.md);
# without it the SPA runs without Cognito
npm ci
npm run dev                                # http://localhost:5173
```

Build and test commands: [CLAUDE.md §9](CLAUDE.md#9-commands).
