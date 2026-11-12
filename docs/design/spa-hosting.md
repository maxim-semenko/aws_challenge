# Design — SPA hosting (Amplify Hosting + CloudFront)

Status: **Draft** — the owner built this manually in the console (Q-12 C); T01-06 records the actual values, then the
owner accepts this doc as the record of the build.
Requirements: [week-01](../requirements/week-01-environment.md) W1-G1, S1, S2 · Spec: [01-spa-delivery](../specs/01-spa-delivery.md)
Architecture: [ARCHITECTURE.md](../ARCHITECTURE.md) §3.1, goals G1, G2

## Problem Statement

The React SPA in `frontend/` must be built from Git and served to users over HTTPS through CloudFront, with no
manual steps after a push.

## Proposed Solution

- The project is in the Git hosting of the build (Q-04 closed; recorded by T01-06), default branch `main`.
- An Amplify Hosting app is connected to the repository (branch `main`, monorepo, `AMPLIFY_MONOREPO_APP_ROOT=frontend`),
  created in the console (Q-12 C); a later IaC import (T00-03) must set the monorepo variable explicitly.
- `amplify.yml` (already in the repository root) builds `frontend/` with `npm ci && npm run build` and publishes
  `artifacts.baseDirectory: dist` — this is the "custom build output" of S2.
- A rewrite rule sends every path without a file extension to `/index.html` (200), so client routes work.
- Amplify serves through its own CloudFront distribution (Q-01, decided by the build). The distribution is not
  visible in our account; the proof of G2 is the response headers (`Via: … cloudfront.net`, `X-Cache`,
  `X-Amz-Cf-Id`) — spec 01 AC-01.1.
- Week 1 deploys the SPA without Cognito/API settings; the SPA must render its home page when `VITE_*` values are
  empty. Real values are added in the week that brings Cognito and the API.

## Alternatives Considered

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Amplify Hosting with its managed CloudFront | matches S1/S2 literally; Git-driven builds, previews, rewrites out of the box | distribution not visible in our account; less control over cache/WAF | built |
| Own S3 bucket + own CloudFront distribution (OAC), deployed by CI | full control, distribution visible, one domain for SPA and API later | not "Amplify Hosting" (S1); we must build CI deploy ourselves | rejected for Week 1; possible later |
| Amplify Hosting + own CloudFront in front of it | single domain for SPA + API | double CDN, more config, little learning value now | rejected |

## API Design

None — static files only. Public URL: `https://main.<appId>.amplifyapp.com`.

## Affected Components

`amplify.yml` · `frontend/` (render without configuration) · Amplify app (console) · Git repository.

## Security Considerations

- HTTPS only (Amplify default certificate on `amplifyapp.com`).
- No secrets in the SPA: `VITE_*` values are public identifiers only.
- Initial commit is secret-scanned before the first push (no `.env.local`, keys or build outputs in history).
- Security headers (CSP, HSTS) are not part of Week 1.

## Open Questions

| ID | Question | Recommendation |
|---|---|---|
| [Q-02](../RISKS.md#q-02) | IaC tool for the later import of the Amplify app (T00-03) | AWS CDK, Python |
