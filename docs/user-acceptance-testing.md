# User Acceptance Testing

Use this checklist before treating the fork as release-ready. Automated tests prove the
core contracts; UAT proves the installed app is usable, audible, and clear under realistic
generation conditions.

## Required Result

All gates below must pass. Real ACE-Step generation is a required acceptance gate, not an
optional smoke test.

Record the tester name, date, operating system, Python version, backend mode, GPU or remote
endpoint, commands run, generated output paths, and pass/fail notes.

## Gate 1: Fresh Install

1. Clone the fork branch.
2. Create and activate a clean virtual environment.
3. Run:

   ```bash
   python -m pip install -e ".[dev,playback]"
   lofi-doctor
   ```

4. Pass criteria:
   - Python, config, cache, and outputs checks are `ok`.
   - Backend is either reachable or clearly reported as not running.
   - Optional ACE-Step/playback warnings match the selected test environment.

## Gate 2: Mock Mode Workflow

1. Ensure `generation.backend = "mock"` in `config.toml`, or remove local config.
2. Start the backend:

   ```bash
   lofi-backend
   ```

3. Start the TUI in a second terminal:

   ```bash
   lofi
   ```

4. Exercise the TUI:
   - Cycle preset, duration, energy, and style.
   - Start a session.
   - Pause, resume, stop, and refresh.
   - Confirm status, progress, playback mode, chunk status, and recent history are legible.

5. Pass criteria:
   - The app does not crash.
   - Status updates are understandable.
   - Saved output contains `audio.wav` and `metadata.json`.
   - If no playback device is available, status says playback is disabled instead of implying audible playback.

## Gate 3: Real ACE-Step Short Generation

Use `ace-step-http`, `runpod`, or embedded `ace-step`. HTTP mode is preferred for UAT because
it keeps the TUI/backend contract independent from model-process lifecycle issues.

Example `config.toml`:

```toml
[generation]
backend = "ace-step-http"
chunk_seconds = 300
inference_steps = 27
batch_size = 1

[ace_step_http]
base_url = "http://127.0.0.1:8001"
timeout_seconds = 1800.0
```

1. Start the ACE-Step service or remote endpoint.
2. Start `lofi-backend`.
3. Start `lofi`.
4. Cycle duration to `5 minutes`.
5. Start a session.

Pass criteria:
- Generation completes before `timeout_seconds`.
- The backend does not hang indefinitely if the remote task stalls.
- `audio.wav` is valid, non-silent, and not clipped.
- Metadata records request, plan, blueprint, settings, requested duration, actual duration, backend, seed, and generation metadata.
- Human listening check: instrumental, focus-friendly, no vocals, no harsh clipping, no obvious distracting artifacts.

## Gate 4: Real ACE-Step Chunked Generation

Use the same real backend with a duration longer than `chunk_seconds`. A practical test is
`10 minutes` with `chunk_seconds = 300`, or `25 minutes` with the default TUI options.

Pass criteria:
- Chunk progress is visible.
- Stop remains responsive between chunks.
- Final output has no obvious seam, click, loudness jump, or timbre jump at chunk boundaries.
- Metadata distinguishes requested duration from actual stitched duration after crossfades.
- Recent history includes the generated session.

## Gate 5: Error UX

Run one intentional failure, such as a bad ACE-Step HTTP URL or invalid API key.

Pass criteria:
- Backend status enters `error`.
- The TUI displays an understandable message.
- The app can start a new valid session after the failure without restarting the terminal.

## Release Decision

The fork is release-ready only when:

- Lint and tests pass.
- Mock UAT passes.
- Real ACE-Step short generation passes.
- Real ACE-Step chunked generation passes.
- Error UX is understandable.
