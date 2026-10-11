# UAT Findings — 2026-10-11 (dev session backlog)

Findings from UAT performed against the real ACE-Step-1.5 HTTP service at
`http://192.168.2.220:8001` (WebUI on 7860, API on 8001), app installed fresh from the
`dev` branch into a clean venv (Python 3.13.5). Working notes for a future development
session; nothing here blocks release except where marked.

## Issues to fix

### 1. [P2] Backend hangs for the full timeout when the ACE-Step port is firewall-dropped
**Resolved:** 080cb07 — adapter now defaults to a 10s connect timeout separate from the
1800s task timeout and raises `RuntimeError: cannot reach ACE-Step service at <base_url>`
on connection errors (rendered in the TUI via finding 2's fix).
- **Observed:** with `base_url = http://192.168.2.220:9999` (host reachable, port
  silently DROPped by the remote firewall), the app sat in `state: generating`,
  `message: generating`, `progress: 50%` for 120s+ (test stopped there) and would hang
  until `timeout_seconds = 1800`. A user gets no error and no way to tell it is stuck.
- **Cause:** `AceStepHttpAdapter` passes a single `timeout_seconds` (1800s) to the
  httpx client (`src/lofi_focus_tui/generation/http_ace_step.py:111-113`). TCP connect
  to a dropping host blocks until that timeout. `/format_input` caps at 30s
  (`http_ace_step.py:163`) but the subsequent `/release_task` POST uses the full 1800s
  client timeout.
- **Suggested fix:** separate short connect timeout (e.g. `httpx.Timeout(connect=10,
  read=timeout_seconds)`) so unreachable hosts fail fast, and surface a distinct
  "cannot reach ACE-Step service" message.
- Related UAT Gate 3 criterion: "The backend does not hang indefinitely if the remote
  task stalls."

### 2. [P3] Error reason is captured but never shown in the TUI
**Resolved:** 1ea597b — `render_status` appends an `error: <reason>` line (dim) under the
message when `state == "error"` and a reason is present.
- **Observed:** Gate 5 (bad URL that refuses): TUI shows only `state: error`,
  `message: generation failed` (rendered in red — see `/tmp/lofi_uat/lofi_5_error.png`).
  The underlying cause (e.g. connection refused) never appears.
- **Cause:** `SessionManager` stores `error=str(exc)` in the status
  (`src/lofi_focus_tui/backend/session_manager.py:315`), `BackendStatus.error` exists
  (`src/lofi_focus_tui/domain.py:184`), but `render_status`
  (`src/lofi_focus_tui/tui/widgets.py:66-88`) never renders it.
- **Suggested fix:** render `status.error` (dim/small) under the message line when
  `state == "error"`.

### 3. [P3] Modal screens are flush-left / full-bleed instead of centered
**Resolved:** 878c08b — `#option-guide` and the export-screen widgets get `width: 64`, so
the existing `align: center middle` rule centers them like the main screen.
- **Observed:** option guide (`h`) and export dialog (`e`) render at column 0 and the
  export Input spans the full terminal width (verified at 110×50), while every main
  screen widget is centered at 64 columns. Screenshots: `/tmp/lofi_uat/lofi_3_guide.png`,
  `/tmp/lofi_uat/lofi_4_export_dialog.png`. No text is lost, but it is visually
  inconsistent with the polished main screen.
- **Likely cause:** the app CSS `Screen { align: center middle; }` and the
  `width: 64` rule only target the main screen's widget IDs
  (`src/lofi_focus_tui/tui/app.py:80-86`); the modals' `#option-guide` Static and
  export Input get default width (100%) so centering is a no-op.
- **Suggested fix:** give `#option-guide` and the export Input `width: 64` (or an
  appropriate max-width) so modals match the main layout.

### 4. [P4] Prompt input border is nearly invisible on the idle screen
**Resolved:** 05e5a76 — `#prompt` gets `border: round #666666` (the default was a
`#191919` tall border, effectively invisible on dark backgrounds; a fixed neutral gray
is used because `city_pop.label` is the style name "dim", not a color).
- **Observed:** on the main screen the empty prompt Input reads as a faint dark box;
  its border blends into the background (city_pop theme). After typing, the text is
  clear but the control boundary stays subtle.
- **Suggested fix:** theme the Input border (e.g. `theme.label` color) in
  `src/lofi_focus_tui/tui/app.py` CSS.

### 5. [P4] Generation-block durations in metadata.json are strings
**Resolved:** ae439de — `_stitch_chunk_results` now emits `chunk_count` (int),
`requested_duration_seconds` (int) and `actual_duration_seconds` (float) as numbers.
- **Observed:** `generation.requested_duration_seconds` is `"1500"` and
  `generation.actual_duration_seconds` is `"1496.000000"` (JSON strings), while the
  top-level `duration_seconds` / `actual_duration_seconds` are numeric. Consumers must
  type-coerce; the inconsistency looks unintentional.
- **Suggested fix:** emit numbers from the output manager / session metadata writer.

## Notes (not defects)

- For single-chunk sessions the transient `generated chunk 1/1` message is superseded
  by `playing` before a repaint, so users never see per-chunk progress when
  `chunk_count == 1`. Harmless; only matters if single-chunk progress is wanted.
- `chunks: i/n` only renders when `chunk_count > 1` (`render_status`), so the 5-minute
  default (600s chunks) shows no chunk line — expected.
- `render_history` keeps the last 5 sessions; the `recent:` block renders correctly
  (verified on screen and in `~/.cache/lofi-focus-tui/history.jsonl`).

## Verification evidence (passes)

- Gate 1: fresh venv install, `lofi-doctor` all-ok, ruff clean, 303 tests passed.
- Gate 3a: `tests/test_live_ace_step_http.py` PASSED with real 300s generation (74s);
  evidence `.uat/ace-step-http/20261011T195933Z_ace_step_15_http_uat/`.
- Gate 3b: driven TUI session — all options cycle, prompt edit, guide open/close
  (Escape and h), 5-min generation, audible playback (sounddevice), pause/restart/seek/
  volume, session saved (audio.wav + metadata.json), export, stop, clean quit.
  Audio validated: non-silent, unclipped, 300.0s @ 48kHz.
- Gate 4: chunk progress visible for all 5 chunks (`chunks: i/5`), stop between chunks
  responded in 0.5s, stitched 1496s output (4×1s crossfades), 5 chunk records with
  boundary continuity accepted on every seam, no click-signal at seams (max sample jump
  at seams 0.003–0.033 vs 0.127 global p99.9), audio non-silent/unclipped, clean quit.
- Gate 5: `state: error` + `message: generation failed`, app accepts a new session
  afterwards and quits cleanly.
