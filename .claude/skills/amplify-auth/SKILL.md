---
name: amplify-auth
description: How the SPA in frontend/ uses aws-amplify v6 Auth against the Cognito User Pool — configuration from VITE_* variables, the auth API calls used by the own sign-up / confirm / sign-in / sign-out screens, the route guard, error mapping and the Vitest unit tests. Use when changing anything in frontend/src/auth, frontend/src/config/amplify.ts or the auth pages.
license: MIT
metadata:
  domain: frontend
  triggers: Amplify, aws-amplify/auth, Cognito, signUp, signIn, confirmSignUp, sign-in, sign-up, route guard, VITE_USER_POOL_ID, Vitest
  role: specialist
  scope: implementation
  related-skills: react-expert, spa-api-client
  source: project (created by T02-04)
  used-by: [frontend]
---

# Amplify Auth in the SPA

Design: [docs/design/authentication.md](../../../docs/design/authentication.md) (ADR-014: own screens, no
`@aws-amplify/ui-react`). Fields, attribute mapping, ranges, env var names and messages:
[spec 04](../../../docs/specs/04-user-registration-and-sign-in.md) §Inputs and §Edge Cases — the single home; the code
mirrors it. Resource ids: [docs/ENVIRONMENT.md](../../../docs/ENVIRONMENT.md).

## Configuration

- `frontend/src/config/amplify.ts` reads `VITE_AWS_REGION`, `VITE_USER_POOL_ID`, `VITE_USER_POOL_CLIENT_ID`
  (trimmed, no defaults). `isAuthConfigured` = all three non-empty.
- `configureAmplify()` runs once in `main.tsx`; it is a silent no-op without configuration. Then `App.tsx` registers
  no auth routes and renders no auth links (AC-04.10). Never add a fallback region or id.
- Amplify v6 takes the region from the pool id; `VITE_AWS_REGION` is still required so the three values are set
  together.
- `signIn` uses the Amplify default `USER_SRP_AUTH` — do not pass `authFlowType`; the app client allows
  `ALLOW_USER_SRP_AUTH` and `ALLOW_REFRESH_TOKEN_AUTH`.

## Calls used (only `aws-amplify/auth`)

| Call | Where | Notes |
|---|---|---|
| `signUp` | `auth/signUpFlow.ts` `submitSignUp` | called only after `validateSignUp` passes; `username` = lower-cased e-mail; `options.userAttributes` exactly the 8 attributes of spec 04 |
| `confirmSignUp`, `resendSignUpCode` | `pages/ConfirmPage.tsx` | code must match `^\d{6}$` before the call |
| `signIn` | `pages/SignInPage.tsx` | `nextStep.signInStep`: `DONE` → target page; `CONFIRM_SIGN_UP` or `UserNotConfirmedException` → `/confirm` with the e-mail |
| `signOut` | `auth/session.ts` `useSignOut` | removes all cached queries except the session, then `/sign-in` |
| `getCurrentUser` | `auth/session.ts` `useSession` | TanStack Query key `['auth','session']`; any error = anonymous (`null`) |
| `fetchUserAttributes` | `pages/MePage.tsx` (T02-05) | key `['user-attributes']` |
| `Hub.listen('auth')` | `auth/session.ts` `useAuthEvents` | `signedIn`, `signedOut`, `tokenRefresh_failure` invalidate the session |

`autoSignIn` is **not** used: after confirmation the user goes to `/sign-in` (spec 04 Behaviour 4).

## Routes and guard

`/sign-up`, `/confirm`, `/sign-in` are wrapped in `AnonymousOnly` (signed-in users go to the requested page or
`/me`); `/me` in `RequireAuth` (anonymous → `/sign-in` with `state.from`; after sign-in back to `from`). Only
same-origin paths starting with a single `/` are accepted as `from` (`redirectTarget`).

## Validation and errors

- `auth/validation.ts` — one function per field, `validateSignUp` returns either field errors or the exact SignUp
  request. Change ranges in spec 04 first, then here and in the tests.
- `auth/countries.ts` — the 249 ISO 3166-1 alpha-2 codes; names only from `Intl.DisplayNames(['en'], {type:'region'})`.
- `auth/errors.ts` — maps `error.name` (Cognito exception name) to the spec 04 messages. Sign-in never shows the raw
  Cognito message (no user enumeration). Never `console.log` tokens, form values or errors that may contain them.

## Tests (Vitest, dev dependency added by T02-04)

- `npm test` (= `vitest run`, Node environment, no DOM). Test files `src/**/*.test.ts` next to the code; they are
  also type-checked by `npm run build`.
- AC-04.4 is covered by `auth/validation.test.ts`: each rejected case asserts that the injected `signUp` mock is
  never called. Inject Amplify functions as parameters instead of mocking modules where possible.
- Component tests (React Testing Library + jsdom) are not set up yet; add them as dev dependencies and describe them
  here when a task needs them.
