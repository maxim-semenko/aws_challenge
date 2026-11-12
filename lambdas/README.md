# lambdas/

Python 3.13 code of the AWS Lambda functions (ADR-015), one directory per function. The code here mirrors what is
deployed; the deployed names and settings are in [docs/ENVIRONMENT.md](../docs/ENVIRONMENT.md).

| Directory | Function | Purpose |
|---|---|---|
| `admin/` | `aws-challenge-admin` | API for the SPA: `GET /api/me`, `GET /api/admin/ping` (T02-02); admin queries from Week 3 |
| `chatbot/` | `aws-challenge-chatbot` | natural-language search through Bedrock (Week 5) |
| `sync/` | `aws-challenge-sync` | copies Cognito users into PostgreSQL (Week 3) |

Each function directory holds `lambda_function.py` (handler `lambda_function.lambda_handler`), `requirements.txt`
when it has dependencies, and `tests/` for pytest.
