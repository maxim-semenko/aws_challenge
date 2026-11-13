---
id: T02-03
title: "HTTP API with Cognito JWT authorizer (built by the owner)"
phase: P2-authorization
status: Review
agent: devops
skills: [cloud-architect, http-api-jwt]
depends_on: [T01-04, T02-01]
blocked_by: []
design: ../../design/api-gateway-auth.md
spec: ../../specs/05-protected-api.md
acceptance: [AC-05.1, AC-05.2, AC-05.3, AC-05.4, AC-05.5, AC-05.6]
---
# T02-03 — HTTP API with Cognito JWT authorizer (built by the owner)

## // BUSINESS CONTEXT

W2-G3, the second half of the Week 2 curriculum topic: the HTTP API is the only public door to the functions in the
VPC, and API Gateway must turn away every request without a valid Cognito token before a function runs. The owner
built the API himself in the console on 2026-11-13; this task records it and collects the proof. Endpoints with real
behaviour, the `admin` group check and the Lambda code are Week 3.

## // TECHNICAL CONSTRAINTS

- No AWS access for the agent (CLAUDE.md §3.11): every AWS fact comes from the owner's screenshots and probes;
  identifiers are recorded only in [ENVIRONMENT.md](../../ENVIRONMENT.md#http-api-week-2) (no copies here).
- Settings as in [design/api-gateway-auth](../../design/api-gateway-auth.md) §Proposed Solution (Week 2, as built).
- No change to the API is needed for Week 2; any change is a console runbook in this task first.
- Token values are never written to Notes, screenshots or logs; evidence shows status codes only.

## // SCOPE

**Implement**
- Record the as-built API (done in ENVIRONMENT.md) and the owner's evidence for AC-05.1 … AC-05.6 in Notes
- Evidence checklist for the owner (below)
- Skill file `http-api-jwt` (authorizer settings, access vs ID token audience, CORS, how to add a route, how to prove
  the authorizer; skills ownership rule)

**Exclude**
- Lambda code and its upload, `/api/...` endpoints, group `admin` and first administrator, access logs, throttling,
  invoke-permission review, CORS for localhost (all Week 3, design §Open Questions), custom domain, WAF, IaC (T00-03)

**Interfaces that must match**
- API endpoint, authorizer, routes and CORS origin as recorded in ENVIRONMENT.md (read by Week 3 planning).

## Definition of Done

- [x] API built by the owner; identifiers recorded in ENVIRONMENT.md
- [ ] AC-05.1 … AC-05.6 verified from the owner's evidence, recorded in Notes
- [x] Monthly cost noted: per request only, ≈ $0 at learning volume (design §Cost)
- [ ] Skill file `http-api-jwt` added; ARCH review passed
- [x] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

- 2026-11-13 — **Built by the owner in the console, before the start gate held** (T02-01 still `In progress`). Task
  rewritten the same day after the owner's decision "Week 2 = the curriculum topic only"; the former scope (admin
  handler deploy, `/api/me`, `/api/admin/ping`, first admin, access log) moved to Week 3. Set to `Review` on the
  owner's request with the evidence items below still open.
- Evidence so far (owner, 2026-11-13; values in [ENVIRONMENT.md](../../ENVIRONMENT.md#http-api-week-2)):
  - **AC-05.1** — console screenshots: API `aws-challenge-api`, HTTP, stage `$default`, authorizer
    `cognito-jwt-authorizer` (JWT, identity source `$request.header.Authorization`, issuer = pool, audience = app
    client) — **pass**.
  - **AC-05.2** — console screenshots: routes `ANY /admin`, `ANY /chat` (since 2026-11-13: `GET /admin`, `POST /chat`), both JWT, no scopes; no other route recorded
    — **pass** (assumes the screenshot showed the complete route list).
  - **AC-05.3** — `/admin` without a token → 401 (owner's probe) — **pass for `/admin`; `/chat` not verified**.
  - **AC-05.4** — **not verified**.
  - **AC-05.5** — **not verified** (the open item: an authenticated call must not return 401).
  - **AC-05.6** — preflight from the Amplify origin → 204 (owner's probe) — **status pass;
    `Access-Control-Allow-Origin` value not recorded**.
  - Open fact: ENVIRONMENT.md records an integration only for `/chat`; which integration `/admin` has is not
    recorded (affects what AC-05.5 returns on `/admin`, not whether it passes).
- **Evidence checklist for the owner** (one browser session, no AWS change). Open the deployed SPA (Amplify domain),
  sign in, open DevTools → Console, paste step 1. It prints only labels and status codes, never the token.

  ```js
  // Step 1
  const api = 'https://o6cpz238i3.execute-api.eu-west-1.amazonaws.com'
  const k = Object.keys(localStorage).find(x => x.startsWith('CognitoIdentityServiceProvider.') && x.endsWith('.accessToken'))
  window.t = localStorage.getItem(k)
  const p = JSON.parse(atob(t.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
  console.log('token_use', p.token_use, 'expires', new Date(p.exp * 1000).toISOString())
  const i = t.lastIndexOf('.') + 20
  const bad = t.slice(0, i) + (t[i] === 'A' ? 'B' : 'A') + t.slice(i + 1)
  const call = async (label, path, auth) => {
    try { const r = await fetch(api + path, auth ? { headers: { Authorization: auth } } : {}); console.log(label, path, r.status) }
    catch { console.log(label, path, 'blocked by the browser - read the status in the Network tab') }
  }
  await call('no token', '/admin'); await call('no token', '/chat')
  await call('malformed', '/admin', 'Bearer abc')
  await call('tampered', '/admin', 'Bearer ' + bad)
  await call('valid', '/admin', 'Bearer ' + t); await call('valid', '/chat', 'Bearer ' + t)
  ```

  Expected: `token_use access`; `no token` → 401 on both; `malformed` and `tampered` → 401; `valid` → anything but
  401 on both (AC-05.3, AC-05.4 without the expiry case, AC-05.5). Step 2 (expiry case of AC-05.4): keep the same tab
  open **without reloading** until after the printed `expires` time, then run
  `await call('expired', '/admin', 'Bearer ' + window.t)` → expected 401. For AC-05.6: in the Network tab, the
  `OPTIONS` request that precedes a `valid` call — screenshot of its status and the `access-control-allow-origin`
  response header. Send screenshots of the console output and of that `OPTIONS` request.
- 2026-11-13 (owner's browser console + unauthenticated curl probes): the authenticated call from the SPA origin is
  blocked by CORS because the routes are `ANY /admin` and `ANY /chat` — an `ANY` route also matches the browser's
  `OPTIONS` preflight, the JWT authorizer rejects it (preflights carry no token) with 401, so the automatic CORS
  preflight response (204, seen on paths without a route) never applies. Fix (owner, console): replace `ANY` with
  explicit methods — `GET /admin`, `POST /chat` (Week 5 sends the query in the body) — and deploy `$default`.
- 2026-11-13 (owner): routes changed to `GET /admin` and `POST /chat` (auto-deploy on `$default`). Evidence:
  - curl, unauthenticated: `OPTIONS /admin` and `OPTIONS /chat` from the Amplify origin → 204 (was 401);
    `GET /admin`, `POST /chat` without token → 401; `Authorization: Bearer abc` → 401; a forged JWT (pool issuer and
    client id, invalid signature) → 401.
  - Owner's browser console on the deployed SPA, signed in: `GET /admin` with the access token → 200, without → 401;
    `POST /chat` with the access token → 200, without → 401.
  - Not checked: an expired token (needs a session older than 60 min) — the authorizer's `exp` check is AWS-managed.
- 2026-11-13 (devops): skill file **done** — [`.claude/skills/http-api-jwt/SKILL.md`](../../../.claude/skills/http-api-jwt/SKILL.md)
  (authorizer by pointer to ENVIRONMENT.md, access token and `aud`/`client_id`, explicit methods instead of `ANY`,
  CORS, adding a route by runbook, verify steps, Week 3 items); added to this task's and the devops agent's `skills`.
  ARCH review pending.
