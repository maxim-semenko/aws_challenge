# Design — Authentication (Cognito User Pool + Amplify Auth + SPA screens)

Status: **Accepted** (2026-11-12, owner), with ADR-004; Q-14 answered (option C).
Requirements: [week-02](../requirements/week-02-authorization.md) W2-G1, W2-G2, W2-G4 (role), S1–S3 ·
Spec: [04-user-registration-and-sign-in](../specs/04-user-registration-and-sign-in.md)
Architecture: [ARCHITECTURE.md](../ARCHITECTURE.md) §3.1, §3.4, §5.1, ADR-004, ADR-013, ADR-014, goal G3
Related design: [api-gateway-auth](api-gateway-auth.md) (HTTP API, `/api/me`)

## Problem Statement

A visitor must register with eight profile fields (first and last name, e-mail, gender `F`/`M`, date of birth
`DD/MM/YYYY`, country of living, height in cm, weight in kg), confirm the e-mail, sign in and see a read-only
personal page with that data. An administrator role must exist. Today the SPA only has a draft that wraps everything
in the Amplify `Authenticator` with the e-mail field only; it adds ~317 kB of CSS
(T00-04 Notes). No User Pool exists, and its attribute schema cannot be changed after creation. Copying users into
PostgreSQL is Week 3 (curriculum), so this week Cognito is the only store of the profile (ADR-013).

## Proposed Solution

```mermaid
sequenceDiagram
    participant B as Browser (SPA)
    participant C as Cognito User Pool
    participant A as HTTP API + admin Lambda
    B->>C: SignUp(email, password, attributes)
    C-->>B: code sent by e-mail
    B->>C: ConfirmSignUp(email, code)
    C-->>B: confirmed
    B->>C: SignIn (SRP)
    C-->>B: ID, access, refresh tokens
    B->>C: GetUser (fetchUserAttributes, access token)
    C-->>B: profile attributes
    B->>A: GET /api/me, Authorization: Bearer <access token>
    A-->>B: id, groups (role line)
```

**User Pool** (`aws-challenge-users`, region per ADR-009; created by the owner in the console from the T02-01
runbook, Q-12 C):

| Setting | Value |
|---|---|
| Feature plan | Lite (no managed login, no threat protection needed); confirm the plan name and price at creation |
| Sign-in | e-mail is the username attribute (`UsernameAttributes=[email]`), case-insensitive |
| Self sign-up | enabled; verification of `email` by code (`AutoVerifiedAttributes=[email]`) |
| Password policy | Cognito default (ARCHITECTURE §3.4) |
| Attributes | [Q-14](../RISKS.md#q-14) option C: required standard attributes, custom attributes without min/max constraints, validation only in the SPA; field table in spec 04 §Inputs |
| E-mail sender | Cognito default sender ([R-13](../RISKS.md#2-risk-register)) |
| MFA, social logins, hosted UI | off (out of scope, ARCHITECTURE §1) |
| Deletion protection | on (the schema is immutable; an accidental delete loses every user) |
| Group | `admin` |
| Lambda triggers | none in Week 2 (the sync chain is Week 3) |

**App client** `aws-challenge-frontend-spa`: public (no secret); auth flows `ALLOW_USER_SRP_AUTH`, `ALLOW_REFRESH_TOKEN_AUTH`;
prevent user existence errors on; token validity per ARCHITECTURE §3.4; read and write permission on every
registration attribute (write is needed by `SignUp`, read by `fetchUserAttributes`; consequence
[R-12](../RISKS.md#2-risk-register)).

**First administrator:** the owner signs up through the SPA (or creates the user in the Cognito console if the
screens are not ready yet), then adds it to the group `admin` in the Cognito console (T02-03 runbook). The group
appears in tokens after the next sign-in or token refresh.

**SPA (ADR-014):** own screens on `aws-amplify/auth`; `@aws-amplify/ui-react` removed. No styling beyond semantic
HTML until the design system exists (CLAUDE.md §5).

| Route | Access | Content |
|---|---|---|
| `/` | public | home page (existing) |
| `/sign-up` | anonymous only | form with the 8 fields + password + password confirmation; client-side validation per spec 04 |
| `/confirm` | anonymous only | e-mail (pre-filled) + 6-digit code; "resend code" |
| `/sign-in` | anonymous only | e-mail + password; an unconfirmed user is sent to `/confirm` |
| `/me` | signed in | personal page: the 8 fields from `fetchUserAttributes`, date shown as `DD/MM/YYYY`, role line from `GET /api/me`, read-only |
| other existing routes (`/chat`, `/admin`) | unchanged in Week 2 | — |

- Amplify is configured once at start-up from the `VITE_*` variables of spec 04 §Inputs; with empty values auth routes are hidden and the home page still renders
  (spec 01).
- A route guard checks the session (`fetchAuthSession` / `getCurrentUser`); an anonymous visit to `/me` redirects to
  `/sign-in` and back after sign-in. After sign-in the user lands on `/me`.
- The date of birth is entered as `DD/MM/YYYY` and sent to Cognito as `YYYY-MM-DD`; the country is a select of
  ISO 3166-1 alpha-2 codes, names via `Intl.DisplayNames` (no hand-written name list).
- The API client sends the **access** token (ADR-004); `fetchUserAttributes` and `/api/me` are read through
  TanStack Query. The role line is the visible proof of the chain SPA → API Gateway → Lambda.

## Alternatives Considered

| Topic | Option | Pros | Cons | Verdict |
|---|---|---|---|---|
| Auth UI | Own screens on `aws-amplify/auth` (ADR-014) | small bundle; full control of date/country/number fields | more code than the Authenticator | **accepted (ADR-014)** |
| Auth UI | `Authenticator` without its stylesheet | little code | unstyled, custom fields via `formFields`/`services.handleSignUp` workarounds | rejected |
| Auth UI | Cognito managed login (hosted UI) + OAuth code flow | no form code | needs a domain and redirect flow; custom date format impossible | rejected |
| Personal page data | `fetchUserAttributes` (Cognito `GetUser` with the access token) | always current; standard Amplify API; no backend needed | one Cognito call per page load | **proposed** |
| Personal page data | ID token claims (`fetchAuthSession().tokens.idToken.payload`) | no network call | values frozen until the token is refreshed; custom attributes as strings | alternative |
| Personal page data | `GET /api/me` from a PostgreSQL copy | one read path for user and admin | the copy is Week 3 (curriculum) | moved to Week 3 (ADR-013) |
| Role on the personal page | `groups` from `GET /api/me` | exercises the protected API from the SPA | page depends on the API for one line | **proposed** |
| Role on the personal page | `cognito:groups` from the access token in the SPA | no API call | the SPA never calls the API in Week 2 | alternative |
| Field validation (Q-14) | A: SPA + min/max constraints on the custom attributes in Cognito | Cognito rejects out-of-range custom values | ranges frozen with the pool; `gender`/`birthdate` still unchecked server-side | rejected |
| Field validation (Q-14) | B: A + PreSignUp Lambda trigger validating every field | true server-side validation | extra synchronous trigger (5 s limit) and function, beyond the week topic | rejected |
| Field validation (Q-14) | C: SPA only; custom attributes without min/max in Cognito | ranges can change later without a new pool | no server-side bound at all (§Security Considerations) | **accepted** (owner, 2026-11-12) |
| Country attribute | `custom:country` (ISO alpha-2) | simple | custom attribute, immutable; length not constrained (Q-14 C) | **accepted** |
| Country attribute | standard `address` (JSON `country` field) | standard claim | JSON string, no length constraint | rejected |

## API Design

No HTTP endpoint is defined here (see [api-gateway-auth](api-gateway-auth.md)). Cognito operations used by the SPA
through `aws-amplify/auth`: `signUp`, `confirmSignUp`, `resendSignUpCode`, `signIn`, `signOut`, `fetchAuthSession`,
`getCurrentUser`, `fetchUserAttributes`. Field names, types, ranges and the mapping to Cognito attributes: spec 04
§Inputs. Amplify Hosting environment variables: spec 04 §Inputs "Configuration" (public identifiers, no secrets).

## Affected Components

New: Cognito User Pool, app client, group `admin` (T02-01); skill files `cognito-user-pool`, `amplify-auth`,
`spa-api-client`. Changed: `frontend/src` (Amplify config, routes, auth screens, personal page, API client),
`frontend/package.json` (remove `@aws-amplify/ui-react`), `frontend/vite.config.ts` (remove the `/api` proxy to the
deleted local backend), Amplify Hosting environment variables.

## Security Considerations

- Public app client without secret; SRP — the password never leaves the browser in clear.
- Tokens are held by Amplify in browser storage (default `localStorage`): any XSS can read them. Mitigation in Week 2:
  no `dangerouslySetInnerHTML`, no third-party scripts; CSP is a later item.
- Field validation exists only in the SPA (Q-14 C): Cognito checks no range or format of `gender`, `birthdate` or the
  custom attributes, and custom attributes cannot be required. A direct call to the public `SignUp` (or
  `UpdateUserAttributes`) API with the app client id can therefore store out-of-range values or omit custom
  attributes. Accepted for Week 2; the personal page shows stored values as they are (spec 04), and the Week 3 sync
  must tolerate such values ([R-11, R-12](../RISKS.md#2-risk-register)).
- Profile data (name, gender, birth date, country, height, weight) is personal data: it stays in Cognito and the
  browser; the SPA never logs tokens or profile data to the console.
- `admin` membership only by the owner in the Cognito console; the SPA never decides authorisation (the API does; the role
  line is display only).
- User existence errors are suppressed for sign-in; sign-up still reports an existing e-mail (Cognito behaviour) —
  accepted.
- Deletion protection on the pool.

## Cost

No always-on resources. Cognito Lite: free up to 10 000 monthly active users (AWS pricing page, to be re-checked at
creation); the learning workload stays far below. Default e-mail sender: no charge.

## Open Questions

None. Resolved 2026-11-12 by the owner: [Q-14](../RISKS.md#q-14) (option C), ADR-004 (Accepted).
