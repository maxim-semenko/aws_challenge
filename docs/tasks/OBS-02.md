# OBS-02 — Request correlation across the chain

| Field | Value |
|---|---|
| Status | **Todo** |
| Epic | OBS — observability |
| Milestone | M2 |
| Role | BE + OPS |
| Size | S |
| Depends on | [OBS-01](OBS-01.md), [INF-06](INF-06.md) |
| Blocked by | — |
| Unblocks | [OBS-03](OBS-03.md) |
| Risks watched | — |
| Goals | G8 |
| References | ARCHITECTURE.md §9 |

## Goal

One request can be followed from API Gateway through Lambda to Bedrock and the database.

## Scope

**In scope**

- MDC `apiRequestId`, `awsRequestId`, `userSub`, `traceId`
- API Gateway access log format with the same `requestId`

**Out of scope**

- Distributed tracing UI (X-Ray optional)

## Plan

- [ ] Implement filter and handler MDC
- [ ] Align access log format
- [ ] Trace one request manually

## Definition of Done

- [ ] Same `requestId` visible in API GW and Lambda logs
- [ ] Status updated here and in [PLAN.md](../PLAN.md)

## Notes

_Decisions, measurements and findings made while working on the task._
