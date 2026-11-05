# ARCH-01 — Resolve open decisions and confirm ADRs

| Field | Value |
|---|---|
| Status | **Todo** |
| Epic | ARCH — decisions & preparation |
| Milestone | M0 |
| Role | OWNER + ARCH |
| Size | S |
| Depends on | — |
| Blocked by | — |
| Unblocks | [ARCH-02](ARCH-02.md), [ARCH-03](ARCH-03.md), [OPS-01](OPS-01.md), [INF-00](INF-00.md), [BE-00](BE-00.md), [FE-00](FE-00.md) |
| Risks watched | — |
| Goals | G1–G8 |
| References | RISKS.md §1, ARCHITECTURE.md §11 |

## Goal

Close every open decision in RISKS.md and move each ADR from Proposed to Accepted or Rejected, so that blocked tasks can be released.

## Scope

**In scope**

- Answers to Q-01 … Q-11 (Q-08 … Q-11 added 2026-11-05 from the [Week 1 spec](../specs/week-01-environment.md))
- ADR-001 … ADR-012 status
- Release or re-scope tasks blocked by the answered items

**Out of scope**

- Any implementation

## Plan

- [ ] Walk through RISKS.md §1 with the owner
- [ ] Record each decision with date in RISKS.md §3 (Closed items)
- [ ] Update ADR statuses in ARCHITECTURE.md §11
- [ ] For every task with a resolved blocker: Blocked → Todo, adjust scope, clear `Blocked by`
- [ ] Update the task index in PLAN.md

## Definition of Done

- [ ] No `Q-xx` left Open (or explicitly deferred with owner and date)
- [ ] Every ADR is Accepted or Rejected
- [ ] PLAN.md index and task files show consistent statuses
- [ ] Status updated here and in [PLAN.md](../PLAN.md)

## Notes

_Decisions, measurements and findings made while working on the task._
