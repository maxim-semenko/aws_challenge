# Design — Backend foundation (VPC, RDS PostgreSQL, RDS Proxy, Lambda skeleton)

Status: **Accepted** (2026-11-12, owner) — Week 1 was built manually in the AWS console (Q-12 C); the facts as built
are in [ARCHITECTURE §4](../ARCHITECTURE.md#4-network) and win where they differ from the tables below.
Requirements: [week-01](../requirements/week-01-environment.md) W1-G2, S3–S7 ·
Spec: [02-database-connectivity](../specs/02-database-connectivity.md)
Architecture: [ARCHITECTURE.md](../ARCHITECTURE.md) §3.2, §3.5, §4, §8, ADR-006, ADR-015

## Problem Statement

The functions `admin`, `chatbot` and `sync` must run in private subnets and reach PostgreSQL only through RDS Proxy,
with credentials from Secrets Manager and logs in CloudWatch.

## Proposed Solution

Built manually in the console in one environment in the region of ADR-009 (Q-03, Q-07 closed). Naming and tags per CLAUDE.md
§7. The tables below are the design; the build differs in the network (2 public subnets, S3 gateway endpoint, no NAT
gateway shown — [R-09](../RISKS.md#2-risk-register)), see ARCHITECTURE §4.

**Network (Q-08, decided by the build; the curriculum asks for 1 public subnet, 2 private subnets and a NAT).**

| Resource | Value |
|---|---|
| VPC | `10.0.0.0/16`, 2 AZs |
| Public subnet | 1 × `/24` in AZ-a, Internet Gateway, one NAT Gateway |
| Private subnets | 2 × `/24` (AZ-a, AZ-b), outbound via the NAT — Lambda, RDS Proxy, RDS |
| VPC endpoints | none in Week 1 (Secrets Manager is reached through the NAT) |

Security groups (only what is needed):

| SG | Inbound | Outbound |
|---|---|---|
| `sg-lambda` | — | 5432 → `sg-proxy`; 443 → `0.0.0.0/0` (Secrets Manager via NAT) |
| `sg-proxy` | 5432 ← `sg-lambda` | 5432 → `sg-db` |
| `sg-db` | 5432 ← `sg-proxy` | — |

**Data.** RDS for PostgreSQL **14** (curriculum S4, Q-09 closed; support deadline [R-14](../RISKS.md#2-risk-register)),
`db.t4g.micro`, single-AZ, encrypted, `PubliclyAccessible=false`, in the private subnets. Master credentials in a
Secrets Manager secret. RDS Proxy with that secret, TLS required, target = the instance.

**Compute.** Three Python functions written in the console (Q-10 closed, ADR-015), in the private subnets with
`sg-lambda`; runtime version, architecture, memory and timeout as built.

| Function | Handler behaviour | IAM role (one per function) |
|---|---|---|
| `admin` | reads the secret, opens a TLS connection to the **proxy** endpoint, runs `SELECT 1`, closes it, returns the result | `AWSLambdaVPCAccessExecutionRole` + `secretsmanager:GetSecretValue` on the DB secret |
| `chatbot` | logs one line, returns `{"status":"ok"}` | same as `admin` (S5 asks for Secrets Manager / Proxy access for all three) |
| `sync` | logs one line, returns `{"status":"ok"}` | same as `admin` |

Log groups `/aws/lambda/<function>`, retention ≥ 7 days (S7). Each invocation writes one JSON log line.

## Alternatives Considered

| Topic | Option | Verdict |
|---|---|---|
| Build method | IaC from the start (ADR-001) | not used for Week 1; IaC imports the resources later (T00-03, Q-02) |
| Network | Isolated subnets + interface endpoints, no NAT (former ADR-005) | not built; same cost, no internet path, but deviates from S3 |
| PostgreSQL | 17 (newest with long support) | not chosen; the curriculum and the build use 14 (R-14) |
| Handlers | Java (plain or Spring Boot) | superseded by ADR-015 (Python) |
| Credentials | IAM authentication to the proxy | later stage; Week 1 uses the secret |

## API Design

No HTTP API in Week 1. Function contract (direct invoke, e.g. the console Test tab):

| Function | Input event | Output |
|---|---|---|
| `admin` | `{}` (any fields ignored) | success: `{"result": 1, "durationMs": <int>}`; failure: function error with message `DB_PROBE_FAILED: <reason>` (no credentials, no connection string) |
| `chatbot`, `sync` | `{}` | `{"status": "ok"}` |

Environment variables (no secret values): `DB_PROXY_ENDPOINT`, `DB_NAME`, `DB_SECRET_ARN`.

## Affected Components

AWS resources only (VPC, subnets, NAT, security groups, RDS, secret, RDS Proxy, three functions, log groups); the
function code lives in the console until it is brought into Git (`admin`: Week 3; [R-15](../RISKS.md#2-risk-register)).

## Security Considerations

- No public IP on Lambda, Proxy or RDS; RDS reachable only from `sg-proxy`, the proxy only from `sg-lambda`.
- Credentials only in Secrets Manager; never in code, env vars, logs or Git. The handler logs no credentials or
  connection string with a password.
- TLS from Lambda to the proxy and from the proxy to RDS.
- One IAM role per function; Secrets Manager access limited to the one secret ARN.
- The NAT gives the private subnets an outbound internet path — accepted for Week 1 (curriculum S3).

## Cost

Running 24/7 in eu-central-1 (Price List API, 2026-11-05): RDS ~$14 + storage ~$3 + RDS Proxy ~$26 + NAT ~$38 ≈
**$81/month** + data transfer (us-east-1 ≈ $69); not re-priced for the actual region (ADR-009); the NAT line
applies only if a NAT gateway exists ([R-09](../RISKS.md#2-risk-register)). The AWS Budgets alert must exist; stop or
remove idle resources ([R-06](../RISKS.md#2-risk-register)).

## Open Questions

| ID | Question | Recommendation |
|---|---|---|
| [Q-02](../RISKS.md#q-02) | IaC tool for the later import (T00-03) | AWS CDK, Python |
