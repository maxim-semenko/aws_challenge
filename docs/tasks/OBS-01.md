# OBS-01 — Logging spike: structured JSON in Lambda

| Field | Value |
|---|---|
| Status | **Todo** |
| Epic | OBS — observability |
| Milestone | M1 |
| Role | BE + OPS |
| Size | S |
| Depends on | [INF-05](INF-05.md) |
| Blocked by | — |
| Unblocks | [OBS-02](OBS-02.md) |
| Risks watched | [R-10](../RISKS.md#2-risk-register) |
| Goals | G8 |
| References | ADR-012 |

## Goal

Choose the log setup that yields exactly one parseable JSON object per log line in CloudWatch.

## Scope

**In scope**

- Spring structured logging (ECS) vs Lambda log format JSON/Text
- Sample lines from each option

**Out of scope**

- Dashboards

## Plan

- [ ] Deploy both variants to dev
- [ ] Compare in Logs Insights
- [ ] Record the choice

## Definition of Done

- [ ] Example lines in Notes
- [ ] ADR-012 Accepted
- [ ] Status updated here and in [PLAN.md](../PLAN.md)

## Notes

_Decisions, measurements and findings made while working on the task._
