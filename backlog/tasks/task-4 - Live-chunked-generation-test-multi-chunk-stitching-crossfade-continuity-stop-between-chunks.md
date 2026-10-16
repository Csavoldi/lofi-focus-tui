---
id: TASK-4
title: 'Live chunked generation test: multi-chunk stitching, crossfade continuity,
  stop between chunks'
status: To Do
created_date: 2026-10-06 05:05
dependencies:
- TASK-2
- TASK-3
labels:
- tests
- ace-step
- live
- continuity
priority: Medium
references:
- src/lofi_focus_tui/backend/session_manager.py
- src/lofi_focus_tui/audio/continuity.py
- docs/user-acceptance-testing.md
- tests/test_continuity.py
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Gate 4 in `docs/user-acceptance-testing.md` ("Real ACE-Step Chunked Generation") is a manual checklist: generate longer than `chunk_seconds`, watch chunk progress, confirm stop is responsive, and judge seam/loudness/timbre continuity by ear. The chunking and crossfade logic lives in `backend/session_manager.py` with continuity helpers in `audio/continuity.py`, but every existing test of that path uses `MockModelAdapter` audio — where seams, clicks and loudness jumps of the kind real crossfades can produce do not occur.

Add a live, non-mock chunked-generation test that drives multiple real chunks and validates the stitched result numerically as well as structurally.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Test is marked `live`, skips cleanly without LOFI_UAT_ACE_STEP_BASE_URL, and completes within an env-tunable bounded runtime
- [ ] #2 Asserts chunk accounting on real generations: expected chunk count for the configured chunk_seconds/duration, per-chunk progress observed, and metadata distinguishing requested from stitched duration
- [ ] #3 Asserts stop-between-chunks: stopping after the first chunk completes ends the session promptly, without error and without submitting further chunks
- [ ] #4 Boundary continuity is measured on the stitched audio with documented thresholds (no silence gap, no click/discontinuity spike, no loudness jump above threshold) rather than by listening alone
- [ ] #5 Evidence (stitched wav, per-chunk timings, boundary metrics) is written under .uat/ and referenced from the task notes
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Reuse the TASK-2 live fixture; configure `chunk_seconds` small (e.g. 10) with a session duration that forces at least three chunks (30-40 s), keeping `inference_steps` low so total GPU time stays predictable.
2. Assert chunk accounting: expected `ceil(duration / chunk_seconds)` chunks, per-chunk progress/status transitions observed through the session manager, and metadata that separates requested duration from the stitched duration after crossfades.
3. Assert stop responsiveness between chunks: stop after the first chunk completes; assert the session ends promptly, raises nothing, and does not submit further chunks (assert on chunk counter/status, not wall-clock alone).
4. Analyse the stitched output with `audio/continuity.py` around each boundary window: assert no silence gap, no single-sample discontinuity/click above a documented threshold, and no RMS jump beyond a documented tolerance compared with mid-chunk windows.
5. Persist evidence (stitched wav, per-chunk timings, boundary metrics) under `.uat/ace-step-http/` and record the thresholds used.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:IMPLEMENTATION_NOTES:BEGIN -->

<!-- SECTION:IMPLEMENTATION_NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->

<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Live chunked test added and covered by the TASK-2 fixture gate
- [ ] #2 Default suite still passes with the new test skipped
- [ ] #3 At least one recorded live multi-chunk pass with evidence path in the task notes
- [ ] #4 Continuity thresholds and their justification documented in the test
<!-- DOD:END -->
