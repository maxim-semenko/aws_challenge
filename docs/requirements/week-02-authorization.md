# Requirements — Week 2: Authorization

Source: challenge curriculum plan, row "Week 2 — Authorization: Cognito User Pool with Amplify Auth; HTTP API Gateway
with JWT authorizer" (screenshot provided by the owner, 2026-11-12). **No assignment page exists for this week** (the
curriculum link points to the Week 1 page), so goals and steps below are **derived** from the topic line and the
project requirements (user part, admin part). Derived items are marked `(derived)`; the owner confirms them by
accepting the design doc. This file is the input for design docs and specs; it is not edited except to fix the export.

## Topic (as given)

Authorization: Cognito User Pool with Amplify Auth; HTTP API Gateway with JWT authorizer.

## Project requirements relevant to this week (as given, translated)

- A user can register and sign in.
- On registration the user enters the required fields: First_name, Last_name, Email, Gender (only two values: F and
  M), Date_of_birth (format DD/MM/YYYY), Country_of_living, Height in cm, Weight in kg.
- After sign-in the user lands on a personal page that shows their data. Editing is not provided.
- The administrator has access to a page with the list of all users and their data in a table (no editing) and to an
  AI query page. *(Pages themselves are later weeks; this week only the admin role has to exist.)*

## Week goals (derived)

| # | Goal |
|---|---|
| W2-G1 | A user signs up in the SPA with all required fields, confirms the e-mail and signs in/out through Amplify Auth against a Cognito User Pool *(2026-11-13, owner: the owner confirms new accounts in the Cognito console; no e-mail code in the SPA)* |
| W2-G2 | After sign-in the user sees a read-only personal page with their registration data |
| W2-G3 | An HTTP API Gateway with a Cognito JWT authorizer rejects requests without a valid token (401) and passes requests with a valid access token to the route's integration |
| ~~W2-G4~~ | *Moved to Week 3 (owner, 2026-11-13: Week 2 = the curriculum topic only).* (Was: an administrator role exists (Cognito group); a protected admin route is denied to non-admins (403).) |
| ~~W2-G5~~ | *Moved to Week 3 per curriculum (2026-11-12): "REST API + data: Admin Lambda ↔ RDS Proxy, Sync chain Cognito → EventBridge → Lambda".* (Was: a newly confirmed user is stored in PostgreSQL.) |

## Implementation steps (derived)

| # | Step |
|---|---|
| S1 | Create a Cognito User Pool: sign-in by e-mail, e-mail verification, password policy, standard and custom attributes for all registration fields, group `admin`, app client for the SPA (no secret) *(2026-11-13: group `admin` moved to Week 3 with W2-G4; e-mail verification replaced by the owner's confirmation in the console)* |
| S2 | Configure Amplify Auth in the SPA (`aws-amplify` 6) with `VITE_*` settings; sign-up, confirm, sign-in, sign-out screens; route guard *(2026-11-13: no confirm screen, see W2-G1)* |
| S3 | Personal page: shows the user's own data, read-only |
| S4 | Create an HTTP API with a JWT authorizer (issuer = User Pool, audience = app client); CORS for the SPA origin; Lambda integrations under `/api` *(2026-11-13: built by the owner with routes `/admin`, `/chat` without the `/api` prefix — [ENVIRONMENT.md](../ENVIRONMENT.md#http-api-week-2); the prefix of CLAUDE.md §6 applies when Week 3 defines the endpoints)* |
| ~~S5~~ | *Moved to Week 3 (owner, 2026-11-13).* (Was: protected endpoints: one for the current user, one admin-only probe; the SPA calls them with `Authorization: Bearer <token>`.) |
| ~~S6~~ | *Moved to Week 3 per curriculum (2026-11-12).* (Was: users table and Sync Lambda writing the user row through RDS Proxy.) |
| ~~S7~~ | *Moved to Week 3 (2026-11-13): no handler code and no API access log in the Week 2 build; logging comes with the Week 3 Lambda code (G8 standardised in Week 6).* (Was: logs of the API and Lambdas in CloudWatch without tokens or personal data beyond what §7 of CLAUDE.md allows.) |

## Traceability

| Requirement | Spec |
|---|---|
| W2-G1, W2-G2, S1–S3 | [04-user-registration-and-sign-in](../specs/04-user-registration-and-sign-in.md) |
| W2-G3, S4 | [05-protected-api](../specs/05-protected-api.md) |
| W2-G4, W2-G5, S5, S6, S7 | moved to Week 3 (not planned yet) |
