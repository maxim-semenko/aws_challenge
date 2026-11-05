# OPS-01 — Put the project under Git and push to the remote

> **BLOCKED** by [Q-04](../RISKS.md#q-04). Do not start design or implementation until the item is resolved in RISKS.md.

| Field | Value |
|---|---|
| Status | **Blocked** |
| Epic | OPS — repository, CI/CD, cost |
| Milestone | M0 |
| Role | OPS |
| Size | S |
| Depends on | [ARCH-01](ARCH-01.md) |
| Blocked by | [Q-04](../RISKS.md#q-04) |
| Unblocks | [OPS-02](OPS-02.md), [INF-08](INF-08.md), [FE-06](FE-06.md) |
| Risks watched | — |
| Goals | G1 |
| References | ARCHITECTURE.md §3.1 |

## Goal

Version-control the project in the agreed hosting so Amplify and CI can build from it.

## Scope

**In scope**

- `git init`, default branch `main`
- Review `.gitignore`: `build/`, `dist/`, `node_modules/`, `.idea/`, `.env.local`, `cdk.out/`, `*.zip`
- Initial commit, remote repository, push
- Branch protection on `main` (PR required, checks required once OPS-02 exists)
- Secret scan of the initial commit (e.g. gitleaks)

**Out of scope**

- CI pipeline (OPS-02)

## Plan

- [ ] Fix `.gitignore`
- [ ] Commit and push
- [ ] Configure branch protection
- [ ] Run a secret scan

## Definition of Done

- [ ] Repository reachable by the team
- [ ] No build outputs or secrets in history
- [ ] `main` is protected
- [ ] Status updated here and in [PLAN.md](../PLAN.md)

## Notes

_Decisions, measurements and findings made while working on the task._
