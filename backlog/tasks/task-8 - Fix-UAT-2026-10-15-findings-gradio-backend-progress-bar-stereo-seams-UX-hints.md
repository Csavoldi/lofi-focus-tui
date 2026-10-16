---
id: TASK-8
title: 'Fix UAT 2026-10-15 findings: gradio backend, progress bar, stereo, seams,
  UX hints'
status: Done
created_date: 2026-10-15 15:59
updated_date: 2026-10-15 18:25
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement fixes for all findings in UAT-FINDINGS-2026-10-15.md: (1) new ace-step-gradio backend talking directly to the Gradio service at 7860; (2) live progress bar with elapsed time + friendly transport error messages; (3) mono-to-stereo upmix at ingest; (4) continuous chunk section prompts to avoid seam silence dips; (6) export modal Enter hint; (7) full key map in controls line; (8) lofi-doctor warning for drifted inference/guidance settings.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:IMPLEMENTATION_NOTES:BEGIN -->
Implementation (all in dev working tree, TASK-8):

- Finding 3 (mono): ensure_stereo() in audio/normalization.py, applied in SessionManager._generate_chunk; mono backends now persist stereo WAVs (verified live: channels=2).
- Findings 2+5 (progress): SessionManager.health() derives live fields while GENERATING — progress creeps asymptotically per chunk (floor jumps on chunk completion, capped at 95%) and message shows "generating chunk N/M, Ns elapsed". Verified live through a real 2-chunk generation: 12%→22%→52%→66%→100%.
- Finding 2b (errors): AceStepHttpAdapter._post/_get now wrap all httpx.TransportError as "lost connection to the ACE-Step service at <url> (it may be restarting)" (connect errors keep the "cannot reach" wording).
- Finding 4 (seams): create_chunk_blueprint appends positive continuity constraints at internal boundaries; trim_edge_silence() (normalization.py) cuts quiet fade tails at internal chunk edges before crossfade (50ms windows, RMS 0.004 threshold, 15% cap, all-silent chunks untouched); crossfade default 1s→2s. Live re-measure pending service recovery (GPU host went down mid-verification); unit tests cover the trimmer.
- Finding 6: ExportScreen shows "Enter to export · Escape to cancel" hint.
- Finding 7: render_controls renders options row + playback row with the full key map.
- Finding 8 + 1 (operational): lofi-doctor gained "generation settings" drift warning (thresholds: steps > 2x8 or guidance > 10) and "ace-step service" probe of {base_url}/health that prints "start it on the GPU host with `uv run acestep-api`" when unreachable. Probe hardened per security hook: http(s) only, follow_redirects=False.
- Maintainer decision: no Gradio adapter — ace-step-http REST backend stays the only path; config.toml restored to http://192.168.2.220:8001, chunk_seconds 600, inference 8 / guidance 7.0.

Verification: ruff clean; pytest -q 354 passed, 1 skipped (live gate). Live: doctor output shows both new checks; progress bar + stereo verified on real generations through the REST-to-Gradio bridge; UAT-FINDINGS-2026-10-15.md updated with per-finding resolution notes.
Trimmer refinement during verification: the absolute silence floor only caught digital-silence tails; the threshold is now adaptive (max(0.004, 0.35 x 95th-percentile window RMS)), so gradual fades are trimmed too. Integration test test_chunk_seams_do_not_dip_to_silence_when_model_fades_edges reproduces the UAT failure shape (3s faded edges per chunk) and asserts every seam-side 200ms window stays above 0.05 RMS. Note discovered while testing: a linear crossfade can cancel exactly anti-phase correlated material — synthetic test chunks therefore use distinct pitches like real independent takes; production crossfade left unchanged.

Final verification: ruff clean, pytest -q 355 passed 1 skipped. Both remote ports (7860 Gradio, 8001 REST) unreachable at close of work, so the live seam re-measure is documented as pending in UAT-FINDINGS-2026-10-15.md; bridge stopped and config.toml restored to the maintainer's intended setup (ace-step-http @ http://192.168.2.220:8001, chunk_seconds 600, inference 8 / guidance 7.0).
Post-fix live verification against the restarted acestep-api REST service at 192.168.2.220:8001: lofi-doctor shows [ok] ace-step service reachable; live pytest gate passed (75.8s); real 2x150s TUI session verified the progress bar (15%->51% on chunk completion->63%->100%), stereo export (channels=2), and the seam fix — trimmer removed ~11.4s of fades (286.65s stitched from 300s), boundary left/right RMS 0.119/0.124, spectral delta 0.032, seam envelope ~0.13 RMS with only a ~1s crossfade duck to 0.036 (pre-fix: 5-6s at 0.0007). Integrated loudness -16.1 LUFS, LRA 9.3. Config restored to chunk_seconds 600 after the test.
Endpoint move (2026-10-15 later): ACE-Step REST service now runs on 192.168.2.216:8010 (host debianv100s, V100). Fixed on the server via SSH: systemd user unit acestep-api.service was bound to 127.0.0.1 — rebound to 0.0.0.0; unit also ran the base model in fp16 which produced NaN latents on 300s generations (pre-Ampere V100) — switched ACESTEP_CONFIG_PATH to acestep-v15-turbo, matching the app's documented turbo defaults. Verified end-to-end: lofi-doctor [ok], live gate passed (76.9s), real 5-minute TUI session generated in ~135s and exported as 48 kHz stereo, 300.0s, -14.8 LUFS. config.toml base_url now http://192.168.2.216:8010.
<!-- SECTION:IMPLEMENTATION_NOTES:END -->
## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
All UAT 2026-10-15 findings addressed. Progress bar now animates live during generation (elapsed seconds + chunk N/M in the message, monotonic progress with per-chunk jumps — verified on a real generation); transport failures surface as friendly "cannot reach / lost connection to the ACE-Step service" messages instead of raw exceptions. Mono backend output is upmixed to stereo at ingest (live-verified channels=2). Chunk seams: continuity constraints in internal-chunk prompts plus an adaptive fade-tail trimmer (unit + integration tested) and a 2s crossfade. Export modal shows the Enter/Escape hint; the controls line shows the full key map; lofi-doctor warns on drifted inference/guidance settings and probes the configured ACE-Step service, printing the exact `uv run acestep-api` command to start it. Per maintainer decision the REST API server remains the only supported backend (no Gradio adapter). ruff clean; pytest 355 passed, 1 skipped (live gate). Config restored to the intended remote service; live seam re-measure pending GPU-host availability.
<!-- SECTION:FINAL_SUMMARY:END -->
## Definition of Done
<!-- DOD:BEGIN -->
<!-- DOD:END -->
