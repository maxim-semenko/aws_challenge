---
name: cognito-user-pool
description: How this project uses the Cognito User Pool aws-challenge-users and its SPA app client — sign-in and attribute schema (and why it can never change), app client flows and token validity, manual confirmation of new users by the owner, where the identifiers live, how a change is made (console runbook executed by the owner) and what Week 3 adds. Use when writing a runbook that touches the pool or app client, when reading pool settings for the authorizer or the SPA, or when planning the admin group or the user sync.
license: MIT
metadata:
  domain: infrastructure
  triggers: Cognito, User Pool, app client, aws-challenge-users, aws-challenge-frontend-spa, custom attribute, confirm user, UNCONFIRMED, SRP, refresh token, token validity, issuer, cognito:groups
  role: specialist
  scope: infrastructure
  related-skills: cloud-architect, amplify-auth, http-api-jwt
  source: project (created by T02-01)
  used-by: [devops]
---

# Cognito User Pool

Design: [docs/design/authentication.md](../../../docs/design/authentication.md) (§Proposed Solution, §Security
Considerations). Attribute schema (names, types, ranges, mapping to the form): [spec 04](../../../docs/specs/04-user-registration-and-sign-in.md)
§Inputs — the single home. Identifiers and as-built values (pool id, client id, issuer, token validity, flows):
[docs/ENVIRONMENT.md §Authentication](../../../docs/ENVIRONMENT.md#authentication-week-2-t02-01) — **link to it, never
copy the values** into tasks, skills or code (the SPA reads them only from `VITE_*` variables).

Built manually in the console by the owner on 2026-11-12 (T02-01). Agents have no AWS access (CLAUDE.md §3.11).

## What the pool is configured for

- **Sign-in:** e-mail is the username attribute (case-insensitive), password only; MFA off; self sign-up on;
  deletion protection on; Cognito default e-mail sender (R-13).
- **Attributes:** required standard `given_name`, `family_name`, `gender`, `birthdate` (`email` is on every user as
  the sign-in attribute); custom `country` (String), `height`, `weight` (Number), mutable, **Cognito default bounds,
  no own min/max** (Q-14 C). All range checks live in the SPA only; Cognito stores whatever a direct `SignUp` call
  sends (R-11, R-12) — consumers must tolerate odd or missing values.
- **App client** `aws-challenge-frontend-spa`: public, **no client secret**; flows SRP (`ALLOW_USER_SRP_AUTH`) and
  refresh (`ALLOW_REFRESH_TOKEN_AUTH`), plus `ALLOW_USER_AUTH` as built (password only, accepted deviation, AC-04.2);
  prevent user existence errors on; token revocation on; read/write on every registration attribute; no OAuth,
  hosted UI or managed login used by the SPA (ADR-014). Token validity: ENVIRONMENT.md.
- **No Lambda triggers** in Week 2.
- Cost: no always-on resource; Essentials plan, free up to 10 000 MAU → ≈ $0/month.

## Immutable after creation

The username/sign-in attribute, the set of required attributes and the custom attributes (name, type, bounds) can
never be changed or removed. A mistake costs a new pool and every registered user (new pool id → new issuer → the
JWT authorizer, `VITE_*` variables and ENVIRONMENT.md all change). Adding a *new* custom attribute is possible but
it is new schema: design doc + spec first. Mutable settings (app client flows, token validity, groups, triggers,
password policy, e-mail settings) may change through a runbook.

## Confirming a new user (owner, console)

The SPA has no code-confirmation screen (owner decision 2026-11-13); a new user stays `UNCONFIRMED`.
Cognito console → User pools → `aws-challenge-users` → Users → select the user → **Actions → Confirm account**.
Verify: the user's "Confirmation status" shows *Confirmed*; the user can now sign in on the deployed SPA. Cognito may
still e-mail a verification code (verification of `email` is on as built); it is not used.

## Changing the pool or app client

Only through a step-by-step **console runbook** written by `devops` in the task Notes (page, field, exact value,
what to report back) and executed by the owner; the owner's screenshots are the evidence. After the change update
ENVIRONMENT.md (the only home of the values). Before any change check whether it touches the immutable list above or
the issuer/client id used by the authorizer ([http-api-jwt](../http-api-jwt/SKILL.md)). IaC: later, T00-03 (Q-02).

## Verify (as used for AC-04.1 / AC-04.2)

Screenshots from the owner, no token values: pool *Overview* (name, plan, deletion protection), *Sign-in* (e-mail),
*Sign-up* (required and custom attributes, self-registration), *Extensions* (no Lambda triggers), *App clients* →
`aws-challenge-frontend-spa` (no secret, auth flows, token validity, prevent user existence errors). Functional
check: sign up on the deployed SPA, confirm in the console, sign in, the profile on Home shows all eight fields.

## Planned for Week 3 (not built)

Group `admin` and the first administrator (owner adds the user in the console; membership arrives as
`cognito:groups` in the access token, checked by the API handler); the user sync to PostgreSQL (Lambda trigger or
other mechanism, designed in Week 3).
