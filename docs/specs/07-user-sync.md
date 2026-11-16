# Spec 07 — User sync: Cognito → EventBridge → Sync Lambda → PostgreSQL

Requirements: [week-03](../requirements/week-03-rest-api-data.md) W3-G1, W3-G5, S2, S8 ·
Design: [user-sync](../design/user-sync.md) §3, §4
Tasks: T03-04, T03-05, T03-10

Written against [Q-17](../RISKS.md#q-17) option A and [Q-18](../RISKS.md#q-18) option A — both accepted by the
owner on 2026-11-13 (ADR-016, ADR-006 revised). Revised 2026-11-16 (owner): `aws-challenge-sync` also hosts the
migration runner, so its handler first routes the event (dispatch table: [spec 06](06-users-table-and-migrations.md)
§Inputs); runtime Python 3.12 (ADR-015 revised). No AC changed.

## Purpose

When the owner confirms a user in Cognito, a `UserConfirmed` event goes through the EventBridge bus
`aws-challenge-events` to the Sync Lambda, which writes the user's row into `users` (spec 06) through RDS Proxy —
idempotently, tolerant of missing or odd values, and without ever blocking the confirmation.

## Inputs

**Cognito PostConfirmation event** to `aws-challenge-post-confirmation` (format defined by Cognito): used fields
`triggerSource`, `userPoolId`, `request.userAttributes`.

**EventBridge event** put by the trigger (and by the owner's re-sync runbook) on bus `aws-challenge-events`:

| Field | Type | Valid range | Required |
|---|---|---|---|
| `source` | string | `aws-challenge.cognito` | yes |
| `detail-type` | string | `UserConfirmed` | yes |
| `detail.version` | integer | `1` | yes |
| `detail.userPoolId` | string | the pool id | yes |
| `detail.sub` | string | UUID (Cognito `sub`) | yes |
| `detail.email` | string | non-empty | yes |
| `detail.attributes` | object | keys only from: `given_name`, `family_name`, `gender`, `birthdate`, `custom:country`, `custom:height`, `custom:weight`; values strings as stored in Cognito; a key may be missing | yes (may be `{}`) |
| `detail.confirmedAt` | string | ISO-8601 UTC | yes |

Unknown keys in `detail` or `detail.attributes` are ignored by the Sync Lambda.

**Configuration**: trigger — env `EVENT_BUS_NAME` = `aws-challenge-events`; sync — the DB variables of spec 06.

## Outputs

**Mapping into `users`** (columns: spec 06):

| Event field | Column | Rule |
|---|---|---|
| `sub` | `id` | must be a UUID, else the event is rejected |
| `email` | `email` | trimmed, lower-cased; empty → rejected |
| `given_name`, `family_name`, `gender`, `custom:country` | `given_name`, `family_name`, `gender`, `country` | stored as given; missing or empty string → NULL |
| `birthdate` | `birthdate` | valid calendar date `YYYY-MM-DD` → date; anything else → NULL (field name logged) |
| `custom:height`, `custom:weight` | `height_cm`, `weight_kg` | optional sign + digits within PostgreSQL `integer` → integer, **stored even if outside the SPA range**; anything else (e.g. `170.5`, `abc`) → NULL (field name logged) |
| `confirmedAt` | `confirmed_at` | parsed ISO-8601; invalid → NULL |

**Trigger return value**: the Cognito event, unchanged, in every case.

**Log lines** (one JSON object per invocation):

| Function | Fields |
|---|---|
| post-confirmation | `level`, `message`, `function`, `awsRequestId`, `triggerSource`, `userSub`, `outcome` (`published` / `publish_failed` / `ignored`), `durationMs`, `errorClass` |
| sync | `level`, `message`, `function`, `awsRequestId`, `eventId`, `userSub`, `outcome` (`inserted` / `updated` / `rejected` / `failure`), `invalidFields` (list of field names), `durationMs`, `errorClass` |

Never logged: e-mail, names, gender, birth date, country, height, weight, the event detail, tokens.

## Behaviour

1. The owner confirms a user (Cognito console *Confirm account* → `AdminConfirmSignUp`); Cognito invokes the
   PostConfirmation trigger with `triggerSource = PostConfirmation_ConfirmSignUp`.
2. The trigger builds the detail of §Inputs from `request.userAttributes` (allow-listed keys only), calls
   `PutEvents` once (one entry) and returns the event. Other trigger sources (`PostConfirmation_ConfirmForgotPassword`)
   → `outcome=ignored`, no event.
3. If `PutEvents` raises or reports `FailedEntryCount > 0`, the trigger logs `publish_failed` and still returns the
   event (the confirmation succeeds).
4. Rule `aws-challenge-user-confirmed` matches `source` and `detail-type` and invokes `aws-challenge-sync`
   asynchronously; the handler's dispatch (spec 06 §Inputs) routes the envelope to the upsert.
5. Sync validates `sub` and `email` (invalid → `rejected`, return normally), maps the values (§Outputs), and runs one
   parameterised `INSERT … ON CONFLICT (id) DO UPDATE` setting every mapped column and `updated_at = now()`, keeping
   `created_at`; `outcome` is `inserted` or `updated`.
6. A database error makes Sync raise → Lambda retries the async invocation (2 retries); after that the row is
   missing until the re-sync runbook.
7. Re-sync / back-fill: the owner sends the same event from the EventBridge console (*Send events*) with values copied
   from the user's Cognito attributes; step 5 applies.

## Edge Cases / Failure Modes

| Case | Expected result |
|---|---|
| Same event delivered twice | second run `updated`, row unchanged except `updated_at` |
| User signed up directly with `custom:height = 400`, no `custom:weight` | row stored, `height_cm = 400`, `weight_kg = NULL` |
| `birthdate = 31/02/2000` or `2000-02-31` | `birthdate = NULL`, `invalidFields` contains `birthdate` |
| `sub` not a UUID or `email` missing | `rejected`, no row, no retry |
| EventBridge `PutEvents` throttled / unreachable | trigger logs `publish_failed`; user confirmed; row missing → re-sync runbook |
| Trigger cold start | completes well under the 5 s Cognito limit (R-02); duration recorded |
| Proxy or DB unavailable | Sync `failure`, async retries; then re-sync runbook |
| User confirmed before the trigger existed | no row until the back-fill runbook |
| User later changes attributes (`UpdateUserAttributes`) | not synced (R-12) |
| Forgot-password confirmation | trigger `ignored`, no event |

## Acceptance Criteria

AWS-side criteria are verified from evidence the owner provides (console screenshots, log lines, Test-tab outputs);
agents have no AWS access (CLAUDE.md §3.11). AC-07.1 and AC-07.2 are verified locally.

- [ ] AC-07.1 `pytest` for `lambdas/post-confirmation` passes and covers: `PostConfirmation_ConfirmSignUp` → one
  `PutEvents` entry with exactly the §Inputs fields (allow-listed attributes only) and the event returned unchanged;
  `PutEvents` exception and `FailedEntryCount = 1` → `publish_failed`, event still returned, no exception;
  `PostConfirmation_ConfirmForgotPassword` → no `PutEvents`; the log line contains no attribute value
- [ ] AC-07.2 `pytest` for `lambdas/sync` passes and covers every row of §Outputs mapping and of §Edge Cases that
  concerns the handler (duplicate → `updated`; out-of-range height stored; invalid birthdate/height → NULL with
  `invalidFields`; bad `sub`/missing `email` → `rejected` without DB call; DB error → raises); SQL is parameterised
  (no value inside the SQL string)
- [ ] AC-07.3 Bus `aws-challenge-events`, rule `aws-challenge-user-confirmed` (pattern and target `aws-challenge-sync`,
  retry policy 1 h / 5) and the pool's PostConfirmation trigger = `aws-challenge-post-confirmation` exist; the trigger
  function has no VPC configuration and its role allows only `events:PutEvents` on the bus ARN plus logging; the sync
  role has `rds-db:connect` and no Secrets Manager permission (owner screenshots, account id masked)
- [ ] AC-07.4 End to end: a new user signs up in the deployed SPA, the owner confirms the account in the Cognito
  console; within 1 minute the trigger log shows `published` (with its `durationMs`) and the sync log shows
  `inserted` with the same `userSub`; the row is visible in the admin table (AC-09.3) with the eight values
- [ ] AC-07.5 Re-sync runbook: sending the same event again from the EventBridge console → sync log `updated`, still
  one row for that `sub`
- [ ] AC-07.6 The trigger and sync log lines of AC-07.4 contain no e-mail, name, birth date, country, height or weight
  value (owner screenshot of the log events)
