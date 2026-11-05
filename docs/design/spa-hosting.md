# Design — SPA hosting (Amplify Hosting + CloudFront)

Status: **Draft** — waiting for the owner's answers to the open questions below.
Requirements: [week-01](../requirements/week-01-environment.md) W1-G1, S1, S2 · Spec: [01-spa-delivery](../specs/01-spa-delivery.md)
Architecture: [ARCHITECTURE.md](../ARCHITECTURE.md) §3.1, goals G1, G2

## Problem Statement

The React SPA in `frontend/` must be built from Git and served to users over HTTPS through CloudFront, with no
manual steps after a push. There is no Git repository and no AWS hosting yet.

## Proposed Solution

- The project goes into the Git hosting chosen in Q-04, default branch `main`.
- An Amplify Hosting app is connected to the repository (branch `main`, monorepo, `AMPLIFY_MONOREPO_APP_ROOT=frontend`).
  It is created by IaC (Q-02); with IaC the monorepo variable must be set explicitly.
- `amplify.yml` (already in the repository root) builds `frontend/` with `npm ci && npm run build` and publishes
  `artifacts.baseDirectory: dist` — this is the "custom build output" of S2.
- A rewrite rule sends every path without a file extension to `/index.html` (200), so client routes work.
- Amplify serves through its own CloudFront distribution (Q-01 option A; visibility and proof: see the note under
  [Q-01](../RISKS.md#q-01)).
- Week 1 deploys the SPA without Cognito/API settings; the SPA must render its home page when `VITE_*` values are
  empty. Real values are added in the week that brings Cognito and the API.

## Alternatives Considered

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Amplify Hosting with its managed CloudFront (proposed) | matches S1/S2 literally; Git-driven builds, previews, rewrites out of the box | distribution not visible in our account; less control over cache/WAF | proposed |
| Own S3 bucket + own CloudFront distribution (OAC), deployed by CI | full control, distribution visible, one domain for SPA and API later | not "Amplify Hosting" (S1); we must build CI deploy ourselves | rejected for Week 1; possible later (Q-01 B) |
| Amplify Hosting + own CloudFront in front of it | single domain for SPA + API | double CDN, more config, little learning value now | rejected |

## API Design

None — static files only. Public URL: `https://main.<appId>.amplifyapp.com`.

## Affected Components

`amplify.yml` · `frontend/` (render without configuration) · IaC Hosting stack (new) · Git repository (new).

## Security Considerations

- HTTPS only (Amplify default certificate on `amplifyapp.com`).
- No secrets in the SPA: `VITE_*` values are public identifiers only.
- Initial commit is secret-scanned before the first push (no `.env.local`, keys or build outputs in history).
- Security headers (CSP, HSTS) are not part of Week 1.

## Open Questions

| ID | Question | Recommendation |
|---|---|---|
| [Q-01](../RISKS.md#q-01) | Which CloudFront counts for G2 | Amplify-managed (option A) |
| [Q-02](../RISKS.md#q-02) | IaC tool (creates the Amplify app) | AWS CDK, Java |
| [Q-04](../RISKS.md#q-04) | Git hosting | GitHub |
