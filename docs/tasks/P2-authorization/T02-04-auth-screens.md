---
id: T02-04
title: "Amplify Auth config, sign-up / confirm / sign-in / sign-out screens, route guard"
phase: P2-authorization
status: Review
agent: frontend
skills: [react-expert]
depends_on: [T00-04, T02-01]
blocked_by: []
design: ../../design/authentication.md
spec: ../../specs/04-user-registration-and-sign-in.md
acceptance: [AC-04.4, AC-04.5, AC-04.8, AC-04.9, AC-04.10, AC-04.11]
---
# T02-04 — Amplify Auth config, sign-up / confirm / sign-in / sign-out screens, route guard

## // BUSINESS CONTEXT

W2-G1: a visitor must be able to register with all eight required fields, confirm the e-mail and sign in. The SPA is
the only place where the field ranges are enforced (Q-14 C: Cognito has no min/max on the custom attributes), so the
rules must match spec 04 exactly.

## // TECHNICAL CONSTRAINTS

- ADR-014: own screens on `aws-amplify/auth` (`signUp`, `confirmSignUp`, `resendSignUpCode`, `signIn`, `signOut`,
  `fetchAuthSession`/`getCurrentUser`); remove `@aws-amplify/ui-react` and its CSS import.
- Field list, attribute mapping, ranges and messages exactly as spec 04 §Inputs and §Edge Cases (Q-14 C); date entered `DD/MM/YYYY`, sent `YYYY-MM-DD`; country codes ISO 3166-1 alpha-2 with names from
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

- [x] Build green; AC-04.4, AC-04.10, AC-04.11 verified locally
- [ ] AC-04.5, AC-04.8, AC-04.9 verified against the dev User Pool (`npm run dev` or the Amplify URL), evidence in Notes
- [x] Skill file added
- [x] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

- 2026-11-12 — **Start gate not met, started on the owner's explicit request:** T02-01 is `In progress` (pool and app
  client exist, ids in [ENVIRONMENT.md](../../ENVIRONMENT.md); schema evidence pending).
- Implemented: `src/config/amplify.ts` (env names aligned to the Amplify Hosting variables `VITE_AWS_REGION`,
  `VITE_USER_POOL_ID`, `VITE_USER_POOL_CLIENT_ID`; no default region; auth configured only when all three are set;
  start-up `console.warn` removed), `src/auth/` (`validation.ts`, `countries.ts`, `errors.ts`, `signUpFlow.ts`,
  `session.ts`, `guards.tsx`), pages `SignUpPage`, `ConfirmPage`, `SignInPage`, `App.tsx` routes `/sign-up`,
  `/confirm`, `/sign-in`, guarded `/me` (content from T02-05) and header auth links / sign-out. Sign-in uses the
  Amplify default `USER_SRP_AUTH`. `autoSignIn` is **not** used: after confirmation the SPA navigates to `/sign-in`
  (spec 04 Behaviour 4). Spec 04 §Inputs/Behaviour 9/AC-04.10, design authentication, ENVIRONMENT.md and the
  `amplify.yml` comment updated to the actual env var names.
- `@aws-amplify/ui-react` and its CSS import removed (`npm uninstall`). Dev dependency **Vitest 3.2** added
  (`npm test`), described in skill [amplify-auth](../../../.claude/skills/amplify-auth/SKILL.md).
- `tsconfig.app.json`: `"strict": true` added — CLAUDE.md §4 requires strict TypeScript but the template config
  lacked it; the existing code compiled without changes.
- 2026-11-12 (owner): `frontend/.env.example` removed from Git; all `.env*` files are ignored. Variable names live
  in spec 04, values in ENVIRONMENT.md; local values go to `frontend/.env.local`. T02-01 runbook text (lines 36–37)
  still names `VITE_COGNITO_*` (devops task, left to its owner; the console already uses the right names).
- Name rule: spec 04 says "Unicode letters"; implemented literally as `\p{L}` plus space, `-`, `'`. Names that need
  combining marks (`\p{M}`, e.g. Devanagari) are rejected — widen in spec 04 first if wanted.
- Evidence (2026-11-12, local):
  - Build: `npm run build` green (CSS 1 382 bytes, was 317 410; JS 459 kB, was 811 kB). `npm run lint`: no lint
    script exists (oxlint removed by the owner) — not run.
  - **AC-04.4** — `src/auth/validation.test.ts` (`npm test`: 4 files, 44 tests passed): each of empty first name,
    gender `X`, `31/02/2000`, a date < 13 years ago, height `49`, height `170.5`, weight `301`, mismatched
    confirmation returns a field error from `submitSignUp` and the injected `signUp` mock is **not called**; the
    pages call Cognito only through `submitSignUp`.
  - **AC-04.10** — `npm run build` without any `.env*` values (bundle contains no pool id), `vite preview`,
    headless Chrome (`--dump-dom`, console logging on; channel checked with a probe page whose error was captured):
    `/`, `/sign-in`, `/me` render the home page with only Home/Chat/Admin links, zero console messages.
  - **AC-04.11** — `frontend/package.json` and `frontend/src` contain no `@aws-amplify/ui-react`.
  - Smoke check with the public pool/client ids (temporary build, no Cognito call made): header shows Sign in /
    Sign up, `/sign-up` and `/confirm` render, anonymous `/me` redirects to `/sign-in`, no console messages.
  - **Not verified** (needs the dev User Pool and a person with a mailbox): AC-04.5, AC-04.8 (sign-out part),
    AC-04.9.
