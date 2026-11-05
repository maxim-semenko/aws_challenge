# OPS-05 — Local AWS CLI and SDK setup check

> **BLOCKED** by [Q-11](../RISKS.md#q-11). Do not start design or implementation until the item is resolved in RISKS.md.

| Field | Value |
|---|---|
| Status | **Blocked** |
| Epic | OPS — repository, CI/CD, cost |
| Milestone | M0 |
| Role | OPS |
| Size | S |
| Depends on | [ARCH-02](ARCH-02.md) |
| Blocked by | [Q-11](../RISKS.md#q-11) |
| Unblocks | — |
| Risks watched | — |
| Goals | — |
| References | [Week 1 spec](../specs/week-01-environment.md) W1-G3, AC-8 |

## Goal

The developer machine can reach the target account with the CLI and with the SDK(s) chosen in Q-11, using the
same named profile and no long-lived keys in files of the repository.

## Scope

**In scope**

- AWS CLI v2 profile `awsch` (from ARCH-02) works: `aws sts get-caller-identity --profile awsch`
- SDK check per Q-11 (one-off, results recorded here; no new project code unless Q-11 says so)
- README section "Local AWS access" (profile name, region, how to log in)

**Out of scope**

- CI credentials (OPS-02)

## Plan

- [ ] Run the CLI check
- [ ] Run the SDK check(s)
- [ ] Update README

## Definition of Done

- [ ] All checks succeed; outputs recorded below (account id may be masked)
- [ ] No credentials in the repository
- [ ] Status updated here and in [PLAN.md](../PLAN.md)

## Notes

_Decisions, measurements and findings made while working on the task._
