---
id: T02-01
title: "Cognito User Pool, SPA app client and group admin"
phase: P2-authorization
status: Blocked
agent: devops
skills: [cloud-architect]
depends_on: [T00-01]
blocked_by: [Q-14]
design: ../../design/authentication.md
spec: ../../specs/04-user-registration-and-sign-in.md
acceptance: [AC-04.1, AC-04.2]
---
# T02-01 — Cognito User Pool, SPA app client and group admin

> **BLOCKED** by [Q-14](../../RISKS.md#q-14).

## // BUSINESS CONTEXT

W2-G1 starts here: without a User Pool nobody can register. The pool's sign-in attribute, required attributes and
custom attributes can never be changed after creation, so a mistake costs a new pool and every registered user —
this is why the task waits for the owner's answer on the attribute schema (Q-14).

## // TECHNICAL CONSTRAINTS

- AWS CLI commands with profile `awsch`, recorded as a replayable runbook in Notes (Q-12 C); region of the Week 1
  build.
- Settings exactly as in [design/authentication](../../design/authentication.md) §Proposed Solution; attributes exactly
  as in the accepted Q-14 answer (spec 04 §Inputs).
- Names `awsch-dev-users`, `awsch-dev-spa`; tags `project`, `env`, `owner` (CLAUDE.md §7).
- App client without secret; no OAuth/hosted-UI configuration; no Lambda triggers; deletion protection on.
- Public identifiers only in Amplify env vars; nothing secret exists in this task.
- Show every command to the owner and wait for the go-ahead before running it (CLAUDE.md §3.8).

## // SCOPE

**Implement**
- User Pool, app client `awsch-dev-spa`, group `admin`
- Amplify Hosting env vars `VITE_AWS_REGION`, `VITE_COGNITO_USER_POOL_ID`, `VITE_COGNITO_USER_POOL_CLIENT_ID`
  (rebuild of the branch noted)
- Runbook in Notes: every command, resulting ids and ARNs (account id masked), verify commands for AC-04.1/04.2
- Skill file `cognito-user-pool` (pool settings, attribute schema and its immutability, adding a user to `admin`,
  verification commands; skills ownership rule)

**Exclude**
- Lambda triggers (Week 3), SES, MFA, hosted UI/domain, adding members to `admin` (T02-03), IaC code (T00-03)

**Interfaces that must match**
- Attribute names and constraints exactly as spec 04 §Inputs (used by T02-04 and T02-05).
- Pool id, pool ARN, issuer URL and client id recorded in Notes for T02-03 and T02-04.

## Definition of Done

- [ ] AC-04.1, AC-04.2 verified, evidence in Notes
- [ ] Monthly cost noted (expected $0, Lite plan)
- [ ] Skill file added; ARCH review passed
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes
