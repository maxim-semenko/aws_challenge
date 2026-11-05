# ARCH-03 — Define engineering conventions

| Field | Value |
|---|---|
| Status | **Todo** |
| Epic | ARCH — decisions & preparation |
| Milestone | M0 |
| Role | ARCH |
| Size | S |
| Depends on | [ARCH-01](ARCH-01.md) |
| Blocked by | — |
| Unblocks | — |
| Risks watched | — |
| Goals | — |
| References | CLAUDE.md, ARCHITECTURE.md |

## Goal

Fix the conventions every contributor follows, so tasks can be delegated without re-discussing basics.

## Scope

**In scope**

- AWS resource naming `awsch-<env>-<name>` and mandatory tags (`project`, `env`, `owner`)
- Java package structure and layering rules
- Error model (RFC 9457 ProblemDetail) and error codes
- Logging fields and what must never be logged
- Commit and branch conventions

**Out of scope**

- Tooling enforcement (CI checks come with OPS-02)

## Plan

- [ ] Draft the conventions section in ARCHITECTURE.md
- [ ] Mirror the short version in CLAUDE.md
- [ ] Review with the owner

## Definition of Done

- [ ] Conventions section published in ARCHITECTURE.md
- [ ] CLAUDE.md references it
- [ ] Status updated here and in [PLAN.md](../PLAN.md)

## Notes

_Decisions, measurements and findings made while working on the task._
