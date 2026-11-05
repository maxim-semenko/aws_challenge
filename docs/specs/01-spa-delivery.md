# Spec 01 — SPA delivery from Git through CloudFront

Requirements: [week-01](../requirements/week-01-environment.md) W1-G1, S1, S2 · Design: [spa-hosting](../design/spa-hosting.md)
Tasks: T00-02, T00-04, T01-05, T01-06

## Purpose

Every push to `main` publishes the current SPA, served over HTTPS through CloudFront.

## Inputs

| Name | Type | Valid range | Required |
|---|---|---|---|
| Git push | commit on branch `main` | any commit where `npm ci && npm run build` succeeds in `frontend/` | yes |
| `amplify.yml` | build spec in the repository root | `version: 1`, `applications[0].appRoot: frontend`, `artifacts.baseDirectory: dist` | yes |
| `AMPLIFY_MONOREPO_APP_ROOT` | Amplify app env var | exactly `frontend` | yes |
| `VITE_*` | Amplify app env vars | may be empty in Week 1 | no |

## Outputs

| Output | Structure | Guarantees |
|---|---|---|
| Public URL | `https://main.<appId>.amplifyapp.com` | HTTPS only; served by CloudFront (`Via` contains `cloudfront.net`, `X-Amz-Cf-Id` present) |
| Any path without a file extension (e.g. `/chat`) | `index.html`, status 200 | client-side routing works on reload |
| Static assets `/assets/*` | files from `frontend/dist/assets` | correct content type |

## Behaviour

1. Developer pushes to `main`.
2. Amplify detects the push and runs `preBuild` (`npm ci`) and `build` (`npm run build`) in `frontend/`.
3. Amplify publishes `frontend/dist` and invalidates its CloudFront cache.
4. A user requests the URL; CloudFront serves `index.html` and assets over HTTPS.
5. The SPA renders the home page; without `VITE_*` values it shows no login and does not crash.

## Edge Cases / Failure Modes

| Case | Expected result |
|---|---|
| Build fails (lint/type error) | Amplify build fails, the previous version stays live |
| Deep link `/admin` reloaded | 200 with `index.html` (rewrite), not 404 |
| Request to a missing asset `/x.js` | 404 (no rewrite for paths with an extension) |
| HTTP request | redirected to HTTPS |
| `VITE_*` empty | home page renders; auth-dependent UI hidden |

## Acceptance Criteria

- [ ] AC-01.1 `curl -I https://main.<appId>.amplifyapp.com` → `200`, headers `Via` (…cloudfront.net), `X-Cache`, `X-Amz-Cf-Id`
- [ ] AC-01.2 `curl -I https://main.<appId>.amplifyapp.com/chat` → `200`, `content-type: text/html`
- [ ] AC-01.3 A commit pushed to `main` appears in the Amplify build list and its build is live without manual steps
- [ ] AC-01.4 The Amplify app, its branch and env vars are defined in IaC (manual console steps listed in the task notes, if any)
- [ ] AC-01.5 The repository history contains no secrets and no build outputs (secret scan report)
