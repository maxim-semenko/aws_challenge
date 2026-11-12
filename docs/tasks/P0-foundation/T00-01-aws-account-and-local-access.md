---
id: T00-01
title: "AWS account, budget and local CLI/SDK access"
phase: P0-foundation
status: Review
agent: devops
skills: [cloud-architect]
depends_on: []
blocked_by: []
design: null  # account setup, no product feature
spec: ../../specs/03-local-aws-access.md
acceptance: [AC-03.1, AC-03.2, AC-03.3, AC-03.4]
---
# T00-01 — AWS account, budget and local CLI/SDK access

> **2026-11-12 — built manually by the owner** in the AWS console ([Q-12](../../RISKS.md#q-12), option C).
> T01-06 records the facts of the build and verifies the ACs; the owner sets `Done` from that evidence.
> Constraints and ACs that assume IaC are deferred to T00-03. Scope items the manual build did not produce
> (e.g. the skill file) appear as open items in T01-06; the owner waives them or asks devops to deliver them.

## // BUSINESS CONTEXT

Every later task deploys to or calls AWS from a developer machine. Without a safe identity and a budget alert, a
mistake costs money (Week 1 stack cost: [backend-foundation](../../design/backend-foundation.md) §Cost) or leaks
credentials. Week 1 goal W1-G3 requires the CLI and an
SDK to work locally.

## // TECHNICAL CONSTRAINTS

- Root user only for account setup; daily work through IAM Identity Center or an IAM user with MFA.
- Profile name `awsch`, region from Q-03. No access keys in the repository, in `.env` files or in docs.
- SDK checks are one-off commands; outputs go to Notes with the account id masked. No new project code unless Q-11
  says so.
- The owner performs console steps; the agent prepares exact commands and verifies.

## // SCOPE

**Implement**
- Working identity + CLI profile `awsch`
- AWS Budgets monthly alert 80 % / 100 % to the owner's email
- SDK check(s) per Q-11
- README section "Local AWS access"
- Skill file `aws-access` (profile, login, budget; skills ownership rule)

**Exclude**
- `cdk bootstrap` (T00-03), Bedrock model access, CI credentials

**Interfaces that must match**
- Profile name `awsch` and the region are used unchanged by T00-03 and every deploy command.

## Definition of Done

- [ ] AC-03.1 … AC-03.4 of [spec 03](../../specs/03-local-aws-access.md) pass, evidence in Notes
- [ ] Skill file added
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes
