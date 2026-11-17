# Spec 09 — SPA: admin users table, role line, admin-only navigation

Requirements: [week-03](../requirements/week-03-rest-api-data.md) W3-G4, S6 ·
Design: [admin-api](../design/admin-api.md) §4
Tasks: T03-08, T03-10

Written against [Q-19](../RISKS.md#q-19) option A (profile values stay from Cognito), accepted by the owner on
2026-11-13, and ADR-018 (owner, 2026-11-17: the role comes from the access token, there is no `/api/me`; the users
list comes from `GET /admin`).
Extends [spec 04](04-user-registration-and-sign-in.md): Behaviour 9 there ("the SPA makes no API request") holds
only while `VITE_API_URL` is empty from Week 3 on.

## Purpose

An administrator opens Admin and sees all users in a read-only table with paging; every signed-in user sees the own
role on the profile card; the Admin link is shown only to administrators. The SPA reads server data only through
the API of spec 08; the role is read from the signed-in user's access token.

## Inputs

No form and no write request.

| Source | Used for |
|---|---|
| claim `cognito:groups` (string array; absent = no group) of the current access token (`fetchAuthSession`, no API call) | role line, Admin link |
| `GET /admin?page=<p>&size=20` (default sort; spec 08 §Outputs) | admin table |

User actions on `/admin`: **Previous** / **Next** buttons (change `page` by 1). Configuration: `VITE_API_URL`
(spec 04 §Inputs).

## Outputs

**Role line** (profile card on Home, signed in; independent of `VITE_API_URL`):

| Token groups | Text |
|---|---|
| contain `admin` | `Role: administrator` |
| otherwise (incl. claim absent) | `Role: user` |
| session / access token cannot be read | `Role: unavailable` |
| loading | nothing |

**Header:** the Admin link is rendered only when the signed-in user's token groups contain `admin`; Chat stays as in
spec 04. Both are display only — `GET /admin` enforces the group (spec 08).

**`/admin` page** — heading "Users", then one of:

| State | Content |
|---|---|
| `VITE_API_URL` empty | the existing placeholder "Not available yet — coming in a later week." and no request (AC-04.10) |
| not signed in | redirect to `/sign-in`, back to `/admin` after sign-in |
| loading | "Loading…" |
| 403 | "You do not have access to this page." (no table) |
| 5xx / network | "Users could not be loaded." with a **Retry** button; no stale data shown as current |
| `total = 0` | "No users yet." |
| data | table + paging line |

Table columns, in order: Email · First name · Last name · Gender · Date of birth (`DD/MM/YYYY`) · Country (name + code,
as the profile) · Height (cm) · Weight (kg) · Registered (`createdAt` as `DD/MM/YYYY`). `null` → "—"; values outside
the SPA ranges shown as stored. No input, edit, delete or save control.

Paging line: "Page <page+1> of <max(1, ceil(total/20))> · <total> users"; **Previous** disabled on the first page,
**Next** disabled on the last page.

## Behaviour

1. With a session, the SPA reads `cognito:groups` from the access token once per session (TanStack Query key
   `['groups', <userId>]`, no request); the role line and the header use it. A new sign-in reads it again.
2. `/admin` calls `GET /admin?page=<p>&size=20` with the access token (ADR-004; key `['admin','users',p]`); changing
   the page keeps the previous page visible until the next arrives.
3. 401 from any call → sign-out and `/sign-in` (rule of the `spa-api-client` skill); not retried. 403 → the no-access state; not
   retried.
4. Without `VITE_API_URL` the SPA makes no API request (spec 04 AC-04.10 unchanged).

## Edge Cases / Failure Modes

| Case | Expected result |
|---|---|
| Non-admin types `/admin` | request → 403 → "You do not have access to this page." |
| Admin just added to the group, old token | "Role: user", no Admin link, 403 until a new sign-in (spec 08) |
| User row with nulls or odd values | "—" or the stored value; no crash |
| Last page has fewer than 20 rows | rows shown, Next disabled |
| `total` shrinks between pages | page beyond the end shows an empty table with Previous enabled |

## Acceptance Criteria

AC-09.1 and AC-09.2 are verified locally; AC-09.3 … AC-09.5 on the deployed SPA from owner screenshots (agents have no
AWS access; screenshots show only test users' data).

- [ ] AC-09.1 `npm test` and `npm run build` pass; unit tests cover the role-line mapping from the token groups
  (`admin`, other group, claim absent, unreadable session), the request path `/admin?page=<p>&size=20`, the paging line
  (first/last page, `total = 0`), the cell formats (date, country, null → "—") and the `/admin` state selection
  (403, error, empty, data, no `VITE_API_URL`)
- [ ] AC-09.2 With all `VITE_*` empty, `npm run preview` still satisfies AC-04.10 (no API request; `/admin` shows the
  placeholder)
- [ ] AC-09.3 Signed in as the admin on the deployed SPA: the profile shows "Role: administrator", the header shows
  Admin, `/admin` shows the table with the columns of §Outputs, the paging line, and no edit control
- [ ] AC-09.4 Signed in as a non-admin: the profile shows "Role: user", the header has no Admin link, typing `/admin`
  shows "You do not have access to this page."
- [ ] AC-09.5 If at least 21 users exist on `dev`: Next shows page 2 and the paging line updates, Previous returns to
  page 1. With fewer users this AC is verified by the paging unit tests of AC-09.1 and the report says so
