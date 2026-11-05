# INF-08 — Hosting: Amplify app and CloudFront

> **BLOCKED** by [Q-01](../RISKS.md#q-01), [Q-04](../RISKS.md#q-04). Do not start design or implementation until the item is resolved in RISKS.md.

| Field | Value |
|---|---|
| Status | **Blocked** |
| Epic | INF — infrastructure as code |
| Milestone | M1 |
| Role | OPS |
| Size | M |
| Depends on | [OPS-01](OPS-01.md), [FE-00](FE-00.md) |
| Blocked by | [Q-01](../RISKS.md#q-01), [Q-04](../RISKS.md#q-04) |
| Unblocks | [FE-06](FE-06.md), [QA-03](QA-03.md) |
| Risks watched | — |
| Goals | G1, G2 |
| References | ARCHITECTURE.md §3.1 |

## Goal

The SPA is built from Git on every push and served over HTTPS through CloudFront.

## Scope

**In scope**

- Amplify app connected to the repository, branch `main`
- `AMPLIFY_MONOREPO_APP_ROOT=frontend`, `amplify.yml`
- Environment variables `VITE_*` from stack outputs (added once INF-04 / INF-06 exist; not needed for Week 1)
- Custom build output (`artifacts.baseDirectory`) in `amplify.yml` — [Week 1 spec](../specs/week-01-environment.md) S2
- SPA rewrite to `index.html`, security headers
- CloudFront setup according to the Q-01 decision

**Out of scope**

- Custom domain (optional later)

## Plan

- [ ] Create the app (CDK or console, recorded in IaC if possible)
- [ ] First build
- [ ] Verify CloudFront headers

## Definition of Done

- [ ] Push to `main` triggers a build and the new version is live
- [ ] Response carries CloudFront headers (`x-cache`, `via`)
- [ ] Status updated here and in [PLAN.md](../PLAN.md)

## Notes

_Decisions, measurements and findings made while working on the task._
