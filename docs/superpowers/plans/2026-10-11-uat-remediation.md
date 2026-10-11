# UAT Findings Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the five UAT findings from 2026-10-11 (1×P2 unreachable-service hang, 2×P3 TUI issues, 2×P4 cosmetic issues) documented in `UAT-FINDINGS.md`.

**Architecture:** All fixes are local to two existing layers: the ACE-Step HTTP adapter (timeout strategy + error wrapping) and the TextUI presentation layer (CSS and status rendering), plus one metadata typing fix in `SessionManager._stitch_chunk_results`. No config schema or public API changes.

**Tech Stack:** Python 3.13, httpx, pydantic, Textual/rich, pytest.

**Spec:** `UAT-FINDINGS.md` (issues 1–5), verified against `UAT-REPORT-2026-10-11.md`.

## Global Constraints

- Branch: all work lands on `dev`, never `main`.
- Lint must stay clean: `.venv/bin/ruff check src tests` → 0 errors (line length ≤ 100).
- Full suite must pass: `.venv/bin/python -m pytest -q` → all pass (baseline 334 passed, 1 skipped).
- Existing adapter behavior contracts stay intact: `/format_input` failures fall back to the local prompt (swallow exceptions); `health()` keeps returning `bool` (`False` on any HTTP error) — it must not start raising `RuntimeError`.
- TUI tests use `LofiFocusApp(session_manager=FakeSessionManager(), config=AppConfig())` with `app.run_test()` pilots (pattern in `tests/test_tui_app.py`).
- Each task is one commit on `dev`; commit messages use conventional prefixes (`fix:`/`feat:`/`docs:`).

## Review Focus

- Firewall-DROPped host (host up, port silently dropped): connect must fail in ~`connect_timeout_seconds` (10s default), never the full 1800s `timeout_seconds`. Pinned by `test_http_adapter_client_uses_short_connect_timeout` (Task 1).
- Connection-level failure mid-generation (`ConnectError`/`ConnectTimeout` on `/release_task`, `/query_result`, or `/v1/audio`): user-visible `status.error` must say "cannot reach ACE-Step service at <base_url>", not a bare httpx repr. Pinned by `test_http_adapter_wraps_unreachable_service_errors` (Task 1) and the render test (Task 2).
- Error text that is empty/absent or a stale error on a non-error status: `render_status` must render the `error:` line only when `state == "error"` and the reason is non-empty. Pinned in Task 2.
- Single-chunk sessions: `_stitch_chunk_results` also runs for `chunk_count == 1`, so numeric metadata applies there too. Pinned in Task 5.
- Narrow terminals (< 64 cols): modal `width: 64` must not lose text at typical sizes; verified at 110×50 (UAT size) in Task 3 — no change if smaller widths clip gracefully (Textual wraps/shrinks Static content).

---

### Task 1: [P2] Fast-fail connect timeout and unreachable-service error in `AceStepHttpAdapter`

**Files:**
- Modify: `src/lofi_focus_tui/generation/http_ace_step.py` (constructor ~97-119, `submit_task` ~149-212, `query_result` ~214-221, `download_audio` ~223-230)
- Test: `tests/test_http_ace_step.py`

**Interfaces:**
- Consumes: existing `httpx.Client`, `httpx.MockTransport` test pattern.
- Produces: `AceStepHttpAdapter(..., connect_timeout_seconds: float = 10.0)`; private helpers `_request_timeout(read_seconds: float | None = None) -> httpx.Timeout`, `_post(path: str, json: dict, timeout: httpx.Timeout | None = None) -> httpx.Response`, `_get(path: str, params: dict) -> httpx.Response`. `_post`/`_get` attach `self._headers()` and translate `(httpx.ConnectError, httpx.ConnectTimeout)` into `RuntimeError(f"cannot reach ACE-Step service at {self.base_url}: {exc}")` (chained `from exc`).

- [x] **Step 1: Write the failing tests**

In `tests/test_http_ace_step.py` add:

```python
def test_http_adapter_client_uses_short_connect_timeout():
    adapter = AceStepHttpAdapter(base_url="http://ace.test", timeout_seconds=1800.0)

    assert adapter.client.timeout.connect == 10.0
    assert adapter.client.timeout.read == 1800.0
    assert adapter.client.timeout.write == 1800.0
    assert adapter.client.timeout.pool == 1800.0


def test_http_adapter_wraps_unreachable_service_errors():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out")

    adapter = AceStepHttpAdapter(
        base_url="http://ace.test",
        transport=httpx.MockTransport(handler),
        poll_interval_seconds=0.0,
    )

    with pytest.raises(RuntimeError, match="cannot reach ACE-Step service at http://ace.test"):
        adapter.generate(make_blueprint(), duration_seconds=1)
```

(`ConnectTimeout` on `/format_input` is swallowed by the existing fallback; the wrap fires at `/release_task`.)

Update the existing `/format_input` timeout assertion in `test_http_adapter_generates_audio_from_remote_task` to:

```python
assert request.extensions["timeout"] == {
    "connect": 10.0,
    "read": 30.0,
    "write": 30.0,
    "pool": 30.0,
}
```

- [x] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_http_ace_step.py -v -k "short_connect_timeout or wraps_unreachable"`
Expected: FAIL (connect is 1800.0; ConnectTimeout propagates as httpx error, not RuntimeError) — plus the updated assertion fails.

- [x] **Step 3: Implement in `http_ace_step.py`**

- Constructor: add `connect_timeout_seconds: float = 10.0` parameter; store as attribute; build the default client with `timeout=self._request_timeout()` instead of `timeout=timeout_seconds`.
- `_request_timeout`: `read = self.timeout_seconds if read_seconds is None else min(read_seconds, self.timeout_seconds)`; return `httpx.Timeout(connect=self.connect_timeout_seconds, read=read, write=read, pool=read)`.
- `_post`/`_get`: single try/except around `self.client.post(...)` / `self.client.get(...)` as specified in Interfaces; `health()` keeps its raw `self.client.get` inside its own `except httpx.HTTPError → False`.
- Replace call sites: `submit_task` `/release_task` POST (and `/format_input` POST keeps raw client call but uses `timeout=self._request_timeout(30.0)` in place of `timeout=min(30.0, self.timeout_seconds)`), `query_result`, `download_audio`.
- `RunPodAceStepAdapter` needs no change (inherits).

- [x] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_http_ace_step.py -v`
Expected: all PASS.

- [x] **Step 5: Commit**

```bash
git add src/lofi_focus_tui/generation/http_ace_step.py tests/test_http_ace_step.py
git commit -m "fix: fail fast when the ACE-Step service is unreachable"
```

---

### Task 2: [P3] Render the error reason in the TUI status panel

**Files:**
- Modify: `src/lofi_focus_tui/tui/widgets.py:71-93` (`render_status`)
- Test: `tests/test_tui_app.py`

**Interfaces:**
- Consumes: `BackendStatus.error` (`src/lofi_focus_tui/domain.py:184`), `_field_line` helper, `theme.desc`.
- Produces: `render_status` output gains a trailing `error: <reason>` line (style `theme.desc`) exactly when `_enum_value(status.state) == "error"` and `status.error` is truthy.

- [x] **Step 1: Write the failing test**

```python
def test_render_status_shows_error_reason_only_in_error_state():
    failing = BackendStatus(
        state=BackendState.ERROR, message="generation failed", error="connection refused"
    )
    idle = BackendStatus(state=BackendState.IDLE, message="ready", error="stale")

    rendered = str(render_status(failing))

    assert "error: connection refused" in rendered
    assert "stale" not in str(render_status(idle))
```

(Import `render_status` and `BackendState` in the test module if not already imported.)

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_tui_app.py::test_render_status_shows_error_reason_only_in_error_state -v`
Expected: FAIL — "error: connection refused" not in rendered output.

- [x] **Step 3: Implement in `render_status`**

After the `message` line is appended (before the `chunk_count` block), append:

```python
if state == "error" and status.error:
    lines.append(_field_line("error", status.error, theme.desc))
```

- [x] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_tui_app.py -v`
Expected: all PASS.

- [x] **Step 5: Commit**

```bash
git add src/lofi_focus_tui/tui/widgets.py tests/test_tui_app.py
git commit -m "feat: show the backend error reason in the status panel"
```

---

### Task 3: [P3] Center the option-guide and export modals

**Files:**
- Modify: `src/lofi_focus_tui/tui/app.py:84-93` (app `CSS`)
- Test: `tests/test_tui_app.py`

**Interfaces:**
- Consumes: existing `Screen { align: center middle; }` rule (centering is a no-op at width 100%; giving the modal children `width: 64` activates it).
- Produces: CSS rule `#option-guide, #export-prompt, #export-directory, #export-error { width: 64; }`.

- [x] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_tui_modal_screens_center_their_content_at_110_columns():
    app = LofiFocusApp(session_manager=FakeSessionManager(), config=AppConfig())

    async with app.run_test(size=(110, 50)) as pilot:
        await pilot.press("h")
        guide = pilot.app.screen.query_one("#option-guide")
        assert guide.region.width == 64
        assert guide.region.x == (110 - 64) // 2

        await pilot.press("escape")
        await pilot.press("e")
        export_input = pilot.app.screen.query_one("#export-directory", Input)
        assert export_input.region.width == 64
        assert export_input.region.x == (110 - 64) // 2
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_tui_app.py::test_tui_modal_screens_center_their_content_at_110_columns -v`
Expected: FAIL — width is 110 (full bleed) / x is 0.

- [x] **Step 3: Add the CSS rule in `LofiFocusApp.CSS`**

```css
#option-guide, #export-prompt, #export-directory, #export-error {
    width: 64;
}
```

- [x] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_tui_app.py -v`
Expected: all PASS.

- [x] **Step 5: Commit**

```bash
git add src/lofi_focus_tui/tui/app.py tests/test_tui_app.py
git commit -m "fix: center option-guide and export modal content"
```

---

### Task 4: [P4] Make the prompt input border visible

**Files:**
- Modify: `src/lofi_focus_tui/tui/app.py` (app `CSS`)
- Test: `tests/test_tui_app.py`

**Interfaces:**
- Consumes: Textual app CSS (higher precedence than the widget default border).
- Produces: `#prompt { border: round #666666; }` — a neutral mid-gray that reads against a dark terminal across all 10 themes (theme `label` colors are unreliable here: `city_pop.label` is the rich style name `"dim"`, not a color).

- [x] **Step 1: Write the failing test**

```python
def test_prompt_input_border_is_styled_and_visible():
    app = LofiFocusApp(session_manager=FakeSessionManager(), config=AppConfig())

    async with app.run_test() as pilot:
        border = pilot.app.query_one("#prompt", Input).styles.border

    assert border[0] == "round"
    assert border[1].hex == "#666666"
```

(Decorate with `@pytest.mark.asyncio` to match neighboring async tests.)

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_tui_app.py::test_prompt_input_border_is_styled_and_visible -v`
Expected: FAIL — default Input border is not round/#666666.

- [x] **Step 3: Add the CSS rule**

In `LofiFocusApp.CSS`, append:

```css
#prompt {
    border: round #666666;
}
```

- [x] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_tui_app.py -v`
Expected: all PASS.

- [x] **Step 5: Commit**

```bash
git add src/lofi_focus_tui/tui/app.py tests/test_tui_app.py
git commit -m "fix: give the prompt input a visible border"
```

---

### Task 5: [P4] Emit numeric durations in the metadata `generation` block

**Files:**
- Modify: `src/lofi_focus_tui/backend/session_manager.py:543-554` (`_stitch_chunk_results` metadata update)
- Test: `tests/test_session_manager.py`

**Interfaces:**
- Consumes: `ChunkRecordingModel` + `RecordingPlayback` fixtures (tests), `RecordingPlayback.loaded` (stitched `GenerationResult`).
- Produces: `result.metadata["chunk_count"]` as `int`, `["requested_duration_seconds"]` as `int`, `["actual_duration_seconds"]` as `float` (plain `len(audio) / sample_rate`, matching the top-level metadata fields' types).

- [x] **Step 1: Write the failing test**

```python
def test_chunked_generation_records_numeric_durations_in_metadata():
    model = ChunkRecordingModel()
    playback = RecordingPlayback()
    manager = SessionManager(model=model, playback=playback, chunk_seconds=60)

    manager.start_session(make_request().model_copy(update={"duration_minutes": 5}))
    manager.wait_for_active_task()

    metadata = playback.loaded.metadata
    assert metadata["chunk_count"] == 5
    assert metadata["requested_duration_seconds"] == 300
    assert isinstance(metadata["requested_duration_seconds"], int)
    assert isinstance(metadata["actual_duration_seconds"], float)
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_session_manager.py::test_chunked_generation_records_numeric_durations_in_metadata -v`
Expected: FAIL — values are `"300"` (str) and `str`/`"1500.000000"`-style strings.

- [x] **Step 3: Implement in `_stitch_chunk_results`**

Replace the metadata update values with:

```python
"chunk_count": len(chunk_results),
"requested_duration_seconds": sum(result.duration_seconds for result in chunk_results),
"actual_duration_seconds": len(audio) / sample_rate,
```

- [x] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_session_manager.py tests/test_output_history.py tests/test_project_metadata.py -v`
Expected: all PASS.

- [x] **Step 5: Commit**

```bash
git add src/lofi_focus_tui/backend/session_manager.py tests/test_session_manager.py
git commit -m "fix: record generation durations as numbers in metadata"
```

---

### Task 6: Full verification, findings-log update, push to `dev`

**Files:**
- Modify: `UAT-FINDINGS.md` (mark issues 1–5 resolved with commit references)
- Modify: `docs/superpowers/plans/2026-10-11-uat-remediation.md` (tick checkboxes)

**Interfaces:** none.

- [x] **Step 1: Full gate**

Run: `.venv/bin/ruff check src tests && .venv/bin/python -m pytest -q`
Expected: 0 lint errors; all tests pass, 1 skipped (live gate needs env var).

- [x] **Step 2: Update `UAT-FINDINGS.md`**

Under each of the 5 issue headings, append one line: `**Resolved:** <commit short-hash> (<one-line what changed>).` Keep the observed/cause text intact — the file stays the running issues log.

- [x] **Step 3: Commit and push to `dev`**

```bash
git add UAT-FINDINGS.md docs/superpowers/plans/2026-10-11-uat-remediation.md
git commit -m "docs: mark UAT findings resolved"
git push origin dev
```

Expected: `origin/dev` contains the prior-session commit plus the six remediation commits; `main` untouched.

---

## Pull request outline (dev → main)

**Title:** `fix: remediate 2026-10-11 UAT findings (P2–P4)`

**Body:**

- Fixes all five findings from the 2026-10-11 UAT against real ACE-Step (`UAT-FINDINGS.md`); all gates had already passed — these are the follow-up dev-backlog fixes.
- [P2] ACE-Step HTTP adapter now uses a short connect timeout (10s) separate from the 1800s task timeout, so a firewall-dropped port fails fast with "cannot reach ACE-Step service at …" instead of hanging for 30 minutes (`http_ace_step.py`).
- [P3] The TUI status panel renders the captured `error` reason (dim, under the message) when state is `error` (`widgets.py`).
- [P3] Option-guide (`h`) and export (`e`) modals are centered at 64 columns like the main screen (`app.py` CSS).
- [P4] Prompt input gets a visible rounded border (`app.py` CSS).
- [P4] `metadata.json` `generation` block durations/chunk count are now numeric instead of strings (`session_manager.py`).
- Verification: `ruff` clean, full pytest suite green; manual UAT evidence in `UAT-REPORT-2026-10-11.md`.

Suggested command once `gh` is available: `gh pr create --base main --head dev --title "fix: remediate 2026-10-11 UAT findings (P2-P4)" --body-file <body>`
