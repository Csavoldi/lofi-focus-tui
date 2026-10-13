# Web Search & Playwright Browser Tools (pi extensions) — Design

Date: 2026-09-18

## Purpose

Give the pi coding agent three capabilities it currently lacks or needs to
standardize:

1. **Shell access** — already provided by the built-in `bash` tool. No work.
2. **Web search** — no built-in tool; add a `web_search` tool.
3. **Playwright browser automation** — no built-in tool; add read-only
   browser tools.

## Constraints / decisions (from user)

- **No API keys available** — web search must be keyless. Verified from this
  machine (2026-09-18):
  - Bing HTML endpoint (`https://www.bing.com/search?q=...`) works: HTTP 200,
    10 parseable organic results, no captcha.
  - DuckDuckGo lite/html is blocked (botnet captcha on this IP).
  - Mojeek serves a JS-only page; Marginalia redirects. Both unusable.
  - DDG Instant Answer API works but returns Wikipedia abstracts only — not
    general web search.
  - **Decision: `web_search` scrapes Bing's HTML SERP.**
- **Read-only browsing** — no click/type/form/JS-eval tools. Just open,
  extract, screenshot.
- **Global placement** — extensions live in `~/.pi/agent/extensions/`, active
  in every project. Not committed to any repo.

## Architecture

Two independent extension files plus one shared package.json:

```
~/.pi/agent/extensions/
├── package.json            # { "dependencies": { "playwright": "<pinned>" } }
├── web-search.ts           # registers web_search — zero dependencies
└── playwright-browser.ts   # registers browser_* tools — uses `playwright`
```

- pi resolves npm imports from a parent-directory `node_modules` automatically,
  so the shared `package.json` covers both files.
- Two files (not one) so a Bing markup breakage or a browser regression can be
  fixed/reloaded independently (`/reload`).

## Tool specs

### web_search

- **Parameters:** `query` (string, required), `count` (integer, optional,
  default 8, max 10).
- **Behavior:** GET `https://www.bing.com/search?q=<urlencoded>` with a
  desktop browser User-Agent. Parse:
  - Titles from `<h2><a href=...>title</a>` inside `#b_results`.
  - URLs from `<cite>` elements (display URLs) when present; otherwise decode
    Bing's `bing.com/ck/a?...u=a1<base64>` redirect links (the `u` value is
    base64 of a URL-encoded URL).
  - Snippets from the caption/paragraph text following each result.
- **Result:** numbered text list: `1. Title — URL` with snippet on the next
  line (snippets omitted when absent).
- **Errors:** non-200 responses, empty result sets, and captcha detection
  (presence of `anomaly-modal` / "bots use" markers) return a clear error
  string instead of partial garbage.

### Browser tools (read-only, headless Chromium)

One persistent browser context per extension instance, lazily started on the
first `browser_open` call, closed on `session_shutdown` and by `browser_close`.
Calling `browser_extract` or `browser_screenshot` before a page is open
returns an error telling the model to call `browser_open` first.

| Tool | Parameters | Behavior |
|------|-----------|----------|
| `browser_open` | `url` (required) | Navigate, wait for `load`. Returns final URL + page title. |
| `browser_extract` | `selector` (optional CSS), `mode` ("text" default, "html") | Returns `innerText` (text) or outerHTML (html) of body or of the first matching element. Output truncated at ~50KB with a note. |
| `browser_screenshot` | `path` (optional) | Viewport PNG. Returned as an image content block (so the model can see it) and saved to `path` or a temp file; returns the saved path. |
| `browser_close` | — | Closes the context. Subsequent browser calls re-launch lazily. |

- Browser: Chromium, headless, default viewport. No persistent profile, no
  cookies storage — stateless per session.
- Navigation/extract/screenshot errors (timeouts, bad URLs, selector not
  found) return descriptive error text.

## Setup

1. Write the two extension files.
2. Create `~/.pi/agent/extensions/package.json` pinning a `playwright` version
   that matches an already-cached browser build (`~/.cache/ms-playwright` has
   chromium-1208/1217/1228, firefox, webkit) to avoid a fresh download; if no
   cached build matches the latest release, pin the matching older version.
3. `npm install` in that directory.

## Verification

End-to-end smoke tests in print mode, one per tool:

- `pi -p -e ~/.pi/agent/extensions/web-search.ts "use web_search to search for <query>"`
  → expect a numbered list of real results.
- `pi -p -e ~/.pi/agent/extensions/playwright-browser.ts` with prompts to:
  open a known page → expect URL + title; extract text → expect page content;
  screenshot → expect an image in the tool result.

## Risks

- **Bing markup change** — parser is regex-based against a known structure;
  a breakage means a quick edit to `web-search.ts` and `/reload`.
- **Bing rate-limiting/captcha under heavy use** — surfaced as a clear error,
  not silent garbage.
- **playwright version ↔ cached browser mismatch** — pinned at setup; worst
  case is a one-time `npx playwright install chromium`.

## Out of scope

- Interactive browsing (click/type/forms/JS eval)
- Cookie/login persistence, profiles, parallel pages
- Other search engines or fallback providers
- Shell access (built-in `bash` covers it)
