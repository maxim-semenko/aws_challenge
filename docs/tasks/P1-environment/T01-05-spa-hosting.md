---
id: T01-05
title: "Hosting stack: Amplify app connected to Git"
phase: P1-environment
status: Blocked
agent: devops
skills: [cloud-architect, devops-engineer]
depends_on: [T00-02, T00-03, T00-04]
blocked_by: [Q-01]
design: ../../design/spa-hosting.md
spec: ../../specs/01-spa-delivery.md
acceptance: [AC-01.1, AC-01.2, AC-01.3, AC-01.4]
---
# T01-05 — Hosting stack: Amplify app connected to Git

> **BLOCKED** by [Q-01](../../RISKS.md#q-01).

## // BUSINESS CONTEXT

W1-G1: users open the SPA over HTTPS through CloudFront, and every push to `main` publishes it without manual steps
(G1). This is the first thing a reviewer sees of the project.

## // TECHNICAL CONSTRAINTS

- Amplify app created by IaC, connected to the repository from T00-02, branch `main`, auto-build on.
- `AMPLIFY_MONOREPO_APP_ROOT=frontend` set explicitly (IaC does not set it); `amplify.yml` keeps
  `appRoot: frontend`, `baseDirectory: dist`.
- Rewrite: paths without a file extension → `/index.html` (200).
- Git access token for Amplify stored in Secrets Manager (or a GitHub App connection), never in code or context files.
- Manual console steps only where IaC cannot do it; list them in Notes.

## // SCOPE

**Implement**
- Hosting stack: Amplify app, branch, env var, rewrite rule
- First build; verification with `curl -I` per spec 01
- Skill file for Amplify Hosting (skills ownership rule)

**Exclude**
- `VITE_*` values for Cognito/API, custom domain, security headers, own CloudFront distribution

**Interfaces that must match**
- `amplify.yml` in the repository root is the build spec; build output `frontend/dist`.

## Definition of Done

- [ ] AC-01.1 … AC-01.4 verified, evidence in Notes
- [ ] Skill file added; ARCH review passed
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes
