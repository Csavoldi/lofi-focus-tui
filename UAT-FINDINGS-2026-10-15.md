# UAT Findings — 2026-10-15 (interactive pass, vision + click-through)

> **Resolution status (2026-10-15, TASK-8):** findings 2-8 are fixed in code and covered by
> tests (`pytest -q`: 354 passed). Finding 1 was resolved operationally per maintainer
> decision: the `ace-step-http` REST backend stays the only supported path; run the API
> server on the GPU host with `uv run acestep-api` (docs/ace-step.md). `lofi-doctor` now
> probes the configured service and prints that exact command when it is unreachable, and
> the app config was restored to `http://192.168.2.220:8001`. The Gradio WebUI on 7860 is
> not directly usable by the app.

UAT performed against the real ACE-Step-1.5 **Gradio WebUI** at `http://192.168.2.220:7860`.
The REST wrapper (`acestep-api`, port 8001) is **not running** today, so live generation was
routed through a local REST-to-Gradio bridge (`/tmp/uat_bridge.py`, listening on
`127.0.0.1:8001`) that presents the `/health`, `/format_input`, `/release_task`,
`/query_result`, `/v1/audio` contract the app expects. The app under test was unchanged.
Method: key-driven click-through of the TUI in tmux with screen captures, real audio
generation, and signal + spectrogram (vision) analysis of the produced audio.

Environment: Fedora (kernel 7.2.9-200.fc44), Python 3.14.8, dev branch @ fe73d29,
`backend = "ace-step-http"`, `inference_steps = 8`, `guidance_scale = 7.0`,
playback via sounddevice. Baseline `pytest -q` (fake pipeline): **passed**.
Live gate `LOFI_UAT_ACE_STEP_BASE_URL=http://127.0.0.1:8001 pytest tests/test_live_ace_step_http.py`: **passed** (evidence under `.uat/ace-step-http/20261015T152721Z_*`).

## What worked (verified end-to-end)

- Fresh app start shows `backend: ace-step-http`, `message: ready`; `lofi-doctor` all ok
  (expected embedded-model warning only).
- All option cycling works and is reflected live: focus (`1`), preset (`p`), duration (`2`),
  energy (`3`), style (`4`), theme (`t`), prompt editing (`i`/Escape), vocal toggle (`v`).
- Option guide (`h`) opens/closes (`Escape`/`h`); session keys are suppressed while open;
  `q` remains global quit.
- Real 5-minute generation (single 300s chunk) completed in ~130s and played correctly.
- Full playback contract: pause/resume, volume ±10%, seek ±10s, restart, refresh, stop,
  quit — all behave as documented.
- Export (`e`) writes `audio.wav` + `metadata.json` under `~/Music/lofi-focus-tui/<session>/`.
- Metadata is complete: request, plan, blueprint, settings, requested vs actual duration,
  backend, seed, task id, per-chunk quality profiles.
- Chunked generation (5 min, `chunk_seconds = 150`, 2 chunks): chunk progress visible
  (`chunks: 0/2` → `generated chunk 1/2` → `2/2`), stop responsive during generation,
  stitched duration 299.0s documented as actual vs 300 requested.
- Error UX (Gate 5): backend failures put the app in `state: error` with the reason shown,
  and **new sessions can be started from the same app instance without restarting** —
  verified twice after real remote failures.

## Issues found

### 1. [P1] App cannot use the actually-running ACE-Step service (Gradio UI on 7860)
**Resolved operationally (maintainer decision):** the REST API server stays the required
backend. `lofi-doctor` now probes `{base_url}/health` and, when unreachable, prints
"start it on the GPU host with `uv run acestep-api`" (src/lofi_focus_tui/diagnostics.py).
- **Observed:** the only ACE-Step-1.5 service running on 192.168.2.220 today is the Gradio
  WebUI on port 7860. The `ace-step-http` adapter requires the `acestep-api` REST wrapper
  (`/release_task`, `/query_result`, `/v1/audio`, `/health`), which is down (8001 times
  out). Pointed at 7860 the app gets 404s from `/health` and cannot generate at all.
- **Impact:** with the current deployment, a fresh user following the README reaches for a
  service the app cannot talk to. UAT could only proceed via a protocol bridge.
- **Suggested fix:** either (a) document + operationalize `uv run acestep-api` as the
  required companion service (and keep 8001 alive), or (b) add a Gradio-adapter backend
  (`gradio` transport for `generation_wrapper`) so the WebUI deployment works directly.
  Note the deployed Gradio build differs from GitHub main (78 inputs incl. States, int-valued
  sample-rate choices, DCW on by default) — an adapter must derive the input layout from
  `/config`, not from a hard-coded list.

### 2. [P1] Remote long-chunk generation stalls crash the session ~10 minutes in; app shows a flat 50% the whole time
**Resolved:** the status line now animates during generation — elapsed seconds and the
current chunk are derived in `SessionManager.health()` (`message: generating chunk 1/2,
26s elapsed`, progress creeps monotonically and jumps at each completed chunk; verified
live: 12% → 22% → 52% → 66% → 100%). Mid-request transport failures
(`ReadError`/connection resets) are wrapped as "lost connection to the ACE-Step service at
<url> (it may be restarting)" in `AceStepHttpAdapter._post/_get`.
- **Observed:** a 25-minute session (5×300s chunks) sat at `state: generating`,
  `progress: 50%`, `message: generating`, `chunks: 0/5` for 620s, then failed. The remote
  ACE-Step handler had timed out after its own 600s cap ("GPU ran out of VRAM or the
  diffusion loop stalled"), and a retry immediately after died with
  `ReadError: [Errno 104] Connection reset by peer` while the Gradio server restarted.
- **App-side gaps:** (a) during the whole wait there is no elapsed-time or per-chunk
  activity indication — 50% + "generating" for 10 minutes is indistinguishable from a hang;
  (b) the surfaced error for the connection reset is a raw Python exception string
  (`AceStepHttpAdapter._post` wraps `ConnectError`/`ConnectTimeout` but not mid-request
  `ReadError`/remote resets), so the user sees `ReadError: [Errno 104]...` with no
  "ACE-Step service unreachable/restarting" framing.
- **Suggested fix:** show elapsed generation time and current chunk in the status line;
  wrap transport-level `httpx.HTTPError` generally into a friendly message; consider
  treating "no chunk completed within N minutes" as a visible stall warning.

### 3. [P2] Generated audio is mono; earlier REST deployment produced stereo
**Resolved:** mono chunks are upmixed to two identical channels at ingest
(`ensure_stereo` in `audio/normalization.py`, applied in `SessionManager._generate_chunk`);
a live 2-chunk session exported as 48 kHz stereo (`channels=2`).
- **Observed:** both generated sessions exported as 48 kHz 16-bit **mono** WAVs. The
  2026-10-06 UAT of the 8001 REST service recorded 48 kHz stereo. Playback works, but
  focus music through one channel is a perceptible quality regression for headphone users.
- **Cause:** the Gradio `generation_wrapper` path returns mono; the app passes channels
  through unchanged.
- **Suggested fix:** document the channel behavior per backend, and/or upmix mono→stereo
  on ingest in `audio/` post-processing (cheap, deterministic).

### 4. [P2] Chunk seams are click-free but musically audible: ~5-6s energy dip to near-silence at each boundary
**Resolved (two-layer fix, live-verified 2026-10-15 against the restarted REST API):**
(a) internal chunk prompts now carry explicit continuity constraints ("carries full
energy through the final bar, ending mid-groove" / "begins mid-groove at full
energy...") via `create_chunk_blueprint`; (b) since prompts alone did not stop the
model's fades on a live take (a constraint-only session still dipped to RMS ≈ 0.0008
before the boundary), `trim_edge_silence` cuts the fade tails at internal chunk
boundaries before the crossfade — the quiet test is adaptive (absolute silence floor or
−9 dB against the chunk's own loud level, so gradual fades are caught, not just digital
silence), bounded at 15% of the chunk, and whole-chunk silence is left intact. The
crossfade default also grew 1s → 2s. Live re-measure (2×150s session through the real
`acestep-api` service): the trimmer removed ~11.4s of fades (stitched 286.65s from
300s requested), boundary levels balanced (left 0.119 / right 0.124 RMS, spectral delta
0.032), and the seam envelope holds at ~0.13 RMS into the boundary with only a ~1s duck
to 0.036 during the crossfade — versus the pre-fix 5-6s plunge to 0.0007.
- **Observed:** in the 2-chunk session, RMS falls from ~0.02 to ~0.0007 over t≈143-148s
  and recovers at t≈149s (the 150s boundary). Spectrogram confirms both chunks carry their
  own outro/intro fades; the app's 1s linear crossfade cannot bridge multi-second
  fade-outs on both sides. Metadata's boundary check accepts it (delta 0.0018, not severe)
  because it compares levels at the cut point, not the surrounding musical energy.
- **Impact:** Gate 4's "no obvious seam/loudness jump" is met technically (no click, no
  level jump) but each chunk transition sounds like the track ending and restarting.
- **Suggested fix:** prompt chunks as continuous sections (avoid outro/intro tags at
  internal boundaries), and/or lengthen the crossfade to overlap the fades; extend the
  boundary check to consider pre/post-boundary energy envelopes.

### 5. [P3] Generation progress is a flat 50% for the entire single-chunk wait
**Resolved:** same live-progress mechanism as finding 2; verified live during a real
130s generation.
- **Observed:** during the ~130s 5-minute generation, `progress: 50%` and
  `message: generating` never change (no polling feedback exists in the HTTP contract).
  Same root as finding 2a but visible even in the happy path.
- **Suggested fix:** animate the message (elapsed seconds), or map poll count to a
  pseudo-progress; the remote task API offers no true progress.

### 6. [P3] Export modal gives no cue that Enter is required
**Resolved:** the modal now shows a dim "Enter to export · Escape to cancel" caption
(`#export-hint` in `ExportScreen`).
- **Observed:** `e` opens the export dialog pre-filled with `~/Music/lofi-focus-tui`;
  nothing happens until Enter is pressed, and the dialog shows no hint or default-button
  affordance. Escape cancels (undocumented in-dialog).
- **Suggested fix:** add a dim "Enter to export · Escape to cancel" caption in the modal.

### 7. [P3] On-screen controls line omits several documented keys
**Resolved:** `render_controls` now renders two rows — an options row
(`i prompt  v mode  1 focus  p preset  2 duration  3 energy  4 style  t theme  h guide`)
above the playback row.
- **Observed:** the controls row lists only playback keys; `i`, `v`, `1-4`, `h` are
  documented in the README but not visible in the TUI itself (the guide lists option
  catalogs, not key bindings).
- **Suggested fix:** extend the controls line or the guide header with the full key map.

### 8. [P3] Local config drift: `inference_steps = 27`, `guidance_scale = 15.0`
**Resolved:** `lofi-doctor` gained a `generation settings` check that warns when values
drift far from the turbo recommendation (verified: `inference_steps=27` → warn naming
docs/ace-step.md). The local config was reset to the recommended 8 / 7.0.
- **Observed:** `config.toml` as found had 27/15.0 vs the recommended turbo values 8/7.0
  (docs: "Generation defaults follow the 1.5 turbo recommendations"). This makes every
  generation ~3× slower for no quality gain (guidance only affects base/sft models).
  Reset to 8/7.0 for this UAT.
- **Suggested fix:** warn in `lofi-doctor` when `inference_steps`/`guidance_scale` deviate
  strongly from the documented recommendation for turbo checkpoints.

## Audio quality verdict (human-listening proxies)

- 5-min neo_soul session: integrated **−21.2 LUFS**, LRA 5.7, true peak −3.6 dBFS, zero
  clipped samples, DC ≈ 0, clean fade-in/out. Spectrogram (vision) shows coherent lofi
  texture: sustained bass <150 Hz, mid-range keys/harmonics, gentle HF roll-off, steady
  pulse, no noise bursts or aliasing spikes. One stylistic low-pass breakdown at
  t≈133-147.5s (highs at digital silence, mids/bass continue) — judged musical
  (tape-style breakdown), not an artifact.
- 2-chunk classic_lofi session: **−20.0 LUFS**, LRA 7.1, no clipping; same coherent
  texture; seam behavior per finding 4.
- Both tracks are usable, focus-appropriate instrumental lofi; loudness is on the quiet
  side of streaming targets but suits background focus (the app normalizes peak, not LUFS).

## Artifacts

- Sessions: `~/Music/lofi-focus-tui/83c959b8-..._neo_soul/`, `~/Music/lofi-focus-tui/c195c7f0-..._classic_lofi/`
- Analysis images: `/tmp/uat_viz/` (spectrograms incl. seam + breakdown close-ups, waveform)
- Bridge (left running for retests): `/tmp/uat_bridge.py` on `127.0.0.1:8001`; log `/tmp/uat_bridge.log`
- Live-test evidence: `.uat/ace-step-http/20261015T152721Z_ace_step_15_http_uat/`
