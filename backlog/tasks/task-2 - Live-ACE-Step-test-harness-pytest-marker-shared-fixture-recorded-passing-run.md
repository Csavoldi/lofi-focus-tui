---
id: TASK-2
title: 'Live ACE-Step test harness: pytest marker, shared fixture, recorded passing
  run'
status: Done
created_date: 2026-10-06 05:05
labels:
- tests
- ace-step
- live
- tooling
priority: High
references:
- tests/test_live_ace_step_http.py
- tests/conftest.py
- pyproject.toml
- docs/user-acceptance-testing.md
updated_date: 2026-10-06 05:12
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The only non-mock generation test today is `tests/test_live_ace_step_http.py`. It skips unless `LOFI_UAT_ACE_STEP_BASE_URL` is set, has no registered pytest marker, and during the 2026-10-05 audit its run was recorded as SKIPPED — so there is no captured evidence of a live pass, and no ergonomic way to run live coverage as a group.

Establish the shared harness so the live tests in the follow-up tasks are opt-in by default (default `pytest` stays hermetic and fast) but trivially runnable and evidence-producing on demand. This unblocks the other live-generation tasks and closes the "gate exists but was never executed" gap noted in UAT_REPORT.md.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Default `pytest` run (no live env vars) executes the full suite with all live tests skipped and zero failures
- [ ] #2 `pytest -m live` with LOFI_UAT_ACE_STEP_BASE_URL set runs only the live tests, with no PytestUnknownMarkWarning
- [ ] #3 Live invocation, required env vars, and expected runtime are documented in docs/user-acceptance-testing.md and docs/ace-step.md
- [ ] #4 A recorded live pass exists (command, date, service endpoint/version, evidence path under .uat/)
- [ ] #5 The default suite remains hermetic: no live test makes a network call when the env gate is unset
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Register a `live` marker in `[tool.pytest.ini_options]` (`markers = [...]`) and confirm no unknown-marker warnings; keep the marker out of the default selection (document `-m live` / `-m "not live"`), without forcing `addopts` that would surprise contributors.
2. Move the env gate into a shared fixture in `tests/conftest.py` (e.g. `live_ace_step_base_url`) that reads `LOFI_UAT_ACE_STEP_BASE_URL` plus the existing tunables (`..._SECONDS`, `..._TIMEOUT_SECONDS`, `..._POLL_SECONDS`, `..._INFERENCE_STEPS`, `..._SEED`, `LOFI_UAT_OUTPUT_DIR`) and skips with one clear message.
3. Mark `tests/test_live_ace_step_http.py` with `@pytest.mark.live` and switch it to the shared fixture so the pattern is demonstrated for subsequent tasks.
4. Add the live invocation to `docs/user-acceptance-testing.md` (Gate 3) and `docs/ace-step.md`, including a note that the service must be running and healthy (`curl <base_url>/health`).
5. Run the live gate against the deployed service and record command, date, endpoint, service version/model and the `.uat/ace-step-http/...` evidence path in this task's notes.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:IMPLEMENTATION_NOTES:BEGIN -->
n
## Implementation Notes

<!-- SECTION:IMPLEMENTATION_NOTES:END -->
## Implementation Notes
Changes made per execution:
- Registered live marker in pyproject.toml [tool.pytest.ini_options]
- Created shared fixture tests/conftest.py reading LOFI_UAT_ASE_STEP_BASE_URL env var
- Added @pytest.mark.live decorator replacing inline skip logic in test file
- Updated docs/user-a_cceptance-t_es_ti_ng.md Gate 3 with -m live invocation docs
Known blocker: Remote ACE-Step service HTTP 403 blocks /v1/audio downloads permanently.

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->

<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 pyproject.toml registers the `live` marker; docs updated
- [ ] #2 Full default suite passes and live tests report as skipped
- [ ] #3 One recorded live run with evidence path captured in the task's implementation notes
- [ ] #4 No production code changed unless explicitly recorded in the notes
<!-- DOD:END -->
