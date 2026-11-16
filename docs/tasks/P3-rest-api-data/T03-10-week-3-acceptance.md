---
id: T03-10
title: "Week 3 acceptance check"
phase: P3-rest-api-data
status: Todo
agent: tester
skills: [test-master]
depends_on: [T03-01, T03-02, T03-03, T03-04, T03-05, T03-06, T03-07, T03-08, T03-09]
blocked_by: []
design: null  # acceptance task, verifies specs 06-09 and the spec 01/04/05 regressions
spec: [../../specs/01-spa-delivery.md, ../../specs/06-users-table-and-migrations.md, ../../specs/07-user-sync.md, ../../specs/08-admin-api.md, ../../specs/09-admin-page-and-role.md]
acceptance: [AC-06.1, AC-06.2, AC-06.3, AC-06.4, AC-06.5, AC-06.6, AC-07.1, AC-07.2, AC-07.3, AC-07.4, AC-07.5, AC-07.6, AC-08.1, AC-08.2, AC-08.3, AC-08.4, AC-08.5, AC-08.6, AC-08.7, AC-08.8, AC-08.9, AC-09.1, AC-09.2, AC-09.3, AC-09.4, AC-09.5, AC-01.2]
---
# T03-10 — Week 3 acceptance check

## // BUSINESS CONTEXT

Week 3 ("REST API + data") is done only when the chain sign-up → owner confirms → row in PostgreSQL → admin table,
the 401/403 rules and the logs are proven on `dev` by someone other than the implementer. The report is what the
owner shows to the mentor.

## // TECHNICAL CONSTRAINTS

- No AWS access for the agent (CLAUDE.md §3.11). Local ACs (pytest of each function, zip builds, `npm test`,
  `npm run build`, repository contents, `git grep` for secrets) run by the tester; AWS-side ACs from owner evidence;
  public unauthenticated probes (`curl` without a token) allowed.
- Evidence already in T03-01 … T03-09 Notes is reused by pointer; only missing evidence is requested.
- Each AC: pass / fail / not verifiable + source + trimmed output; account ids masked; no tokens; no personal data of
  test users beyond the e-mail domain.
- Regression: spec 04 AC-04.10, spec 05 AC-05.3 (on the new routes), spec 01 AC-01.1/AC-01.2.

## // SCOPE

**Implement**
- Owner checklist for missing evidence; report table AC → result → evidence in Notes

**Exclude**
- Fixing defects (reported to the owning task), E2E suite

**Interfaces that must match**
- AC numbering exactly as in the specs.

## Definition of Done

- [ ] All listed ACs pass, or failures are recorded against their tasks and the owner decides
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

- 2026-11-13: created by Week 3 planning.
