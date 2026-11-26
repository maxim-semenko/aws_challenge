# lambdas/

Python code of the AWS Lambda functions (ADR-015), Python 3.12 runtime (local tests on 3.13), one directory per
function. The code here mirrors what is
deployed; the deployed names and settings are in [docs/ENVIRONMENT.md](../docs/ENVIRONMENT.md).

| Directory | Function | Purpose |
|---|---|---|
| `admin/` | `aws-challenge-admin` | `GET /admin` (users list for admins) behind the HTTP API JWT authorizer (spec 08; skill `admin-api`) |
| `chatbot/` | `aws-challenge-chatbot` | `POST /chat` for admins (Week 5, spec 12): a question with the word "sql" → Bedrock Nova Micro writes one `SELECT` (`llm.py`), validated by the `sqlglot` guard (`sql_guard.py`) and run read-only; otherwise Titan V2 embedding + pgvector top-5 (`search.py`); skill `chatbot-api` |
| `sync/` | `aws-challenge-sync` | copies Cognito users into PostgreSQL (`user_sync.py`, spec 07) with a Bedrock Titan V2 profile embedding (shared `embeddings.py`, spec 10), applies the SQL migrations in `sync/migrations/` on the owner's invoke (ADR-017) and runs the owner's vector actions `embed-missing`, `seed`, `similar` (`vectors.py`, specs 10, 11; skill `bedrock-embeddings`) |
| `post-confirmation/` | `aws-challenge-post-confirmation` | Cognito PostConfirmation trigger: publishes `UserConfirmed` to EventBridge, outside the VPC (ADR-016) |
| `shared/` | — (not a function) | copied into each zip by `package.py`: `db.py` (IAM-auth TLS connection to RDS Proxy), `embeddings.py` (Titan V2 client, sync + chatbot), `http_api.py` (JWT claims, groups, problem+json; admin + chatbot); `tests/` (incl. the shared `bedrock_stub.py` double) is never packaged |

Other files: `package.py` builds `build/lambdas/<function>.zip` (its tests: `tests/`); `requirements-dev.txt` holds
the local test tools.

Each function directory holds `lambda_function.py` (handler `lambda_function.lambda_handler`), `requirements.txt`
when it has dependencies, and `tests/` for pytest. Commands (set-up, pytest, packaging) and conventions:
[python-lambda skill](../.claude/skills/python-lambda/SKILL.md); migration rules:
[postgres-migrations skill](../.claude/skills/postgres-migrations/SKILL.md).
