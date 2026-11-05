# Spec 02 — Lambda → RDS Proxy → PostgreSQL connectivity

Requirements: [week-01](../requirements/week-01-environment.md) W1-G2, S3–S7 ·
Design: [backend-foundation](../design/backend-foundation.md)
Tasks: T00-03, T01-01, T01-02, T01-03, T01-04, T01-06

## Purpose

Prove that a function in a private subnet reaches PostgreSQL only through RDS Proxy, using credentials from Secrets
Manager, and that every function logs to CloudWatch.

## Inputs

| Name | Type | Valid range | Required |
|---|---|---|---|
| Invocation event of `admin` | JSON object | `{}`; any fields are ignored | yes |
| Invocation event of `chatbot`, `sync` | JSON object | `{}`; any fields are ignored | yes |
| `DB_PROXY_ENDPOINT` | env var, string | RDS Proxy default endpoint host name | yes (`admin`) |
| `DB_NAME` | env var, string | database name created with the instance | yes (`admin`) |
| `DB_SECRET_ARN` | env var, string | ARN of the DB secret | yes (`admin`) |

## Outputs

| Function | Structure | Guarantees |
|---|---|---|
| `admin` success | `{"result": 1, "durationMs": <int ≥ 0>}` | the query went through the proxy endpoint over TLS |
| `admin` failure | function error, message `DB_PROBE_FAILED: <reason>` | no credentials or password-bearing URL in the message or logs |
| `chatbot`, `sync` | `{"status": "ok"}` | — |
| Log line (every invocation) | one JSON object: `level`, `message`, `function`, `awsRequestId`, `durationMs`, `outcome` | in `/aws/lambda/<function>`, retention 14 days |

## Behaviour

1. `admin` is invoked.
2. It reads the secret `DB_SECRET_ARN` from Secrets Manager (reached through the network path from Q-08).
3. It opens one JDBC connection to `DB_PROXY_ENDPOINT:5432/DB_NAME` with `sslmode=require`.
4. It runs `SELECT 1`, reads the value, closes the connection.
5. It writes one JSON log line with `outcome=success` and returns the result.
6. `chatbot` and `sync` write one JSON log line and return `{"status":"ok"}`.

## Edge Cases / Failure Modes

| Case | Expected result |
|---|---|
| Secret not readable (IAM, network) | error `DB_PROBE_FAILED: secret`, log `outcome=failure`, no retry inside the function |
| Proxy unreachable / timeout (> 5 s connect) | error `DB_PROBE_FAILED: connect` |
| TLS not possible | connection refused, error `DB_PROBE_FAILED: connect`; never falls back to plain text |
| Direct connection attempt to the RDS instance endpoint | blocked by security groups (`sg-db` accepts only `sg-proxy`) |
| Cold start | completes within the 15 s timeout |
| Proxy target not yet available after deploy | error, succeeds on a later invocation |

## Acceptance Criteria

- [ ] AC-02.1 VPC has the subnet layout from the accepted Q-08 option; Lambda, Proxy and RDS have no public IP
- [ ] AC-02.2 RDS has `PubliclyAccessible=false`; `sg-db` inbound only from `sg-proxy`; `sg-proxy` inbound only from `sg-lambda`
- [ ] AC-02.3 `aws rds describe-db-proxy-targets` shows the instance as `AVAILABLE`
- [ ] AC-02.4 `admin`, `chatbot`, `sync` exist with `VpcConfig` = the private subnets + `sg-lambda`, each with its own role
- [ ] AC-02.5 `aws lambda invoke --function-name awsch-dev-admin` returns `{"result":1,…}`
- [ ] AC-02.6 RDS Proxy metric `ClientConnections` > 0 at the time of the invocation
- [ ] AC-02.7 Each function has a log group created by IaC with retention 14 days, containing the JSON log line
- [ ] AC-02.8 No secret value in code, function configuration, logs or Git
- [ ] AC-02.9 Network, Data and Compute are defined in IaC: `synth` passes with cdk-nag (no unexplained
  suppressions) and switching env/region needs no code change
