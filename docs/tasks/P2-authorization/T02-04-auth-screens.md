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
- 2026-11-13 — **Owner decision after testing the deployed SPA: no e-mail confirmation in the UI.** The owner
  confirms new users in the Cognito console ("Confirm account"). Removed: `pages/ConfirmPage.tsx`, route `/confirm`,
  `confirmSignUp` / `resendSignUpCode` usage, `validateConfirmationCode`, the confirm/resend error messages. After
  `signUp` the page shows "Account created. It will be activated by an administrator; then you can sign in." with a
  link to `/sign-in`; sign-in of an unconfirmed user (`UserNotConfirmedException` or `CONFIRM_SIGN_UP`) shows "Your
  account is not activated yet" and stays on `/sign-in` (`auth/signInFlow.ts`). After sign-in the SPA goes to `/`.
  Chat and Admin nav links are shown only to a signed-in user. Spec 04 (Purpose, Inputs, Outputs, Behaviour, Edge
  Cases, AC-04.1/.5/.8/.9/.10), design authentication (Proposed Solution, Alternatives, API Design), skill
  `amplify-auth` updated. The title and scope of this task still say "confirm"; the spec is the reference.
- Evidence (2026-11-13, local): `npm test` 5 files, 48 tests passed (new `auth/signInFlow.test.ts`; `errors.test.ts`
  covers `UserNotConfirmedException` → "not activated"; `validation.test.ts` covers `pendingActivation` / `done`);
  `npm run build` green (JS 454 kB). Runtime check with `vite preview` and headless Chrome over the DevTools protocol
  (console, exceptions, log entries and every request captured; the channel proven with a probe page that logged an
  error and made a fetch):
  - all `VITE_*` empty (**AC-04.10**): `/`, `/me`, `/confirm`, `/sign-in`, `/sign-up` → `/` with the intro, header
    only "Home"; `/chat`, `/admin` → "Not available yet"; zero console messages, zero API/network requests.
  - public pool/client ids set, `VITE_API_URL` empty (temporary build, no sign-in attempted): header Home + Sign in /
    Sign up, no Chat/Admin; `/` intro with both links; `/me`, `/confirm` → `/`; `/sign-in`, `/sign-up` render; zero
    console messages, zero requests.
  - **Not verified** (need the dev User Pool): AC-04.5 (activation message, console confirm), AC-04.8 (sign-out
    part), AC-04.9 (unconfirmed sign-in message).
- 2026-11-13 — **Owner request: layout.** Plain CSS, no UI library. All colour, spacing, radius, font-size and width
  values defined once as custom properties in `:root` of `src/index.css` (the existing colours reused, no new hex
  values; interim until the design-system task, CLAUDE.md §5); `src/App.css` uses only `var(--…)` except the 560px
  breakpoint (custom properties do not work in `@media`). Header and main in a centered `.container`
  (max-width `--content-max`); sign-in / sign-up / account-created as centered cards: label above input, full-width
  inputs and primary button, field error under each field (`aria-describedby`), form-level message box, link to the
  other form in the card footer; sign-up first/last name and height/weight in a two-column grid from 560px, one
  column below. Anonymous Home intro: centered card with Sign in / Sign up buttons. Obsolete draft CSS (`.row`,
  `table`, `pre`, `.results`, `.error`) removed; the template hero/logo styles were already gone. Unused template
  assets `src/assets/hero.png`, `react.svg`, `vite.svg` left in place (deleting user files needs consent).
- Evidence (2026-11-13, local): `npm test` 5 files, 48 tests passed; `npm run build` green (CSS 3.7 kB, JS 453 kB).
  `vite preview` + headless Chrome over the DevTools protocol at 1280px and 360px (capture channel proven by a probe
  console error and fetch): all `VITE_*` empty → `/` intro card, `/chat` / `/admin` placeholder, `/sign-in` and
  `/sign-up` → `/`, header only "Home" (**AC-04.10** still holds); public pool/client ids + `VITE_API_URL=
  https://dummy-api.invalid` (temporary build) → intro card with both buttons, sign-in / sign-up cards render; in both
  builds zero console messages, zero external requests, no horizontal overflow at 360px. Screenshots checked by eye.
  **Not verified:** the signed-in profile card (needs a session in the dev pool).
