# Spec 13 — SPA: admin AI search page `/chat` (form, debounced request, results table)

Requirements: [week-05](../requirements/week-05-semantic-search.md) task, S1, W5-G1, project requirement ·
Design: [semantic-search](../design/semantic-search.md) §8 · API: [spec 12](12-chat-api.md) (single home of the
request and response fields)
Tasks: T05-04, T05-03 (deployed check), T05-05

Extends [spec 04](04-user-registration-and-sign-in.md) Behaviour 7 and 9 and [spec 09](09-admin-page-and-role.md)
§Outputs (Header): from Week 5 the Chat link is shown only to members of `admin`, and `/chat` calls `POST /chat` when
`VITE_API_URL` is set. API client rules (token, 401 sign-out, retry): skill `spa-api-client`.

## Purpose

An administrator opens `/chat`, types a question in plain language and sees the rows the Chatbot Lambda returns
(similarity search, or statistics through generated SQL when the question contains the keyword "sql"), without
spending LLM tokens on half-typed text.

## Inputs

| Input | Rule |
|---|---|
| Query field | single-line text input, label "Question", `maxLength` 500; the value sent is the trimmed text |
| Keyword rule (same as spec 12 §Inputs) | `sql` mode when the trimmed text matches `\bsql\b` case-insensitively; otherwise `vector` mode |
| Automatic request (debounce) | only in `vector` mode: **800 ms** after the last change, when the trimmed text has **≥ 3** characters and differs from the last sent text |
| Explicit request | **Search** button or Enter: any trimmed text of 1…500 characters, both modes; this is the **only** way to send a `sql`-mode question |
| Request | `POST /chat` with body `{"query": "<trimmed text>"}` — exactly this one field (spec 12 §Inputs) |
| Access | `cognito:groups` of the access token (spec 09) for the link and the page guard; the API enforces the group |

Hint text under the field (fixed): "Find similar users: type a profile, e.g. *which users are similar to gender: female;
birth year: 1990; country: Poland*. Statistics: start with **sql**, e.g. *sql how many users aged 25 to 35 live in
Poland and weigh more than 70 kg* — press Search."

## Outputs

**Header:** Chat link only when the signed-in user's token groups contain `admin` (like Admin); display only.

**`/chat` page** — heading "AI search", the form, then one of:

| State | Content |
|---|---|
| `VITE_API_URL` empty | the existing placeholder "Not available yet — coming in a later week." and no request |
| not signed in | redirect to `/sign-in`, back to `/chat` after sign-in |
| signed in, not in `admin` | "You do not have access to this page." — no form, no request |
| nothing sent yet | form and hint only |
| loading | "Searching…"; the previous result stays visible but marked busy (`aria-busy`) |
| 200, `rowCount` 0 | "No matching rows." + meta line |
| 200 with rows | meta line + table (+ SQL block in `sql` mode) |
| 400 | "The question could not be answered. Rephrase it." |
| 401 | sign-out and `/sign-in` (spa-api-client rule) |
| 403 | "You do not have access to this page." |
| 429 | "The AI service is busy. Try again shortly." |
| 502 | "AI service not available — it is switched on only during working sessions." |
| 500 / network / other | "The search failed." |

**Meta line:** `<mode> · <rowCount> rows · <timings.totalMs> ms`, plus "(first 100 rows)" when `truncated`.

**SQL block (`sql` mode):** the returned `sql` in a `<pre>` block labelled "Executed SQL".

**Table:** header cells = `columns` in order; one row per `rows` item; cells as text: `null` → "—", numbers as
returned (`distance` with 4 decimals), booleans `true`/`false`, strings as returned. No edit control. Rendered with
React text nodes only (never HTML from the response).

## Behaviour

1. The page renders the form for an admin; typing updates the field only.
2. In `vector` mode the debounce timer (800 ms) restarts on every change; when it fires and the rule of §Inputs holds,
   one request is sent. In `sql` mode no timer runs.
3. Search / Enter sends the current trimmed text at once (cancelling a pending timer) if it has 1…500 characters;
   an empty field sends nothing.
4. Requests go through TanStack Query keyed by `['chat', <trimmed text>]` with **no retry** of `POST /chat` (each
   call may cost tokens) and no refetch on focus/reconnect; only the response of the latest sent text is shown. The
   same text sent again within 60 s is answered from the cache (no second call).
5. Errors are shown by status as in §Outputs; the 401 rule of spa-api-client applies.

## Edge Cases / Failure Modes

| Case | Expected result |
|---|---|
| Typing "sql how many …" letter by letter | no request until Search / Enter (`s`, `sq` are under 3 characters; from `sql` on the keyword rule blocks the timer) |
| Typing "mysql users" | `vector` mode (whole-word rule), automatic request after 800 ms |
| "ab" then pause | no request (< 3 characters) |
| Field cleared after a result | the last result stays until the next request |
| 501 characters pasted | the input keeps 500 (`maxLength`) |
| Response with an unexpected column set (SQL mode) | rendered generically from `columns` / `rows` |
| Endpoint absent (between sessions) | 502 text, no retry |
| Non-admin opens `/chat` by URL | no-access text, no request |

## Acceptance Criteria

- [ ] AC-13.1 `cd frontend && npm run build` and `npm test` pass; unit tests cover the keyword/mode rule, the
  automatic-request rule (length ≥ 3, not `sql` mode, not equal to the last sent text), the status → message mapping
  and the cell formatting of §Outputs
- [ ] AC-13.2 Code review: `POST /chat` body is exactly `{"query": <trimmed>}`; no retry and no refetch on focus for
  the chat query; no `dangerouslySetInnerHTML`; the Chat link and the page are admin-only; with empty `VITE_API_URL`
  no request is made
- [ ] AC-13.3 Deployed SPA, admin (DevTools Network): typing a vector-mode query fires one `POST /chat` about 800 ms
  after the last keystroke; typing a `sql …` question fires **no** request until Search; the results table, meta line
  and (SQL mode) the executed SQL are shown (owner screenshot)
- [ ] AC-13.4 Deployed SPA, non-admin: no Chat link; `/chat` by URL shows "You do not have access to this page." and
  DevTools shows no `POST /chat` (owner screenshot)
- [ ] AC-13.5 Deployed SPA with the endpoint absent: a search shows the 502 text "AI service not available …" (owner
  screenshot)
