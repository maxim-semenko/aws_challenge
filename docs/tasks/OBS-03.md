# OBS-03 — Logs Insights queries and dashboard

| Field | Value |
|---|---|
| Status | **Todo** |
| Epic | OBS — observability |
| Milestone | M5 |
| Role | OPS |
| Size | S |
| Depends on | [OBS-02](OBS-02.md) |
| Blocked by | — |
| Unblocks | [OBS-04](OBS-04.md), [QA-04](QA-04.md) |
| Risks watched | — |
| Goals | G8 |
| References | — |

## Goal

Operators answer 'what happened to this request' and 'how healthy is the API' in minutes.

## Scope

**In scope**

- Saved queries: trace by `apiRequestId`, p95 latency, errors by status
- CloudWatch dashboard
- All in IaC

**Out of scope**

- Alarms (OBS-04)

## Plan

- [ ] Write queries
- [ ] Add to IaC
- [ ] Demo

## Definition of Done

- [ ] Queries and dashboard deployed by IaC
- [ ] Status updated here and in [PLAN.md](../PLAN.md)

## Notes

_Decisions, measurements and findings made while working on the task._
