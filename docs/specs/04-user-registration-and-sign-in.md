# Spec 04 — User registration, sign-in and personal page

Requirements: [week-02](../requirements/week-02-authorization.md) W2-G1, W2-G2, S1–S3 ·
Design: [authentication](../design/authentication.md)
Tasks: T02-01, T02-04, T02-05, T02-06

Reduced 2026-11-13 (owner: Week 2 = the curriculum topic only): the group `admin` and the role line on the profile
(`GET /api/me`) are **moved to Week 3** (AC-04.3 and AC-04.7 withdrawn).

## Purpose

A visitor registers in the SPA with all required profile fields; the owner activates (confirms) the new account in the
Cognito console (owner decision 2026-11-13, no code confirmation in the SPA); the user signs in and out through
Amplify Auth against the Cognito User Pool and sees the own registration data, read-only, on Home `/` (ADR-013).

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

**Sign-in form** (`/sign-in`): `email`, `password` (non-empty). There is no confirm form: the SPA never asks for a
confirmation code (owner decision 2026-11-13).

**Configuration** (Amplify Hosting env vars and `.env.local`; public identifiers only):

| Name | Valid range | Required |
|---|---|---|
| `VITE_AWS_REGION` | the region of the Week 1 build (ADR-009) | yes for auth |
| `VITE_USER_POOL_ID` | `<region>_<id>` of `aws-challenge-users` | yes for auth |
| `VITE_USER_POOL_CLIENT_ID` | id of app client `aws-challenge-frontend-spa` | yes for auth |
| `VITE_API_URL` | invoke URL of `aws-challenge-api` (spec 05) | no — read by no Week 2 screen (the first API call from the SPA is Week 3); set or empty, the SPA makes no API request |

**User Pool configuration** (T02-01): as in [design/authentication](../design/authentication.md) §Proposed Solution;
attributes per the column "Cognito definition" above.

## Outputs

| Output | Structure | Guarantees |
|---|---|---|
| Sign-up result | message "Account created. It will be activated by an administrator; then you can sign in." with a link to `/sign-in` | shown after a successful `signUp`; Cognito user status `UNCONFIRMED` until the owner confirms it |
| Cognito user after activation by the owner | status `CONFIRMED`, the attributes from §Inputs with the values entered | `birthdate` in `YYYY-MM-DD`; `email_verified` is not guaranteed (no code is entered) |
| Session after sign-in | ID, access and refresh tokens held by Amplify | tokens never written to the console or logs |
| Profile on Home `/` (signed in) | read-only list: First name, Last name, Email, Gender, Date of birth (`DD/MM/YYYY`), Country (name + code), Height (cm), Weight (kg) | profile values from `fetchUserAttributes`; no role line (Week 3); no input elements, no edit or save action |
| Home `/` (anonymous) | short intro; links to `/sign-in` and `/sign-up` when auth is configured | no profile data, no API request |

## Behaviour

1. A visitor opens `/sign-up`, fills in the form; the SPA validates every field per §Inputs and shows field-level
   messages without calling Cognito while any field is invalid.
2. The SPA calls `signUp`; Cognito creates the user as `UNCONFIRMED`; the SPA shows the sign-up result message of
   §Outputs with a link to `/sign-in`. The SPA has no confirmation-code screen and never calls `confirmSignUp` or
   `resendSignUpCode`.
3. The owner confirms the user in the Cognito console ("Confirm account"). While Cognito-assisted verification is on,
   Cognito may still e-mail a code; it is not used (the owner may switch the verification off).
4. The user signs in with e-mail and password (SRP); the SPA navigates to Home `/`.
5. Home `/` shows the signed-in user's profile: attributes from `fetchUserAttributes` through TanStack Query.
6. "Sign out" calls `signOut`; tokens are removed; the SPA navigates to `/sign-in`.
7. Without a session Home `/` shows the intro with sign-in / sign-up links and no profile data. `/me` and `/confirm`
   no longer exist; like every unknown path they redirect to `/`. Chat and Admin nav links are shown only to a
   signed-in user.
8. With empty `VITE_AWS_REGION` / `VITE_USER_POOL_*` values the auth routes and links are hidden and the home page renders (spec 01).
9. The SPA makes no API request, whatever `VITE_API_URL` is; `/chat` and `/admin` show "Not available yet".

## Edge Cases / Failure Modes

| Case | Expected result |
|---|---|
| E-mail already registered | message "An account with this e-mail already exists" with a link to sign in; no second user |
| Invalid date (`31/02/2000`), wrong format, future date, age < 13 | field error, `signUp` not called |
| Height/weight not an integer or out of range | field error, `signUp` not called |
| Sign-in of an unconfirmed user (`UserNotConfirmedException` or `nextStep.signInStep = CONFIRM_SIGN_UP`) | message "Your account is not activated yet"; the user stays on `/sign-in`, no session |
| Wrong password / unknown e-mail | one generic message "Incorrect e-mail or password" (no user enumeration) |
| An attribute missing or not parseable in Cognito (e.g. created outside the SPA) | the field shows "—"; the page does not crash |
| An attribute outside the SPA ranges, stored by a direct `SignUp` call (Q-14 C) | the stored value is shown as is (read-only); the page does not crash |
| `fetchUserAttributes` fails (network) | error message with a retry button; no stale data shown as current |
| Too many attempts (`LimitExceededException`) | generic "Too many attempts, try later" |

## Acceptance Criteria

AWS-side criteria are verified from evidence the owner provides (console screenshots, or outputs of commands the
owner runs); agents have no AWS access (CLAUDE.md §3.11). AC-04.4, AC-04.10 and AC-04.11 are verified locally.

- [ ] AC-04.1 The User Pool `aws-challenge-users` shows: `UsernameAttributes=[email]` (e-mail verification is not
  checked: the owner confirms users in the console, decision 2026-11-13), self sign-up allowed, deletion protection
  active, required standard attributes `email`, `given_name`, `family_name`, `gender`, `birthdate`, and custom attributes `country` (String), `height` (Number), `weight`
  (Number) created without min/max constraints (Q-14 C: the runbook leaves the min/max fields empty;
  `height`/`weight` show no min/max value; Cognito defaults, if shown, are accepted); no Lambda triggers
- [ ] AC-04.2 The app client `aws-challenge-frontend-spa` shows no client secret, explicit auth flows
  `ALLOW_USER_SRP_AUTH` and `ALLOW_REFRESH_TOKEN_AUTH` (plus `ALLOW_USER_AUTH` with password only, accepted as built
  2026-11-13; no other flow), `PreventUserExistenceErrors=ENABLED`, token validity as in ARCHITECTURE §3.4, read and
  write permission on every registration attribute (a sign-up through the SPA that stores all eight values and a
  profile that shows them count as evidence)
- ~~AC-04.3~~ *Withdrawn 2026-11-13 — group `admin` moved to Week 3.*
- [ ] AC-04.4 The sign-up form (the only enforcement of the ranges, Q-14 C) rejects, without a network call to
  Cognito, each of: empty first name, gender `X`,
  date `31/02/2000`, a date less than 13 years ago, height `49`, height `170.5`, weight `301`, mismatched password
  confirmation (checked in the browser network tab or a component test)
- [ ] AC-04.5 A valid sign-up with a new e-mail shows "Account created. It will be activated by an administrator; then
  you can sign in." with a link to sign-in, and the SPA shows no code input; the user in the Cognito console shows
  `UserStatus=UNCONFIRMED` and all eight values, `birthdate` as `YYYY-MM-DD`; the owner confirms it in the Cognito
  console ("Confirm account") and it then shows `UserStatus=CONFIRMED`
- [ ] AC-04.6 Sign-in with that confirmed account lands on Home `/`, which shows all eight values (date as
  `DD/MM/YYYY`, country as name + code) and contains no input, edit or save control
- ~~AC-04.7~~ *Withdrawn 2026-11-13 — role line from `GET /api/me` moved to Week 3.*
- [ ] AC-04.8 Without a session Home `/` shows the intro with sign-in / sign-up links and no profile data; `/me`
  redirects to `/`; after sign-out the SPA is on `/sign-in` and Home shows no profile data again
- [ ] AC-04.9 Signing in with an account the owner has not confirmed yet shows "Your account is not activated yet"
  and stays on `/sign-in`
- [ ] AC-04.10 With `VITE_AWS_REGION`, `VITE_USER_POOL_ID`, `VITE_USER_POOL_CLIENT_ID` and `VITE_API_URL` empty,
  `npm run preview` renders the home page without console errors, shows no auth, Chat or Admin links and makes no
  API request; `/chat` and `/admin` show "Not available yet"
- [ ] AC-04.11 `frontend/package.json` no longer contains `@aws-amplify/ui-react` (ADR-014)
