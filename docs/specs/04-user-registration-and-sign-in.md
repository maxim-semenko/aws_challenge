# Spec 04 — User registration, sign-in and personal page

Requirements: [week-02](../requirements/week-02-authorization.md) W2-G1, W2-G2, W2-G4 (role), S1–S3 ·
Design: [authentication](../design/authentication.md)
Tasks: T02-01, T02-03, T02-04, T02-05, T02-06

## Purpose

A visitor registers in the SPA with all required profile fields, confirms the e-mail, signs in and out through Amplify
Auth against the Cognito User Pool, and sees a read-only personal page with the registration data read from Cognito
(ADR-013). The `admin` group exists and has at least one member.

## Inputs

**Sign-up form** (`/sign-up`) — every field the SPA sends to Cognito `SignUp`. This table is the single home of the
registration fields, their Cognito definition and their ranges ([Q-14](../RISKS.md#q-14) answered 2026-11-12, option C:
**all validation is in the SPA**; Cognito enforces no range on any of these values). The sign-in attribute, the set of
required standard attributes and every custom attribute (name, type, constraints) cannot be changed after the User
Pool exists; custom attributes cannot be marked required.

| UI field | Sent as (Cognito) | Cognito definition (T02-01) | Type | Valid range (checked by the SPA) | Required |
|---|---|---|---|---|---|
| First name | `given_name` | standard, required | string | trimmed, 1..50 characters; Unicode letters, space, `-`, `'` | yes |
| Last name | `family_name` | standard, required | string | same as first name | yes |
| Email | `username` and `email` | standard, required; sign-in (username) attribute, auto-verified | string | e-mail syntax, ≤ 254 characters; stored lower-case by Cognito (case-insensitive pool) | yes |
| Password | `password` | — (pool password policy) | string | Cognito default policy (ARCHITECTURE §3.4) | yes |
| Confirm password | — (not sent) | — | string | equals Password | yes |
| Gender | `gender` | standard, required; value not validated by Cognito | string | exactly `F` or `M` (select) | yes |
| Date of birth | `birthdate` | standard, required; string `YYYY-MM-DD` (OIDC), range not validated by Cognito | string | entered `DD/MM/YYYY`, a real calendar date between 1900-01-01 and today minus 13 years; sent as `YYYY-MM-DD` | yes |
| Country of living | `custom:country` | custom, String, **no min/max length** | string | ISO 3166-1 alpha-2 code, upper case, chosen from a list (names via `Intl.DisplayNames`) | yes |
| Height, cm | `custom:height` | custom, Number, **no min/max value** | integer as string | 50..250 | yes |
| Weight, kg | `custom:weight` | custom, Number, **no min/max value** | integer as string | 20..300 | yes |

No other attribute is sent; unknown fields are not possible from the form. A direct call to the Cognito `SignUp` API
(outside the SPA) can store out-of-range values or omit the custom attributes; readers of the profile must tolerate
that (design [authentication](../design/authentication.md) §Security Considerations, R-11, R-12).

**Confirm form** (`/confirm`): `email` (pre-filled from sign-up, editable), `code` — string of exactly 6 digits.
**Sign-in form** (`/sign-in`): `email`, `password` (non-empty).

**Configuration** (Amplify Hosting env vars and `.env.local`; public identifiers only):

| Name | Valid range | Required |
|---|---|---|
| `VITE_AWS_REGION` | the region of the Week 1 build (ADR-009) | yes for auth |
| `VITE_USER_POOL_ID` | `<region>_<id>` of `aws-challenge-users` | yes for auth |
| `VITE_USER_POOL_CLIENT_ID` | id of app client `aws-challenge-frontend-spa` | yes for auth |
| `VITE_API_URL` | invoke URL of `aws-challenge-api` (spec 05) | yes for the role line on `/me` |

**User Pool configuration** (T02-01): as in [design/authentication](../design/authentication.md) §Proposed Solution;
attributes per the column "Cognito definition" above.

## Outputs

| Output | Structure | Guarantees |
|---|---|---|
| Cognito user after confirmation | status `CONFIRMED`, `email_verified=true`, the attributes from §Inputs with the values entered | `birthdate` in `YYYY-MM-DD` |
| Session after sign-in | ID, access and refresh tokens held by Amplify | tokens never written to the console or logs |
| Personal page `/me` | read-only list: First name, Last name, Email, Gender, Date of birth (`DD/MM/YYYY`), Country (name + code), Height (cm), Weight (kg); line "Role: administrator" or "Role: user" | profile values from `fetchUserAttributes`; role from `groups` of `GET /api/me` (spec 05); no input elements, no edit or save action |
| Group `admin` | Cognito group with ≥ 1 member (the owner) | assigned only by the owner in the Cognito console |

## Behaviour

1. A visitor opens `/sign-up`, fills in the form; the SPA validates every field per §Inputs and shows field-level
   messages without calling Cognito while any field is invalid.
2. The SPA calls `signUp`; Cognito sends a 6-digit code to the e-mail; the SPA navigates to `/confirm`.
3. The user enters the code; the SPA calls `confirmSignUp`; Cognito confirms the user.
4. On success the SPA navigates to `/sign-in` (or signs in automatically if Amplify `autoSignIn` is used — the task
   records which).
5. The user signs in with e-mail and password (SRP); the SPA navigates to `/me`.
6. `/me` loads the attributes with `fetchUserAttributes` and `GET /api/me` with the **access** token (ADR-004), both
   through TanStack Query, and renders the fields and the role.
7. "Sign out" calls `signOut`; tokens are removed; the SPA navigates to `/sign-in`.
8. A visit to `/me` without a session redirects to `/sign-in` and returns to `/me` after sign-in.
9. With empty `VITE_AWS_REGION` / `VITE_USER_POOL_*` values the auth routes and links are hidden and the home page renders (spec 01).

## Edge Cases / Failure Modes

| Case | Expected result |
|---|---|
| E-mail already registered | message "An account with this e-mail already exists" with a link to sign in; no second user |
| Invalid date (`31/02/2000`), wrong format, future date, age < 13 | field error, `signUp` not called |
| Height/weight not an integer or out of range | field error, `signUp` not called |
| Wrong confirmation code | message "Invalid code", user stays `UNCONFIRMED`, can retry |
| Expired code / code not received | "Resend code" calls `resendSignUpCode`; quota limits per R-13 shown as a generic error |
| Sign-in of an unconfirmed user | SPA navigates to `/confirm` with the e-mail pre-filled |
| Wrong password / unknown e-mail | one generic message "Incorrect e-mail or password" (no user enumeration) |
| An attribute missing or not parseable in Cognito (e.g. created outside the SPA) | the field shows "—"; the page does not crash |
| An attribute outside the SPA ranges, stored by a direct `SignUp` call (Q-14 C) | the stored value is shown as is (read-only); the page does not crash |
| `fetchUserAttributes` fails (network) | error message with a retry button; no stale data shown as current |
| `GET /api/me` → 401 (token expired and refresh failed) | session cleared, redirect to `/sign-in` |
| `GET /api/me` → 5xx / network error, or `VITE_API_URL` empty | profile still shown; role line shows "Role: unavailable" |
| Too many attempts (`LimitExceededException`) | generic "Too many attempts, try later" |

## Acceptance Criteria

AWS-side criteria are verified from evidence the owner provides (console screenshots, or outputs of commands the
owner runs); agents have no AWS access (CLAUDE.md §3.11). AC-04.4, AC-04.10 and AC-04.11 are verified locally.

- [ ] AC-04.1 The User Pool `aws-challenge-users` shows: `UsernameAttributes=[email]`, `AutoVerifiedAttributes=[email]`,
  self sign-up allowed, deletion protection active, required standard attributes `email`, `given_name`,
  `family_name`, `gender`, `birthdate`, and custom attributes `country` (String), `height` (Number), `weight`
  (Number) created without min/max constraints (Q-14 C: the runbook leaves the min/max fields empty;
  `height`/`weight` show no min/max value; Cognito defaults, if shown, are accepted); no Lambda triggers
- [ ] AC-04.2 The app client `aws-challenge-frontend-spa` shows no client secret, explicit auth flows exactly
  `ALLOW_USER_SRP_AUTH` and `ALLOW_REFRESH_TOKEN_AUTH`, `PreventUserExistenceErrors=ENABLED`, token validity as in
  ARCHITECTURE §3.4, read and write permission on every registration attribute
- [ ] AC-04.3 Group `admin` exists and lists the owner's account as a member
- [ ] AC-04.4 The sign-up form (the only enforcement of the ranges, Q-14 C) rejects, without a network call to
  Cognito, each of: empty first name, gender `X`,
  date `31/02/2000`, a date less than 13 years ago, height `49`, height `170.5`, weight `301`, mismatched password
  confirmation (checked in the browser network tab or a component test)
- [ ] AC-04.5 A valid sign-up with a new e-mail → code e-mail received → confirm → the user in the Cognito console shows
  `UserStatus=CONFIRMED`, `email_verified=true` and all eight values, `birthdate` as `YYYY-MM-DD`
- [ ] AC-04.6 Sign-in with that account lands on `/me`, which shows all eight values (date as `DD/MM/YYYY`) and
  contains no input, edit or save control
- [ ] AC-04.7 The request `GET /api/me` from the SPA carries `Authorization: Bearer <token>` whose decoded payload has
  `token_use=access`; `/me` shows "Role: administrator" for a member of `admin` and "Role: user" otherwise
- [ ] AC-04.8 Opening `/me` without a session redirects to `/sign-in`; after sign-out, `/me` redirects again
- [ ] AC-04.9 Signing in with an unconfirmed account navigates to `/confirm`; "Resend code" delivers a new code
- [ ] AC-04.10 With `VITE_AWS_REGION`, `VITE_USER_POOL_ID`, `VITE_USER_POOL_CLIENT_ID` empty, `npm run preview` renders the home page without console errors and
  shows no auth links
- [ ] AC-04.11 `frontend/package.json` no longer contains `@aws-amplify/ui-react` (ADR-014)
