---
id: T02-06
title: "Week 2 acceptance check"
phase: P2-authorization
status: Done
agent: tester
skills: [test-master]
depends_on: [T02-01, T02-03, T02-04, T02-05]
blocked_by: []
design: null  # acceptance task, verifies specs 04 and 05
spec: [../../specs/04-user-registration-and-sign-in.md, ../../specs/05-protected-api.md]
acceptance: [AC-04.1, AC-04.2, AC-04.4, AC-04.5, AC-04.6, AC-04.8, AC-04.9, AC-04.10, AC-04.11, AC-05.1, AC-05.2, AC-05.3, AC-05.4, AC-05.5, AC-05.6]
---
# T02-06 — Week 2 acceptance check

## // BUSINESS CONTEXT

Week 2 (owner decision 2026-11-13: the curriculum topic only — Cognito User Pool with Amplify Auth, HTTP API with a
JWT authorizer) is done only when registration, sign-in, the personal page and the authorizer are proven on `dev` by
someone other than the implementer. The report is what the owner shows to the mentor.

## // TECHNICAL CONSTRAINTS

- No AWS access for the agent (CLAUDE.md §3.11). AWS-side ACs are verified from evidence the owner provides (console
  screenshots, the browser-console status codes from the T02-03 evidence checklist); local ACs (AC-04.4, AC-04.10,
  AC-04.11: SPA build/tests, `package.json`) are run by the tester itself. Test users are signed up by the owner
  through the deployed SPA (the feature under test).
- Evidence already recorded in T02-01, T02-03, T02-04 and T02-05 Notes is reused (pointer, not a copy); only what is
  missing is requested from the owner.
- Each criterion gets pass/fail plus evidence (source, command or screenshot reference, trimmed output); account ids
  masked; no tokens, passwords or test-user personal data beyond the test e-mail's domain in the report.
- A failed criterion is reported back to the owning task, not fixed here.

## // SCOPE

**Implement**
- Checklist for the owner: only the evidence still missing (see the owning tasks' Notes)
- Verify every AC listed in the front matter (spec 04 without the withdrawn AC-04.3/AC-04.7; spec 05 as reduced
  2026-11-13); write the report in Notes (table: AC → result → evidence)
- Regression: the spec 01 home page with the current build

**Exclude**
- Week 3 items (group `admin`, `/api/...` endpoints, role line, Lambda code, logs), fixing defects, automated E2E
  suite (later phase)

**Interfaces that must match**
- AC numbering exactly as in the specs.

## Definition of Done

- [ ] All listed ACs pass, or failures are recorded against their tasks and the owner decides
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

### Acceptance run 2026-11-13 (tester)

Start gate not fully met (T02-01 `In progress`, T02-03/04/05 `Review`); run on the owner's request. No AWS access used
(CLAUDE.md §3.11). Sources: **[L]** own local command; **[P]** own public, unauthenticated HTTP probe (no AWS
credentials) of the SPA `https://main.d67fa9mmezz1k.amplifyapp.com` and the API endpoint in
[ENVIRONMENT.md](../../ENVIRONMENT.md#http-api-week-2); **[O]** owner evidence recorded in the named task Notes.

Local runs (`frontend/`, current `main` 0a9cb78, no `.env*` values loaded): `npm ci` ok; `npm test` → 5 files, 48
tests passed; `npm run build` green (`tsc -b`; CSS 3.68 kB, JS 451.54 kB). Runtime: `vite preview` + headless Chrome
over the DevTools protocol, capturing console, exceptions, log entries and every request; the capture channel was
proven with a probe page that logged an error and fetched `https://example.invalid` (both captured).

| AC | Result | Evidence |
|---|---|---|
| AC-04.1 | pass | [O] T02-01 Notes 2026-11-12/13 (sign-in attribute, self-registration, deletion protection, required and custom attributes) + owner screenshot 2026-11-13: *Extensions → Lambda triggers (0)*, "No Lambda triggers" |
| AC-04.2 | pass | [O] T02-01 Notes: no secret; `ALLOW_USER_SRP_AUTH`, `ALLOW_REFRESH_TOKEN_AUTH`, accepted `ALLOW_USER_AUTH` (password only); prevent user existence errors on; access/ID 60 min, refresh 5 days; read/write permission evidenced by use (sign-up with all eight values, profile shows them, T02-05 Notes) |
| AC-04.4 | pass | [L] `src/auth/validation.test.ts` "AC-04.4 rejected without a Cognito call": empty first name (whitespace), gender `X`, `31/02/2000`, date < 13 years, height `49`, height `170.5`, weight `301`, mismatched confirmation → each `invalid` with a field error and the injected `signUp` mock not called; `SignUpPage` calls Cognito only through `submitSignUp` (`auth/signUpFlow.ts`) |
| AC-04.5 | pass | [O] owner screenshots 2026-11-13: after a new sign-up (`test1@gmail.com`) the SPA shows "Account created. It will be activated by an administrator; then you can sign in." with "Go to sign in"; Cognito *Users* lists the user as `Unconfirmed`; after *Confirm account* the user page shows `Confirmed` ("has been confirmed successfully"). The eight attribute values were not shown on the user page — sign-up with all fields is evidenced by the profile (AC-04.6) |
| AC-04.6 | pass | [O] owner screenshot 2026-11-13 (`test1@gmail.com`): Home `/` shows the "My profile" card read-only — first/last name, email, gender `M`, date `27/05/2001` (DD/MM/YYYY), country `Bahamas (BS)`, `175 cm`, `60 kg`; no edit/save control. The "Role: unavailable" badge in that screenshot came from a tab loaded before commit `0a9cb78`; the live bundle has no role line (checked: `/` bundle contains no "Role:") |
| AC-04.8 | pass | [O] owner screenshot 2026-11-13: after Sign out the SPA shows the Sign in card, header "Home" + "Sign in"/"Sign up" only; [P] anonymous `/` shows the intro without profile |
| AC-04.9 | pass | [O] owner screenshot 2026-11-13: sign-in with the unconfirmed `test3@gmail.com` shows "Your account is not activated yet" on the Sign in card; [L] `signInFlow.test.ts` |
| AC-04.10 | pass | [L] empty-env build (no pool id in the bundle) + `vite preview` + headless Chrome: `/`, `/me`, `/sign-in`, `/sign-up`, `/confirm` → `/`, header only "Home", intro; `/chat`, `/admin` → "Not available yet — coming in a later week."; 0 console messages, 0 external requests on all seven paths |
| AC-04.11 | pass | [L] `grep ui-react` in `frontend/package.json`, `package-lock.json`, `src` → 0 matches; [P] deployed bundle → 0 matches |
| AC-05.1 | pass | [O] T02-03 Notes: console screenshots — `aws-challenge-api`, HTTP, `$default`, `cognito-jwt-authorizer` JWT, identity source `$request.header.Authorization`, issuer and audience per ENVIRONMENT.md |
| AC-05.2 | pass | [O] T02-03 Notes: routes changed to `GET /admin`, `POST /chat`, both JWT. [P] corroborated: `DELETE /admin` → 404 (no `ANY` route), `GET /unknown` and `GET /` → 404 `{"message":"Not Found"}` (a `$default` route would have answered 401) |
| AC-05.3 | pass | [P] `GET /admin` and `POST /chat` without `Authorization` → 401 `{"message":"Unauthorized"}`; [O] T02-03 Notes same |
| AC-05.4 | waived (owner, 2026-11-13) | [P] `Bearer abc` → 401; a forged JWT with the pool issuer and client id but an invalid signature → 401 (T02-03 Notes). Tampered-real-token and expired-token cases waived: signature and `exp` checks are done by the AWS-managed JWT authorizer |
| AC-05.5 | pass | [O] T02-03 Notes 2026-11-13: owner's browser console on the deployed SPA, signed in: `GET /admin` with access token → 200, `POST /chat` → 200 |
| AC-05.6 | pass | [P] `OPTIONS /admin` (Origin = Amplify origin, method GET, headers `authorization`) → 204, `access-control-allow-origin: https://main.d67fa9mmezz1k.amplifyapp.com`, allow-headers `authorization,content-type`; same for `OPTIONS /chat` (POST). Edge case: Origin `https://example.com` → 204 without `Access-Control-Allow-Origin` |

**Regression — spec 01 home page (current build):**

| AC | Result | Evidence |
|---|---|---|
| AC-01.1 | pass | [P] `curl -I /` → 200, `Via: … cloudfront.net`, `X-Cache: Hit from cloudfront`, `X-Amz-Cf-Id` present; deployed bundle matches the local build size (451.6 kB) |
| AC-01.2 | **fail**, accepted by the owner (2026-11-13) as a known issue → follow-up for T01-05 (Amplify rewrite rule type `200 (Rewrite)`) | [P] `curl -I /chat` → `301 Location: /chat/`, then `/chat/` → **404** `text/html` (body = `index.html`, `X-Cache: Error from cloudfront`); same for `/admin`, `/sign-in`, `/sign-up`, `/me`. Expected 200 `text/html` (spec 01 Edge Cases: deep link → 200 rewrite). The SPA still renders in a browser (404 body is `index.html`), but each deep link logs a 404 console error. Likely cause: the Amplify rewrite is a 404-rewrite (or missing the `</^[^.]+$|…/>` → `/index.html` **200 (Rewrite)** rule noted in `amplify.yml`); fix is an owner console change from a T01-05 runbook, not done here. `/x.js` → 404 as expected |

**Summary:** 15 Week 2 ACs — **9 pass** (AC-04.2, 04.4, 04.10, 04.11, 05.1, 05.2, 05.3, 05.5, 05.6), **0 fail**,
**6 not verified** for missing owner evidence (AC-04.1, 04.5, 04.6, 04.8, 04.9, 05.4). Regression: AC-01.1 pass,
**AC-01.2 fail**, reported against T01-05. Status stays `In progress`.

**Missing evidence — checklist for the owner** (screenshots; no tokens, passwords or personal values beyond what the
AC needs):
1. AC-04.1 — Cognito → `aws-challenge-users` → *Extensions* → *Lambda triggers*: the empty trigger list.
2. AC-04.5 — sign up a new test user in the deployed SPA: (a) the "Account created …" message with the sign-in link;
   (b) Cognito → Users → that user: `UNCONFIRMED` and its attributes (`birthdate` as `YYYY-MM-DD`, the three custom
   values); (c) after "Confirm account": `CONFIRMED`.
3. AC-04.9 — before step 2(c), sign in with that user: `/sign-in` showing "Your account is not activated yet".
4. AC-04.6 — after step 2(c), sign in: the profile card on Home (date `DD/MM/YYYY`, country "Name (CODE)", no input,
   edit or save control); other values may be blurred.
5. AC-04.8 — click "Sign out": the SPA on `/sign-in`; then Home `/` showing the intro without profile data.
6. AC-05.4 — T02-03 evidence checklist Step 1 (`tampered` → 401) and Step 2 (`expired` → 401 after the printed
   `expires` time, tab not reloaded); screenshot of the console lines.
7. Regression AC-01.2 — decision on the T01-05 rewrite fix (or an explicit waiver).

- 2026-11-13 (owner): "the main cases are checked, everything works" — remaining evidence collected (AC-04.6, AC-04.8, AC-04.9), AC-05.4 partial cases waived, AC-01.2 regression accepted as a known issue. All Week 2 ACs pass or are waived → `Review`.
- 2026-11-13: set to `Done` by the owner (Week 2 closed).
