---
name: amplify-auth
description: How the SPA in frontend/ uses aws-amplify v6 Auth against the Cognito User Pool — configuration from VITE_* variables, the auth API calls used by the own sign-up / sign-in / sign-out screens (no code confirmation; the owner confirms users in the console), the profile on Home, route guards, error mapping and the Vitest unit tests. Use when changing anything in frontend/src/auth, frontend/src/config/amplify.ts, frontend/src/profile or the auth pages.
license: MIT
metadata:
  domain: frontend
  triggers: Amplify, aws-amplify/auth, Cognito, signUp, signIn, UserNotConfirmedException, sign-in, sign-up, profile, route guard, cognito:groups, role, VITE_USER_POOL_ID, Vitest
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
| `signUp` | `auth/signUpFlow.ts` `submitSignUp` | called only after `validateSignUp` passes; `username` = lower-cased e-mail; `options.userAttributes` exactly the 8 attributes of spec 04; result `pendingActivation` (or `done` if Cognito confirmed at once) → `SignUpPage` shows the `MESSAGES.accountCreated*` text with a link to `/sign-in` |
| `signIn` | `pages/SignInPage.tsx`, step mapping in `auth/signInFlow.ts` `signInResult` | `DONE` → target page (default `/`); `CONFIRM_SIGN_UP` or `UserNotConfirmedException` → `MESSAGES.notActivated`, stay on `/sign-in` |
| `signOut` | `auth/session.ts` `useSignOut` | removes all cached queries except the session, then `/sign-in` |
| `getCurrentUser` | `auth/session.ts` `useSession` | TanStack Query key `['auth','session']`; any error = anonymous (`null`); disabled without auth config |
| `fetchUserAttributes` | `profile/Profile.tsx`, rendered by `pages/HomePage.tsx` for a signed-in user (T02-05) | key `['user-attributes']` |
| `fetchAuthSession` | `auth/session.ts` `useGroups`; `api/client.ts` (Bearer header, `spa-api-client`) | groups = access token claim `cognito:groups` via `profile/format.ts` `groupsFromClaims` (absent = no group = `[]`); key `['groups', userId]`, enabled with a session, `staleTime: Infinity`, dropped by sign-out. Error (no token) → "Role: unavailable". Display only — the API enforces the group. A group change shows after the next sign-in (owner decision 2026-11-17, T03-08) |
| `Hub.listen('auth')` | `auth/session.ts` `useAuthEvents` | `signedIn`, `signedOut`, `tokenRefresh_failure` invalidate the session |

**No code confirmation** (owner decision 2026-11-13): `confirmSignUp`, `resendSignUpCode` and `autoSignIn` are not
used and there is no `/confirm` route. The owner confirms new users in the Cognito console. `signUpVerificationMethod:
'code'` stays in the Amplify config only because it mirrors the pool setting.

## Routes and guard

`/sign-up` and `/sign-in` are wrapped in `AnonymousOnly` (signed-in users go to the requested page or `/`). Home `/` is
public and switches on `useSession`: profile when signed in, intro with sign-in / sign-up links otherwise. `/me` and
`/confirm` were removed; the catch-all route sends them to `/`. The header shows Chat and
Admin only when the access token `cognito:groups` claim contains `admin` (`useGroups`; spec 09, T03-08; Chat
admin-only from spec 13, T05-04); `/chat` also shows the no-access text to non-admins without a request. The
profile card shows "Role: administrator" / "Role: user" from the same claim. `RequireAuth` (anonymous →
`/sign-in` with `state.from`, back to `from` after sign-in; only same-origin paths starting with a single `/` are
accepted, `redirectTarget`) wraps `/admin` and `/chat` when the API is configured (`isApiConfigured`).

## Validation and errors

- `auth/validation.ts` — one function per field, `validateSignUp` returns either field errors or the exact SignUp
  request. Change ranges in spec 04 first, then here and in the tests.
- `auth/countries.ts` — the 249 ISO 3166-1 alpha-2 codes; names only from `Intl.DisplayNames(['en'], {type:'region'})`.
- `auth/errors.ts` — `MESSAGES` holds the user-facing texts of spec 04 and maps `error.name` (Cognito exception name)
  to them; `UserNotConfirmedException` → "Your account is not activated yet". Sign-in never shows the raw
  Cognito message (no user enumeration). Never `console.log` tokens, form values or errors that may contain them.

## Tests (Vitest, dev dependency added by T02-04)

- `npm test` (= `vitest run`, Node environment, no DOM). Test files `src/**/*.test.ts` next to the code; they are
  also type-checked by `npm run build`.
- AC-04.4 is covered by `auth/validation.test.ts`: each rejected case asserts that the injected `signUp` mock is
  never called. Inject Amplify functions as parameters instead of mocking modules where possible.
- `auth/signInFlow.test.ts` covers the sign-in step mapping (unconfirmed → not activated); `auth/errors.test.ts` the
  error messages.
- Component tests (React Testing Library + jsdom) are not set up yet; add them as dev dependencies and describe them
  here when a task needs them.
