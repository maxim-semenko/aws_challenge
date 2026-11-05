# Requirements — Week 1: Environment setup

Source: challenge curriculum, "Week 1: Environment setup" (Alex Ramasheuski, 2025-09-02). Local export, translated
to English. This file is the input for design docs and specs; it is not edited except to fix the export.

## Task

Deploy a minimal but working cloud skeleton: Amplify Hosting + CloudFront for the React SPA, a VPC with private
subnets for Lambda, Amazon RDS PostgreSQL and RDS Proxy.

## Week goals

| # | Goal |
|---|---|
| W1-G1 | The SPA opens over HTTPS through CloudFront |
| W1-G2 | VPC with private subnets is configured; a test Lambda successfully pings RDS PostgreSQL through RDS Proxy |
| W1-G3 | AWS CLI and AWS SDK v3 are configured locally |

## Implementation steps

| # | Step |
|---|---|
| S1 | Create a new Amplify project and connect the SPA Git repository |
| S2 | Set a custom build output in `amplify.yml`, deploy and check the CloudFront distribution |
| S3 | Create the VPC: 1 public subnet, 2 private subnets + NAT Gateway |
| S4 | Create RDS PostgreSQL 14 and RDS Proxy (target group = the database); allow access only from the private subnets |
| S5 | Scaffold three empty Lambda functions (Admin, Chatbot, Sync) in the private subnets; give them a role with access to Secrets Manager / RDS Proxy |
| S6 | Check the connection: run `SELECT 1` from the Admin Lambda |
| S7 | Configure CloudWatch log groups for all functions (retention ≥ 7 days) |

## Materials

Amplify Hosting User Guide · SPA on S3 + CloudFront step by step · VPC concept for Lambda (private subnets) ·
Using Amazon RDS Proxy with Lambda.

## Traceability

| Requirement | Spec |
|---|---|
| W1-G1, S1, S2 | [specs/01-spa-delivery.md](../specs/01-spa-delivery.md) |
| W1-G2, S3–S7 | [specs/02-database-connectivity.md](../specs/02-database-connectivity.md) |
| W1-G3 | [specs/03-local-aws-access.md](../specs/03-local-aws-access.md) |
