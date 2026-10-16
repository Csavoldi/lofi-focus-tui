---
id: TASK-3
title: 'Live end-to-end session test: runtime + SessionManager against real ACE-Step
  generation'
status: To Do
created_date: 2026-10-06 05:05
dependencies:
- TASK-2
labels:
- tests
- ace-step
- live
priority: High
references:
- tests/test_live_ace_step_http.py
- tests/test_session_manager.py
- src/lofi_focus_tui/runtime.py
- src/lofi_focus_tui/backend/session_manager.py
- docs/user-acceptance-testing.md
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Existing live coverage stops at `AceStepHttpAdapter.generate()` (`tests/test_live_ace_step_http.py`). The TUI-facing path — `runtime.build_backend(config)` → `SessionManager` → generate → persist/export → history — is only ever exercised with `MockModelAdapter`. So a regression in the real wiring (config plumbing, chunk_seconds/backend selection, status transitions, output/history persistence) can pass the whole suite while live sessions fail.

Add a live, non-mock end-to-end test that drives the app's own construction path against a real ACE-Step-1.5 HTTP service and asserts the observable contract the TUI relies on.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Test is marked `live`, skips cleanly without LOFI_UAT_ACE_STEP_BASE_URL, and is bounded by an env-tunable timeout
- [ ] #2 Asserts the real session lifecycle: idle/planning/generating/ready transitions observed via the session manager, then stop/shutdown without exceptions
- [ ] #3 Asserts audio properties on real output: sample_rate > 0, non-silent, not clipped, and length within tolerance of the requested duration
- [ ] #4 Asserts persistence: audio.wav and metadata.json exist with backend/seed/requested-vs-actual duration and ACE-Step generation metadata, and the session appears in history
- [ ] #5 Passes against the deployed HTTP service end to end; any production-code change required to make it pass is recorded as a finding rather than silently patched
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Build the app objects the way the app does: `AppConfig` with `generation.backend = "ace-step-http"`, `ace_step_http.base_url` from the shared live fixture, small `batch_size`, low `inference_steps`, and a short bounded duration (10-20 s) so GPU time stays predictable.
2. Use `runtime.build_backend(config)` (or the SessionManager constructor used by `runtime`) rather than instantiating the adapter directly, so the test fails if real config plumbing breaks.
3. Drive a session start and observe states; assert `generating` is reached and then `ready`, and that `stop()`/shutdown stay responsive and exception-free.
4. Assert audio contract on the returned buffer: `sample_rate > 0`, `not is_silent`, `not is_clipped`, and length within a documented tolerance of the requested duration.
5. Assert persistence and history: `audio.wav` + `metadata.json` written, metadata carries backend/seed/requested vs actual duration plus ACE-Step `generation_metadata`, and the session record is readable from the history store.
6. Keep runtime bounded via env-tunable duration/steps/timeout and reuse the TASK-2 fixture gate.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:IMPLEMENTATION_NOTES:BEGIN -->

<!-- SECTION:IMPLEMENTATION_NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->

<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Test file added under tests/ and covered by the shared live fixture from TASK-2
- [ ] #2 Default suite still passes with the new test skipped
- [ ] #3 At least one recorded live pass with evidence path captured in the task notes
- [ ] #4 Assertions document the tolerance/threshold values used for real audio
<!-- DOD:END -->
