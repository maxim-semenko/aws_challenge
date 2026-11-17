---
id: T03-01
title: "Cognito group admin and the first administrator (console runbook)"
phase: P3-rest-api-data
status: Done
agent: devops
skills: [cloud-architect, cognito-user-pool]
depends_on: []
blocked_by: []
design: ../../design/admin-api.md
spec: ../../specs/08-admin-api.md
acceptance: [AC-08.2]
---
# T03-01 — Cognito group `admin` and the first administrator (console runbook)

## // BUSINESS CONTEXT

W3-G3, S7: the administrator role must exist before the API can tell admins from users (403 for everyone else) and
before the SPA can show the role. Membership is managed only by the owner.

## // TECHNICAL CONSTRAINTS

- No AWS access for the agent (CLAUDE.md §3.11): a console runbook in Notes, executed by the owner; evidence =
  screenshots without tokens.
- Group name exactly `admin`; no IAM role, no precedence needed (design admin-api §1). Pool identifiers only by
  pointer to [ENVIRONMENT.md](../../ENVIRONMENT.md#authentication-week-2-t02-01).
- The pool schema is immutable — the runbook touches only Groups (cognito-user-pool skill).
- The owner must sign out and in again afterwards so that the access token carries `cognito:groups`.

## // SCOPE

**Implement**
- Runbook: create group `admin`; add the owner's user; verify steps for AC-08.2
- Record the result in ENVIRONMENT.md §Authentication (group name, member count — no e-mail)
- Update the skill `cognito-user-pool` (group section; "Planned for Week 3" reduced accordingly)

**Exclude**
- Lambda trigger (T03-05), API routes (T03-07), SPA (T03-08)

**Interfaces that must match**
- Group name `admin` as checked by the handler (spec 08) and the SPA (spec 09).

## Definition of Done

- [ ] Runbook executed by the owner; AC-08.2 evidence in Notes
- [ ] ENVIRONMENT.md and skill updated; ARCH review passed
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

- 2026-11-13: created by Week 3 planning. Waits only for design admin-api `Accepted`.
- 2026-11-13: design admin-api `Accepted` by the owner — start gate holds.
- 2026-11-16: devops — runbook below written, status `In progress`; waits for the owner's execution and evidence.
  Cost: a Cognito group is free; no always-on resource → $0/month.

## Runbook (owner executes in the AWS console; agent has no AWS access)

Region `eu-west-1`. Pool: `aws-challenge-users` (id in [ENVIRONMENT.md](../../ENVIRONMENT.md#authentication-week-2-t02-01)).
Touch **only** Groups — nothing under Sign-up, Sign-in, attributes, app clients or Extensions.

**Step 1 — Create the group**

1. AWS console → **Amazon Cognito** → **User pools** → `aws-challenge-users`.
2. Left menu **User management → Groups** → **Create group**.
3. Fields:

   | Field | Value |
   |---|---|
   | Group name | `admin` (lower case, exactly) |
   | Description | `Administrators: read-only access to the user list (Week 3)` |
   | IAM role | leave empty (none) |
   | Precedence | leave empty |

4. **Create group**.

Report back: screenshot S1 of the Groups list showing `admin` (description, no IAM role).

**Step 2 — Add the owner's account**

1. Groups → click `admin` → section **Group members** → **Add user to group**.
2. Select the owner's own user (the account used on the deployed SPA; must be `Confirmed`) → **Add**.

Report back: screenshot S2 of the `admin` group page with *Group members* = 1 user. The e-mail may be masked or
cropped (it is not recorded anywhere; only the member count goes into ENVIRONMENT.md).

**Step 3 — Refresh the token**

On `https://main.d67fa9mmezz1k.amplifyapp.com`: **Sign out**, then **Sign in** again with the same account (the
access token issued before Step 2 has no `cognito:groups`; it would otherwise only change on refresh, ≤ 60 min).

**Step 4 — Verify the claim (optional, no token printed)**

Signed in on the deployed SPA, browser DevTools → Console, paste:

```js
const k = Object.keys(localStorage).find(x => x.startsWith('CognitoIdentityServiceProvider.') && x.endsWith('.accessToken'))
const p = JSON.parse(atob(localStorage.getItem(k).split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
console.log('token_use', p.token_use, 'groups', JSON.stringify(p['cognito:groups'] ?? []))
```

Expected output: `token_use access groups ["admin"]`. Report back: screenshot S3 of that one output line (nothing
else from the console). The end-to-end proof via `GET /admin` (200 for the admin) follows in T03-07 / AC-08.6 (ADR-018, 2026-11-17).

**Rollback:** Groups → `admin` → remove the member / **Delete group** (no other resource depends on it until T03-07).

### Verify — AC-08.2

| AC | Evidence | Pass when |
|---|---|---|
| AC-08.2 | S1, S2 (S3 supporting) | `admin` exists in `aws-challenge-users`; it has exactly 1 member, the owner's account; S3 shows `groups ["admin"]` |

### Evidence received

_(to be filled from the owner's report: date, S1, S2, S3 results)_
- 2026-11-16 (owner screenshot): group `admin` created 2026-11-16 17:11 (description "Administrators: read-only access to the user list (Week 3)", no IAM role, no precedence); 1 member — `test@gmail.com` (sub `725594e4-…`, Confirmed, Enabled). S1/S2 evidence for AC-08.2 received. Token check (`cognito:groups`) follows after re-sign-in, verified end to end by T03-07/T03-10.
- 2026-11-17: set to `Done` by the owner (Week 3 closed).
