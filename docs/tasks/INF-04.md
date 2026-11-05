# INF-04 — AuthStack: Cognito User Pool

| Field | Value |
|---|---|
| Status | **Todo** |
| Epic | INF — infrastructure as code |
| Milestone | M1 |
| Role | OPS |
| Size | S |
| Depends on | [INF-01](INF-01.md) |
| Blocked by | — |
| Unblocks | [INF-06](INF-06.md), [BE-04](BE-04.md), [FE-02](FE-02.md) |
| Risks watched | — |
| Goals | G3 |
| References | ARCHITECTURE.md §3.4, ADR-011 |

## Goal

User sign-up/sign-in with email and an `admin` group.

## Scope

**In scope**

- User Pool: email sign-in, self sign-up, email verification, password policy
- Public app client (no secret), SRP flow, token lifetimes
- Group `admin`
- PostConfirmation trigger wired to the `sync` function alias (avoid circular stack dependency)
- Outputs: user pool id, client id

**Out of scope**

- Social logins, MFA, hosted UI branding

## Plan

- [ ] Implement the stack
- [ ] Decide where the trigger is wired (Auth or Compute) to avoid cycles
- [ ] Sign up a test user via CLI

## Definition of Done

- [ ] Test user can sign up, confirm and sign in
- [ ] Outputs are exported for the API and the SPA
- [ ] Status updated here and in [PLAN.md](../PLAN.md)

## Notes

_Decisions, measurements and findings made while working on the task._
