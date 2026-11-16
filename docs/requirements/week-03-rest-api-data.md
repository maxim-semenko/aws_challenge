# Requirements — Week 3: REST API + data

Source: challenge curriculum plan, row "Week 3 — REST API + data: Admin Lambda ↔ RDS Proxy, Sync chain Cognito →
EventBridge → Lambda" (screenshot provided by the owner, 2026-11-13). **No assignment page with goals or steps
exists**, so goals and steps below are **derived** from the topic line, the project requirements and the items moved
from Week 2 (PLAN.md). Derived items are marked `(derived)`; the owner confirms them by accepting the design docs.
This file is the input for design docs and specs; it is not edited except to fix the export.

## Topic (as given)

REST API + data: Admin Lambda ↔ RDS Proxy, Sync chain Cognito → EventBridge → Lambda.

## Project requirements relevant to this week (as given, translated)

- The administrator gets access to a page with the list of all users and their data in table form. Editing is not
  provided.
- After sign-in the user lands on a personal page that shows their data. Editing is not provided.

## Moved from Week 2 (owner decision 2026-11-13)

Admin Lambda Python code in Git (`lambdas/admin`); `/api/...` endpoints with an endpoint contract (CLAUDE.md §6);
group `admin` and 403 for non-admins; role line on the profile; API access log and handler logs; user sync to
PostgreSQL; users table and migrations (Q-16).

## Week goals (derived)

| # | Goal |
|---|---|
| W3-G1 | Every user confirmed in Cognito is stored in PostgreSQL through the chain Cognito → EventBridge → Sync Lambda → RDS Proxy |
| W3-G2 | The Admin Lambda reads users from PostgreSQL through RDS Proxy and serves them over the HTTP API with paging |
| W3-G3 | Only members of the Cognito group `admin` get the users list (others 403); every API call needs a valid token (401) |
| W3-G4 | The SPA admin page shows all users in a read-only table with paging; the profile shows the user's role |
| W3-G5 | The Lambda code lives in Git and is deployed from it; API and Lambda logs are in CloudWatch without personal data beyond CLAUDE.md §7 |

## Implementation steps (derived)

| # | Step |
|---|---|
| S1 | Users table and the migration approach (Q-16); apply the first migration to RDS |
| S2 | Sync chain: Cognito confirmation event → EventBridge rule → Sync Lambda (VPC) → RDS Proxy → idempotent upsert of the user row |
| S3 | Admin Lambda (Python, VPC) → RDS Proxy: `GET` current user and paginated users list; group check |
| S4 | HTTP API routes under `/api` with the JWT authorizer, integrated with the Admin Lambda |
| S5 | Database credentials for the Lambdas (Secrets Manager or IAM auth to RDS Proxy) and network path from the private subnets (R-09) |
| S6 | SPA: admin users table with paging; role line on the profile; admin link only for admins |
| S7 | Group `admin` in the User Pool; the owner's account added to it |
| S8 | Logs: API access log, structured Lambda logs |

## Traceability

| Requirement | Spec |
|---|---|
| W3-G1, S1, S5 | [06-users-table-and-migrations](../specs/06-users-table-and-migrations.md) |
| W3-G1, S2 | [07-user-sync](../specs/07-user-sync.md) |
| W3-G2, W3-G3, S3, S4, S7 | [08-admin-api](../specs/08-admin-api.md) |
| W3-G4, S6; project requirement "personal page shows the user's data" (role line) | [09-admin-page-and-role](../specs/09-admin-page-and-role.md); profile values: [04](../specs/04-user-registration-and-sign-in.md) (Q-19) |
| W3-G5, S8 | [06](../specs/06-users-table-and-migrations.md) (migrate log, no secrets), [07](../specs/07-user-sync.md) (sync logs), [08](../specs/08-admin-api.md) (access log, handler log) |
| Project requirement "admin page with all users, no editing" | [08](../specs/08-admin-api.md), [09](../specs/09-admin-page-and-role.md) |
