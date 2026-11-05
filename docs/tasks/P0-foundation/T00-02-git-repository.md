---
id: T00-02
title: "Put the project under Git and push to the remote"
phase: P0-foundation
status: Blocked
agent: devops
skills: [devops-engineer]
depends_on: []
blocked_by: [Q-04]
design: ../../design/spa-hosting.md
spec: ../../specs/01-spa-delivery.md
acceptance: [AC-01.5]
---
# T00-02 — Put the project under Git and push to the remote

> **BLOCKED** by [Q-04](../../RISKS.md#q-04).

## // BUSINESS CONTEXT

Amplify Hosting builds only from a Git repository (S1), and "You Build It, You Run It" requires every change to be
traceable. Today nothing is under version control, so any lost file is lost for good.

## // TECHNICAL CONSTRAINTS

- Default branch `main`. Commit format from CLAUDE.md (Conventional Commits, task ID in the body).
- `.gitignore` covers `build/`, `dist/`, `node_modules/`, `.idea/`, `.gradle/`, `.env.local`, `cdk.out/`, `*.zip`.
- Secret scan (e.g. gitleaks) **before** the first push; a finding stops the push.
- Do not commit generated files (`frontend/dist`, Gradle build output).

## // SCOPE

**Implement**
- `git init`, `.gitignore` review, secret scan, initial commit, remote repository in the Q-04 hosting, push
- Skill file `secret-scanning` (tool, how to run it before a push; skills ownership rule)

**Exclude**
- CI pipeline and branch protection (later phase)

**Interfaces that must match**
- Repository URL and branch `main` are consumed by T01-05 (Amplify app).

## Definition of Done

- [ ] AC-01.5 passes (scan report in Notes)
- [ ] Repository reachable by the owner; `main` pushed
- [ ] Skill file added
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes
