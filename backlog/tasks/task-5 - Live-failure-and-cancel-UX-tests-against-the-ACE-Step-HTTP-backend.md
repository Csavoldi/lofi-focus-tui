---
id: TASK-5
title: Live failure and cancel UX tests against the ACE-Step HTTP backend
status: To Do
created_date: 2026-10-06 05:05
dependencies:
- TASK-2
labels:
- tests
- ace-step
- live
- error-ux
priority: Medium
references:
- tests/test_http_ace_step.py
- src/lofi_focus_tui/generation/http_ace_step.py
- src/lofi_focus_tui/backend/session_manager.py
- docs/user-acceptance-testing.md
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Gate 5 in `docs/user-acceptance-testing.md` ("Error UX") is a manual checklist, and the error/cancel paths of `AceStepHttpAdapter` and `SessionManager` are only covered with mocks. Real failure modes behave differently: connection refused vs 4xx vs a task that never finishes, and cancellation must actually interrupt live polling.

UAT_REPORT.md's Gate 5 expectation is that the backend enters `error`, the TUI shows an understandable message, and the app can start a new valid session afterwards without restarting. Add live, non-mock tests for those behaviours.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Unreachable-endpoint scenario: health check fails, the session enters `error` with a readable message, and a subsequent valid live session completes without restarting the process
- [ ] #2 Auth/HTTP-error scenario (env-gated on a keyed service): a wrong API key produces an error state carrying the HTTP status/detail and no hang
- [ ] #3 Cancel scenario: cancelling a real submission returns promptly, leaves the session stopped/cancelled, and a new session starts successfully afterwards
- [ ] #4 Timeout scenario: a deliberately impossible deadline surfaces a timeout as the error state within a documented bound rather than hanging
- [ ] #5 All scenarios are marked `live` and skip cleanly when the env gate is unset, leaving the default suite hermetic
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Unreachable endpoint: point `base_url` at a closed port on the service host; assert `health()` is false, the session transitions to `error` with a non-empty readable message, and a following session against the real service succeeds in the same process.
2. Auth/HTTP error: env-gated scenario for a service started with `ACESTEP_API_KEY` set — use a wrong key and assert the error state carries the HTTP status/detail (document the required service setup in the test docstring or skip message).
3. Cancel: start a real generation, cancel shortly after submission (before completion), assert the call returns promptly, the session is stopped/cancelled rather than error, no completion/download is attempted afterwards, and a new session can start.
4. Timeout: configure `timeout_seconds` far below the achievable generation time (small deadline, low steps/duration tuned so the deadline cannot be met) and assert the timeout surfaces as the error state within a documented bound.
5. Record per-scenario observed status and message; keep every scenario behind the TASK-2 live fixture so the default suite makes no network calls.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:IMPLEMENTATION_NOTES:BEGIN -->

<!-- SECTION:IMPLEMENTATION_NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->

<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Live failure/cancel tests added under tests/
- [ ] #2 Each scenario has a recorded observed status/message in the task notes (or an explicit reason it was env-gated and not run)
- [ ] #3 Default suite still passes with the new tests skipped
- [ ] #4 Any adapter/session change needed is recorded as a finding with rationale
<!-- DOD:END -->
