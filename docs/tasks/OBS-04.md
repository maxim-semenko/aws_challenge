# OBS-04 — Alarms (stretch)

| Field | Value |
|---|---|
| Status | **Todo** |
| Epic | OBS — observability |
| Milestone | Stretch |
| Role | OPS |
| Size | S |
| Depends on | [OBS-03](OBS-03.md) |
| Blocked by | — |
| Unblocks | — |
| Risks watched | — |
| Goals | G8 |
| References | — |

## Goal

Get notified when the system misbehaves.

## Scope

**In scope**

- Alarms: API 5xx, Lambda errors/throttles, Proxy connections
- SNS email topic

**Out of scope**

- On-call tooling

## Plan

- [ ] Define thresholds
- [ ] Add to IaC
- [ ] Fire a test alarm

## Definition of Done

- [ ] Test alarm reaches email
- [ ] Status updated here and in [PLAN.md](../PLAN.md)

## Notes

_Decisions, measurements and findings made while working on the task._
