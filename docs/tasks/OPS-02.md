# OPS-02 — CI pipeline: build, test, synth on every PR

> **BLOCKED** by [Q-04](../RISKS.md#q-04). Do not start design or implementation until the item is resolved in RISKS.md.

| Field | Value |
|---|---|
| Status | **Blocked** |
| Epic | OPS — repository, CI/CD, cost |
| Milestone | M1 |
| Role | OPS |
| Size | M |
| Depends on | [OPS-01](OPS-01.md), [BE-00](BE-00.md), [FE-00](FE-00.md), [INF-00](INF-00.md) |
| Blocked by | [Q-04](../RISKS.md#q-04) |
| Unblocks | [OPS-03](OPS-03.md) |
| Risks watched | — |
| Goals | G1 |
| References | — |

## Goal

Every pull request proves that backend, frontend and infrastructure still build.

## Scope

**In scope**

- Backend: `./gradlew :backend:build` including Testcontainers tests (Docker available on runner)
- Frontend: `npm ci`, `npm run lint`, `npm run build`
- Infrastructure: `cdk synth` + cdk-nag
- Gradle and npm caching

**Out of scope**

- Deployment (OPS-03)

## Plan

- [ ] Choose the CI platform matching Q-04
- [ ] Add the workflow
- [ ] Make checks required on `main`

## Definition of Done

- [ ] PRs show status checks
- [ ] A failing test or lint error fails the pipeline
- [ ] Typical run < 10 min
- [ ] Status updated here and in [PLAN.md](../PLAN.md)

## Notes

_Decisions, measurements and findings made while working on the task._
