# UAT Report — lofi-focus-tui — 2026-10-11

## Test record

| Item | Value |
| --- | --- |
| Tester | ZCode (automated UAT on behalf of the user) |
| Date | 2026-10-11 |
| OS | Debian GNU/Linux (kernel 6.12.111+deb13-amd64) |
| Python | 3.13.5 (clean venv, fresh `pip install -e ".[dev,playback]"`) |
| Branch | `dev` (clean tree at start) |
| Backend mode | `ace-step-http` — real ACE-Step-1.5, no mock |
| Remote endpoint | `http://192.168.2.220:8001` (API; the WebUI on 7860 is not the API the app uses) |
| Remote model | `acestep-v15-turbo`, healthy per `/health` and `/v1/models` |
| Config | `config.toml`: `inference_steps=8`, `guidance_scale` 15.0 (later user-tuned to 7.0, which Gate 4 used), `chunk_seconds=300`, `batch_size=1`, `timeout_seconds=1800` |
| Audio output | sounddevice (real device present) |

## Result: ALL REQUIRED GATES PASS

| Gate | Result | Evidence |
| --- | --- | --- |
| Lint + unit tests | PASS | `ruff check src tests` clean; `pytest -q` 303 passed, 1 skipped (live gate without env var) |
| 1 Fresh install | PASS | `lofi-doctor`: python/config/cache/outputs/device ok; only warning `ace-step: not installed` is accurate (embedded backend optional; HTTP mode used) |
| 2 Mock mode | SKIPPED by request | user explicitly requested non-mock UAT only |
| 3 Real ACE-Step short generation | PASS | live pytest + driven TUI session (details below) |
| 4 Real chunked generation | PASS | 25-minute session, 5 chunks (details below) |
| 5 Error UX | PASS | bad URL → `state: error`, `message: generation failed`; new session starts without restart; clean quit |

## Gate 3 — short generation (5 minutes)

- `LOFI_UAT_ACE_STEP_BASE_URL=http://192.168.2.220:8001 LOFI_UAT_ACE_STEP_SECONDS=300
  pytest tests/test_live_ace_step_http.py -v` → **PASSED in 74s**; evidence at
  `.uat/ace-step-http/20261011T195933Z_ace_step_15_http_uat/` (audio.wav 300.0s @ 48 kHz,
  peak 0.762, rms 0.121, non-silent, unclipped, metadata.json).
- Driven TUI session (real keystrokes in a pty): cycled duration 30→5, focus→coding,
  preset→ambient_tape, style→rainy, mellow; edited free-form prompt ("soft rain on glass,
  warm tape hiss") and verified it appears on screen and propagates into saved metadata
  (request → plan → blueprint.prompt); guide opens with `h` and closes with both `Escape`
  and `h`; 25/26 automated checks passed (the one FAIL was a driver regex artifact; the
  history rendering was verified on screen and in `history.jsonl`).
- Generation completed well inside `timeout_seconds`; state went `generating` →
  `playing` with the position line `…s / 300.0s` ticking — audio actually audible via
  sounddevice.
- Transport: pause→`paused`, resume, refresh, rewind/forward, restart (position back to
  1.4s), volume 80%→70%.
- Session saved to `~/.cache/lofi-focus-tui/outputs/993d0859-…_ambient_tape/`
  (audio.wav 300.0s, peak 0.836, rms 0.153, non-silent, unclipped + full metadata:
  request, plan, blueprint, settings, requested/actual duration, backend, task_id,
  seed, device, chunk profile).
- Export (`e` → Enter on default dir) → `session exported`; files at
  `~/Music/lofi-focus-tui/993d0859-…_ambient_tape/{audio.wav,metadata.json}`.

## Gate 4 — chunked generation (25 minutes, chunk_seconds=300)

- Duration cycled to 25 minutes; chunk plan `chunks: 0/5` displayed; `chunks: i/5`
  visible after every chunk.
- Stop pressed right after chunk 1 completed (between chunks): UI acknowledged in
  **0.5s** with `message: stopped`; a new session then started normally.
- Full run: all 5 chunks generated, state → `playing`, position line `…s / 1496.0s`.
- Output: `~/.cache/lofi-focus-tui/outputs/b7e489b1-…_classic_lofi/` — audio.wav
  143.6 MB, 1496.0s @ 48 kHz (1500s requested; 4 seams × 1s crossfade), peak 0.839,
  rms 0.143, non-silent, unclipped.
- Metadata distinguishes requested (1500) from actual stitched duration (1496) and has
  5 chunk records; all 4 boundary reports `accepted: true`, `severe: false`, no
  warnings. Independent sample-level check at the seams found max jumps 0.003–0.033
  vs 0.127 global p99.9 — no click/pop signal at chunk boundaries.
- Note: this run used the user-tuned `guidance_scale = 7.0` (config edited mid-UAT).

## Gate 5 — error UX

- Bad URL (`http://127.0.0.1:59999`, connection refused): `state: error` and
  `message: generation failed` in red; pressing `s` again starts a new session without
  restarting; `q` exits cleanly. Screenshot: `/tmp/lofi_uat/lofi_5_error.png`.

## Human listening check (pending — requires human ears)

Automated checks prove the audio is non-silent, unclipped, and seam-continuity passed.
The subjective criteria (focus-friendly, no vocals, no distracting artifacts, no timbre
jump at chunk seams) still need a human listen. Candidates:
`~/.cache/lofi-focus-tui/outputs/b7e489b1-…_classic_lofi/audio.wav` (25 min) and
`~/Music/lofi-focus-tui/993d0859-…_ambient_tape/audio.wav` (5 min).

## Findings / dev backlog

See [UAT-FINDINGS.md](UAT-FINDINGS.md) — 5 items (1×P2 fast-fail on firewall-dropped
ports, 2×P3 TUI: error reason not rendered, modals not centered; 2×P4 cosmetic).
None block the release decision; the P2 is the one most worth fixing first.

## Release decision

Per docs/user-acceptance-testing.md: lint+tests pass, real short generation passes,
real chunked generation passes, error UX passes — **release-ready from an automated
standpoint**, pending the human listening check. Mock gate (Gate 2) was skipped by
request and should be run if the full checklist is required.
