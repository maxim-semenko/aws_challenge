# ARCH-02 — Prepare the AWS account

> **BLOCKED** by [Q-03](../RISKS.md#q-03). Do not start design or implementation until the item is resolved in RISKS.md.

| Field | Value |
|---|---|
| Status | **Blocked** |
| Epic | ARCH — decisions & preparation |
| Milestone | M0 |
| Role | OWNER |
| Size | S |
| Depends on | [ARCH-01](ARCH-01.md) |
| Blocked by | [Q-03](../RISKS.md#q-03) |
| Unblocks | [INF-07](INF-07.md), [OPS-05](OPS-05.md) |
| Risks watched | [R-05](../RISKS.md#2-risk-register), [R-06](../RISKS.md#2-risk-register) |
| Goals | G7 |
| References | ARCHITECTURE.md §3.6, §10 |

## Goal

Have a safe, cost-guarded AWS account in the chosen region with Bedrock model access.

## Scope

**In scope**

- IAM Identity Center user (or IAM user with MFA), no root usage
- AWS CLI v2 profile `awsch`
- AWS Budgets monthly alert (80% / 100%) to the owner's email
- Bedrock model access for `amazon.titan-embed-text-v2:0`
- Check quotas: Lambda concurrent executions, VPC interface endpoints

**Out of scope**

- `cdk bootstrap` (INF-00)

## Plan

- [ ] Create the user/permission set and CLI profile
- [ ] Create the budget and confirm the email subscription
- [ ] Request model access in the Bedrock console and wait for *Access granted*
- [ ] Record account id, region and profile name in CLAUDE.md (no secrets)

## Definition of Done

- [ ] `aws sts get-caller-identity --profile awsch` succeeds
- [ ] Budget alert exists and is confirmed
- [ ] Titan v2 shows *Access granted* in the chosen region
- [ ] Status updated here and in [PLAN.md](../PLAN.md)

## Notes

_Decisions, measurements and findings made while working on the task._
