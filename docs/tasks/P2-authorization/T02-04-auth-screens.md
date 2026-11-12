---
id: T02-04
title: "Amplify Auth config, sign-up / confirm / sign-in / sign-out screens, route guard"
phase: P2-authorization
status: Blocked
agent: frontend
skills: [react-expert]
depends_on: [T00-04, T02-01]
blocked_by: [Q-14]
design: ../../design/authentication.md
spec: ../../specs/04-user-registration-and-sign-in.md
acceptance: [AC-04.4, AC-04.5, AC-04.8, AC-04.9, AC-04.10, AC-04.11]
---
# T02-04 — Amplify Auth config, sign-up / confirm / sign-in / sign-out screens, route guard

> **BLOCKED** by [Q-14](../../RISKS.md#q-14).

## // BUSINESS CONTEXT

W2-G1: a visitor must be able to register with all eight required fields, confirm the e-mail and sign in. Client-side
validation is what keeps bad data out in practice (Q-14 A), so the rules must match spec 04 exactly.

## // TECHNICAL CONSTRAINTS

- ADR-014: own screens on `aws-amplify/auth` (`signUp`, `confirmSignUp`, `resendSignUpCode`, `signIn`, `signOut`,
  `fetchAuthSession`/`getCurrentUser`); remove `@aws-amplify/ui-react` and its CSS import.
- Field list, attribute mapping, ranges and messages exactly as spec 04 §Inputs and §Edge Cases (accepted Q-14
  answer); date entered `DD/MM/YYYY`, sent `YYYY-MM-DD`; country codes ISO 3166-1 alpha-2 with names from
  `Intl.DisplayNames`.
- Routes `/sign-up`, `/confirm`, `/sign-in`, guarded `/me` (the page content is T02-05; a placeholder is enough here).
- Configuration only from `VITE_*`; with empty values auth routes are hidden and the home page renders.
- No styling beyond semantic HTML; no colour/font/spacing literals (CLAUDE.md §5).
- Never log tokens or form values to the console.
- If a test runner is introduced for the validation tests, it is a new dev dependency and is described in the skill
  file (skills ownership rule).
- Pre-task invariants: `npm run build` green.

## // SCOPE

**Implement**
- Amplify configuration, the three screens, sign-out, route guard with return to the requested page
- Validation functions with tests covering the AC-04.4 cases
- Skill file `amplify-auth` (configuration, `VITE_*` names, auth API calls used, error mapping; skills ownership rule)

**Exclude**
- Personal page content and API client changes (T02-05), forgot-password flow, admin and chat pages, styling

**Interfaces that must match**
- Cognito attribute names as spec 04 §Inputs; env var names as spec 04 §Inputs; route paths as
  [design/authentication](../../design/authentication.md).

## Definition of Done

- [ ] Build green; AC-04.4, AC-04.10, AC-04.11 verified locally
- [ ] AC-04.5, AC-04.8, AC-04.9 verified against the dev User Pool (`npm run dev` or the Amplify URL), evidence in Notes
- [ ] Skill file added
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes
