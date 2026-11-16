---
id: T03-05
title: "Sync chain: EventBridge bus and rule, trigger function, Cognito trigger, Sync Lambda code upload (console runbook)"
phase: P3-rest-api-data
status: Todo
agent: devops
skills: [cloud-architect, cognito-user-pool]
depends_on: [T03-03, T03-04]
blocked_by: []
design: ../../design/user-sync.md
spec: ../../specs/07-user-sync.md
acceptance: [AC-07.3, AC-07.4, AC-07.5, AC-07.6]
---
# T03-05 — Sync chain on AWS (console runbook)

## // BUSINESS CONTEXT

W3-G1, S2: the curriculum's chain Cognito → EventBridge → Lambda goes live; from then on every confirmed user is
copied to PostgreSQL, and existing users are back-filled.

## // TECHNICAL CONSTRAINTS

- No AWS access for the agent (CLAUDE.md §3.11): console runbook in Notes; owner evidence (account id masked, log
  screenshots without personal values).
- Settings exactly as design user-sync §3: bus `aws-challenge-events` (no archive), rule
  `aws-challenge-user-confirmed` (pattern, target, retry 1 h / 5), function `aws-challenge-post-confirmation` (Python
  3.12, **no VPC**, 256 MB, 5 s, env `EVENT_BUS_NAME`, role `events:PutEvents` on the bus ARN only), PostConfirmation
  trigger on the pool. Log retention 14 days; tags per CLAUDE.md §7.
- `aws-challenge-sync`: **code upload only** (zip from T03-04); its configuration, env vars and role were set by
  T03-03. After the upload the Test-tab event `{"action":"status"}` must still return `{"current":1,"pending":[]}`
  (proves the migration files are byte-identical and the runner still reachable).
- Code only from the zips built by T03-04 (R-15). Trigger changes take up to 70 s to apply (AWS docs).
- As-built values are taken from ENVIRONMENT.md (T03-03); if any is missing there, the runbook's first step asks the
  owner to read and report it.

## // SCOPE

**Implement**
- Runbook in the order: bus → trigger function + role → Cognito trigger → sync code upload + `status` check → rule; verify steps for
  AC-07.3 … AC-07.6 (new test user via the deployed SPA, confirm, check logs and the row)
- Re-sync / back-fill runbook (EventBridge *Send events*) and its run for every user confirmed before the trigger
  existed (AC-07.5)
- ENVIRONMENT.md: new "Sync chain (Week 3)" section; skills `user-sync` (as-built) and `cognito-user-pool` (trigger)
  updated

**Exclude**
- DLQ / on-failure destination (design: not in Week 3); attribute-change sync (R-12)

**Interfaces that must match**
- Names, event source/detail-type and env vars as spec 07 and design user-sync.

## Definition of Done

- [ ] Runbook executed; AC-07.3 … AC-07.6 evidence in Notes; trigger cold-start duration recorded (R-02)
- [ ] ENVIRONMENT.md and skills updated; ARCH review passed
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

- 2026-11-13: created by Week 3 planning; `Blocked` by Q-17 and Q-18. AC-07.4's last step (row visible in the admin
  table) needs T03-07/T03-08; until then the row is shown by the sync log `inserted` and checked again in T03-10.
- 2026-11-13: Q-17 A and Q-18 A accepted by the owner (ADR-016, ADR-006 revised); design user-sync `Accepted` →
  `Todo` (waits for T03-03, T03-04 `Done`).
- 2026-11-16 (ARCH, owner decisions): `sync` configuration (timeout 60 s, env, role) moved to T03-03, which also runs
  the first migration through `sync`; this task only uploads the upsert version of the code. AC-06.6 (sync part) moved
  to T03-03; spec 06 dropped from this task. Runtime Python 3.12 for both functions (ADR-015 revised).
