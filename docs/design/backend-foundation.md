# Design — Backend foundation (VPC, RDS PostgreSQL, RDS Proxy, Lambda skeleton)

Status: **Draft** — waiting for the owner's answers to the open questions below.
Requirements: [week-01](../requirements/week-01-environment.md) W1-G2, S3–S7 ·
Spec: [02-database-connectivity](../specs/02-database-connectivity.md)
Architecture: [ARCHITECTURE.md](../ARCHITECTURE.md) §3.2, §3.5, §4, §8, ADR-001, ADR-005, ADR-006

## Problem Statement

The functions `admin`, `chatbot` and `sync` must run in private subnets and reach PostgreSQL only through RDS Proxy,
with credentials from Secrets Manager and logs in CloudWatch. Nothing exists in AWS yet, and the Spring Boot draft in
`backend/` has never compiled (R-04), so it cannot be the Week 1 deliverable.

## Proposed Solution

Everything is created by IaC (Q-02: AWS CDK in Java, Gradle module `infra`), in one environment `dev` (Q-07), in the
region from Q-03. Naming and tags per CLAUDE.md §7.

**Network (Q-08 option A — follows the curriculum).**

| Resource | Value |
|---|---|
| VPC | `10.0.0.0/16`, 2 AZs |
| Public subnet | 1 × `/24` in AZ-a, Internet Gateway, one NAT Gateway |
| Private subnets | 2 × `/24` (AZ-a, AZ-b), `PRIVATE_WITH_EGRESS` via the NAT — Lambda, RDS Proxy, RDS |
| VPC endpoints | none in Week 1 (Secrets Manager is reached through the NAT) |

Security groups (only what is needed):

| SG | Inbound | Outbound |
|---|---|---|
| `sg-lambda` | — | 5432 → `sg-proxy`; 443 → `0.0.0.0/0` (Secrets Manager via NAT) |
| `sg-proxy` | 5432 ← `sg-lambda` | 5432 → `sg-db` |
| `sg-db` | 5432 ← `sg-proxy` | — |

**Data.** RDS for PostgreSQL (major version per Q-09, recommended 17), `db.t4g.micro`, single-AZ, 20 GB gp3,
encrypted, 7-day backups, `PubliclyAccessible=false`, in the private subnets. Master credentials generated into a
Secrets Manager secret. RDS Proxy with that secret, TLS required, target = the instance, idle client timeout 30 min.

**Compute.** Three functions from one small artifact (Q-10 option A: Gradle module with plain Java 21 handlers, no
Spring), runtime `java21`, arm64, 512 MB, timeout 15 s, in the private subnets with `sg-lambda`.

| Function | Handler behaviour | IAM role (one per function) |
|---|---|---|
| `admin` | reads the secret, opens a JDBC connection to the **proxy** endpoint with `sslmode=require`, runs `SELECT 1`, closes it, returns the result | `AWSLambdaVPCAccessExecutionRole` + `secretsmanager:GetSecretValue` on the DB secret |
| `chatbot` | logs one line, returns `{"status":"ok"}` | same as `admin` (S5 asks for Secrets Manager / Proxy access for all three) |
| `sync` | logs one line, returns `{"status":"ok"}` | same as `admin` |

Log groups `/aws/lambda/<function>` are created by IaC before the functions, retention 14 days (S7 requires ≥ 7).
Each invocation writes one JSON log line.

## Alternatives Considered

| Topic | Option | Verdict |
|---|---|---|
| Network | Isolated subnets + interface endpoints, no NAT (current ADR-005) | Q-08 option B. Same cost (~$35 vs ~$38/month), no internet path, but deviates from S3 and needs an endpoint per AWS service |
| Network | Separate isolated subnets for RDS/Proxy + egress subnets for Lambda | Q-08 option C. Tighter data tier, 4 private subnets; possible later |
| PostgreSQL | 14 exactly as in S4 | Q-09 (a). Standard support on RDS ends 2027-02-28, then paid Extended Support |
| Handlers | Spring Boot artifact from `backend/` | Q-10 B. Blocks Week 1 on the draft review; adds cold-start work now |
| Handlers | Inline code in IaC | Q-10 C. No tests, no build, nothing reusable |
| Credentials | IAM authentication to the proxy | later stage; Week 1 uses the secret |

## API Design

No HTTP API in Week 1. Function contract (invoked with `aws lambda invoke`):

| Function | Input event | Output |
|---|---|---|
| `admin` | `{}` (any fields ignored) | success: `{"result": 1, "durationMs": <int>}`; failure: function error with message `DB_PROBE_FAILED: <reason>` (no credentials, no connection string) |
| `chatbot`, `sync` | `{}` | `{"status": "ok"}` |

Environment variables (no secret values): `DB_PROXY_ENDPOINT`, `DB_NAME`, `DB_SECRET_ARN`.

## Affected Components

New: Gradle module for the handlers (name fixed in the task), Gradle module `infra`, stacks Network, Data, Compute.
Changed: `settings.gradle`. Not touched: `backend/` draft.

## Security Considerations

- No public IP on Lambda, Proxy or RDS; RDS reachable only from `sg-proxy`, the proxy only from `sg-lambda`.
- Credentials only in Secrets Manager; never in code, env vars, logs or Git. The handler logs no credentials or JDBC URL with password.
- TLS from Lambda to the proxy (`sslmode=require`) and from the proxy to RDS.
- One IAM role per function; Secrets Manager access limited to the one secret ARN.
- The NAT gives the private subnets an outbound internet path — accepted for Week 1 (Q-08 A).

## Cost

Running 24/7 in eu-central-1 (Price List API, 2026-11-05): RDS ~$14 + storage ~$3 + RDS Proxy ~$26 + NAT ~$38 ≈
**$81/month** + data transfer (us-east-1 ≈ $69). The AWS Budgets alert must exist before the first deploy; destroy the
stacks when not in use ([R-06](../RISKS.md#2-risk-register)).

## Open Questions

| ID | Question | Recommendation |
|---|---|---|
| [Q-02](../RISKS.md#q-02) | IaC tool | AWS CDK, Java |
| [Q-03](../RISKS.md#q-03) | Region | `eu-central-1` |
| [Q-07](../RISKS.md#q-07) | Environments | single `dev` |
| [Q-08](../RISKS.md#q-08) | Network layout | A — public subnet + NAT as in S3 |
| [Q-09](../RISKS.md#q-09) | PostgreSQL major | 17 |
| [Q-10](../RISKS.md#q-10) | Week 1 handler code | A — plain Java in a separate module |
