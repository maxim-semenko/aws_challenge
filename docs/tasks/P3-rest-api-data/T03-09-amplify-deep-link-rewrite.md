---
id: T03-09
title: "Amplify SPA rewrite fix: deep links 200 instead of 301 → 404 (console runbook)"
phase: P3-rest-api-data
status: Done
agent: devops
skills: [cloud-architect, devops-engineer]
depends_on: []
blocked_by: []
design: ../../design/spa-hosting.md
spec: ../../specs/01-spa-delivery.md
acceptance: [AC-01.2]
---
# T03-09 — Amplify SPA rewrite fix (deep links)

## // BUSINESS CONTEXT

Known issue from the Week 2 acceptance (T02-06, regression AC-01.2, follow-up for T01-05): `/chat`, `/admin`,
`/sign-in` answer `301 → /chat/` and then 404 with `index.html` as the body. The SPA still renders, but every deep link
logs a 404 and the new `/admin` page (Week 3) is opened by URL. A one-rule console change.

## // TECHNICAL CONSTRAINTS

- No AWS access for the agent (CLAUDE.md §3.11): console runbook in Notes, executed by the owner.
- Rule exactly as noted in `amplify.yml`: source
  `</^[^.]+$|\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json|webp)$)([^.]+$)/>`, target `/index.html`,
  type **200 (Rewrite)**; it replaces any existing 404-rewrite or redirect rule for the same purpose (owner reports the
  current rules first).
- No change to `amplify.yml` or the SPA.

## // SCOPE

**Implement**
- Runbook: Amplify console → app → Hosting → Rewrites and redirects → screenshot current rules → set the rule above →
  save; verify with `curl -I` on `/chat`, `/admin`, `/sign-in` → 200 `text/html`, and `/x.js` → 404
- Record the rule in ENVIRONMENT.md §Amplify Hosting

**Exclude**
- Custom domain, security headers

**Interfaces that must match**
- Spec 01 AC-01.2.

## Definition of Done

- [ ] Runbook executed; AC-01.2 evidence in Notes (the agent may also run the public `curl -I` itself — no AWS access
  needed)
- [ ] ENVIRONMENT.md updated; ARCH review passed
- [ ] Status updated here and in [PLAN.md](../../PLAN.md)

## Notes

- 2026-11-13: created by Week 3 planning (optional, trivial). Design spa-hosting is `Accepted`, no blocker: the start
  gate holds now.
- 2026-11-16: devops — runbook below written, status `In progress`. Baseline probe by the agent (unauthenticated
  `curl -sSI`, no AWS access) against `https://main.d67fa9mmezz1k.amplifyapp.com`:
  `/` → 200 `text/html`; `/chat`, `/admin`, `/sign-in` → `301 Location: /<path>/`; `/chat/` → 404 `text/html`
  (`X-Cache: Error from cloudfront`); `/x.js` → 404. Static files in `frontend/public` (`favicon.svg`, `icons.svg`)
  and `dist/assets/*` use only extensions from the rule's exclusion list, so they are never rewritten.
  Cost: a rewrite rule is free; no always-on resource → $0/month.

## Runbook (owner executes in the AWS console; agent has no AWS access)

Region `eu-west-1`, app `aws_challenge`, branch `main`.

**Step 1 — Record the current rules**

1. AWS console → **AWS Amplify** → app `aws_challenge` → left menu **Hosting → Rewrites and redirects**.
2. Report back: screenshot R1 of the current rule list (expected: the default `/<*>` → `/index.html`, type
   `404 (Rewrite)`; report anything else too).

**Step 2 — Replace the rules**

1. **Manage redirects** (opens the JSON editor).
2. Replace the **whole** content with exactly (the backslash is doubled because this is JSON):

   ```json
   [
     {
       "source": "</^[^.]+$|\\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json|webp)$)([^.]+$)/>",
       "status": "200",
       "target": "/index.html"
     }
   ]
   ```

   This removes the default `/<*>` 404-rewrite (it is replaced, per the task constraint). If R1 showed any other rule
   that is not about the SPA fallback, stop and report it instead of deleting it.
3. **Save**. No new build is needed; the rule applies within a minute or two.

Report back: screenshot R2 of the rule list after saving: one rule, source as above, target `/index.html`, type
`200 (Rewrite)`.

**Step 3 — Check in the browser**

Open `https://main.d67fa9mmezz1k.amplifyapp.com/chat` directly in a new tab with DevTools → Network open: the
document request is `200` (no 301, no 404) and the Chat page renders. Report back: screenshot R3 of the Network row.

**Rollback:** Manage redirects → restore the content from R1 → Save.

### Verify — AC-01.2 (the agent can run this itself, no AWS credentials)

```bash
for p in /chat /admin /sign-in /x.js; do echo "== $p"; curl -sSI "https://main.d67fa9mmezz1k.amplifyapp.com$p" | grep -iE '^(HTTP|content-type|location)'; done
```

| Path | Pass when |
|---|---|
| `/chat`, `/admin`, `/sign-in` | `200`, `content-type: text/html`, no `Location` header |
| `/x.js` | `404` (missing asset with an extension is not rewritten) |

### Evidence received

_(to be filled: owner's R1–R3, and the agent's curl output after the owner reports "saved")_
- 2026-11-16 (owner screenshots R1/R2): before — one rule `/<*>` → `/index.html` `404 (Rewrite)`; after — one rule `</^[^.]+$|\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json|webp)$)([^.]+$)/>` → `/index.html` `200 (Rewrite)`. Curl check (unauthenticated, public domain): `/`, `/chat`, `/admin`, `/sign-in`, `/sign-up` → 200 `text/html`, no Location header; `/x.js` → 404. AC-01.2 pass → `Review`.
- 2026-11-17: set to `Done` by the owner (Week 3 closed).
