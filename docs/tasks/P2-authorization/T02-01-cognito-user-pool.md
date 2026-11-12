---
id: T02-01
title: "Cognito User Pool, SPA app client and group admin"
phase: P2-authorization
status: In progress
agent: devops
skills: [cloud-architect]
depends_on: [T00-01]
blocked_by: []
design: ../../design/authentication.md
spec: ../../specs/04-user-registration-and-sign-in.md
acceptance: [AC-04.1, AC-04.2]
---
# T02-01 — Cognito User Pool, SPA app client and group admin

## // BUSINESS CONTEXT

W2-G1 starts here: without a User Pool nobody can register. The pool's sign-in attribute, required attributes and
custom attributes can never be changed after creation, so a mistake costs a new pool and every registered user —
the schema was fixed by the owner in Q-14 (option C, 2026-11-12).

## // TECHNICAL CONSTRAINTS

- No AWS access for the agent (CLAUDE.md §3.11): devops writes a step-by-step console runbook in Notes (page, field,
  exact value); the owner executes it in the console (region per ADR-009) and reports back ids and screenshots.
- Settings exactly as in [design/authentication](../../design/authentication.md) §Proposed Solution; attributes exactly
  as spec 04 §Inputs, column "Cognito definition" (Q-14 C: custom attributes without any min/max constraint).
- Names `aws-challenge-users`, `aws-challenge-frontend-spa`; tags `project`, `env`, `owner` (CLAUDE.md §7).
- App client without secret; no OAuth/hosted-UI configuration; no Lambda triggers; deletion protection on.
- Public identifiers only in Amplify env vars; nothing secret exists in this task.

## // SCOPE

**Implement**
- Console runbook for: User Pool, app client `aws-challenge-frontend-spa`, group `admin`
- Console runbook for Amplify Hosting env vars `VITE_AWS_REGION`, `VITE_COGNITO_USER_POOL_ID`,
  `VITE_COGNITO_USER_POOL_CLIENT_ID` (and the branch rebuild)
- In Notes: the owner's reported ids and ARNs (account id masked) and the owner's evidence for AC-04.1/04.2 (which
  console pages/fields to screenshot is part of the runbook)
- Skill file `cognito-user-pool` (pool settings, attribute schema and its immutability, adding a user to `admin`
  in the console, verification steps; skills ownership rule)

**Exclude**
- Lambda triggers (Week 3), SES, MFA, hosted UI/domain, adding members to `admin` (T02-03), IaC code (T00-03)

**Interfaces that must match**
- Attribute names and constraints exactly as spec 04 §Inputs (used by T02-04 and T02-05).
- Pool id, pool ARN, issuer URL and client id recorded in Notes for T02-03 and T02-04.

## Definition of Done

- [ ] Runbook executed by the owner; AC-04.1, AC-04.2 verified from the owner's evidence, recorded in Notes
- [ ] Monthly cost noted (expected $0, Lite plan)
- [ ] Skill file added; ARCH review passed
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

- 2026-11-12: the owner created the User Pool and the SPA app client in the console before the runbook was written,
  and set the `VITE_*` variables in Amplify. Ids recorded in [ENVIRONMENT.md](../../ENVIRONMENT.md#authentication-week-2-t02-01).
  Open: evidence for AC-04.1/AC-04.2 (sign-in attribute, required standard attributes, custom attributes
  `country`/`height`/`weight`, app client without secret, group `admin`) — owner's screenshots of the pool's
  "Sign-up" and "App clients" pages and the "Groups" page.
- 2026-11-12 (owner's screenshot of the pool's sign-up attributes): required standard attributes `birthdate`,
  `gender`, `given_name`, `family_name`; custom attributes `custom:country` String (0..2048), `custom:height` Number
  (0..2^1023), `custom:weight` Number (0..2^1023), all mutable — Cognito defaults, no own min/max, matches Q-14 C
  (AC-04.1 custom-attribute part ✔). `email` is not in the required list: acceptable only if `email` is the sign-in
  (username) attribute, which puts it on every user — to be confirmed with the "Sign-in" page. Still missing for
  AC-04.1/04.2: sign-in attribute, auto-verified email, self sign-up, deletion protection, pool name, app client
  secret / auth flows / user-existence errors / attribute permissions; AC-04.3 group `admin`.
- 2026-11-12 (owner's Overview and Sign-in screenshots): pool name `User pool - maudc4` (console default; convention
  wants `aws-challenge-users` — owner may use "Rename"), feature plan Essentials, region eu-west-1, created
  2026-11-12. Sign-in option Email ✔ (so `email` is on every user; the required-attribute gap above is closed).
  Choice-based sign-in (`USER_AUTH`) offers Password only, passwordless inactive, MFA off, devices not remembered.
  Still missing: auto-verified email + self sign-up (Sign-up page), deletion protection (Settings), app client
  (secret, auth flows, user-existence errors, attribute write permissions), group `admin`.
- 2026-11-12 (owner's screenshots): pool renamed to `aws-challenge-users` ✔; self-registration enabled ✔; deletion
  protection active ✔. App client `aws-challenge-frontend-spa` (actual name; docs aligned): no secret ✔, prevent user
  existence errors ✔, token revocation on, access/ID 60 min, refresh 5 days (ARCHITECTURE §3.4 aligned). Auth flows:
  SRP ✔, refresh ✔, plus `ALLOW_USER_AUTH` (choice-based sign-in, password only) — deviates from AC-04.2 "exactly".
  Amplify domain recorded in ENVIRONMENT.md. Still missing: auto-verified email, attribute write permissions,
  group `admin`.
