---
id: TASK-1
title: 'Update UAT report: ACE-Step audio-download 403 resolved'
status: Done
created_date: 2026-10-06 04:56
labels:
- docs
- uat
- ace-step
updated_date: 2026-10-06 04:57
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
UAT_REPORT.md is dated 2026-10-05 and still records the `/v1/audio` HTTP 403 as the "critical production blocker" for live ACE-Step generation against http://192.168.2.220:8001.

That blocker is now resolved and verified end-to-end, so the report is stale and misleading: it tells a reader that live generation cannot work, and its "Repair Solutions Required" section proposes adding a client-side cache dir to an ACE-Step "allowed-paths configuration" that does not exist.

Verified facts to fold into the report:
- ACE-Step's REST `/v1/audio` route has no allowlist. It serves only files under `app.state.temp_audio_dir`, which is `$ACESTEP_TMPDIR/api_audio` (default `<repo>/.cache/acestep/tmp/api_audio`).
- The HTPC service was simply not running at the time of the follow-up; it was restarted, and `C:\Users\Clem\ACE-Step-1.5\.env` was created pinning `ACESTEP_TMPDIR=C:\Users\Clem\ACE-Step-1.5\.cache\acestep\tmp` so the served dir is explicit and cwd-independent.
- Live re-test: task `cea2021e-3a39-4479-a88a-8689e21bb253` succeeded, returned `C:\Users\Clem\ACE-Step-1.5\.cache\acestep\tmp\api_audio\73e7d3b0-45f3-fa9a-c1de-8e5a57348f32.wav`, and `GET /v1/audio?path=...` returned HTTP 200, 3,072,088 bytes, 8.00 s, 48 kHz stereo, mean -22.7 dB / peak -1.0 dB.
- ACL guards still hold: inside the pinned dir -> 404 (allowed, file missing); `/cache/acestep/tmp/api_audio/...` -> 403; outside dir -> 403.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 UAT_REPORT.md contains no remaining statement that the /v1/audio 403 is an open blocker
- [x] #2 The resolution entry names the actual mechanism (temp_audio_dir = $ACESTEP_TMPDIR/api_audio, no allowlist) and the config change applied on the HTPC
- [x] #3 Verification evidence in the report matches the observed run (task id, path, HTTP 200, byte count, duration, levels)
- [x] #4 Original pre-fix findings remain traceable as historical context rather than being silently deleted
- [x] #5 ACL boundary behaviour (403 outside / 404 inside) is documented so the guard is not misread as removed
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add a dated resolution banner near the top and correct the Executive Summary row + Overall Verdict.
2. Convert the two `[FAIL]` audio-download entries (Section 1 and Section 2) to `[RESOLVED]`, keeping the original failure text as historical pre-fix context.
3. Rewrite the "CRITICAL: Audio Download 403 Blocker" section as resolved: corrected root cause, the actual fix (.env pin on the HTPC), and the verification evidence, replacing the inapplicable allowed-paths solution table.
4. Fix the trailing duplicate section (lines ~176-177) and the Section 6 closing claim that the ACL still blocks the download.
5. Re-read the edited file and grep for stale blocker wording to confirm no contradictions.
6. Record notes/verification on this task, check AC/DoD, move to Done with a final summary.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:IMPLEMENTATION_NOTES:BEGIN -->
**Implementation notes (2026-10-05)**

- **Decision:** preserve the original pre-fix findings as historical context instead of rewriting them, and annotate the document: dated status banner at the top, `[RESOLVED]`/`[PASS]` markers on the two audio-download entries, and one authoritative remediation section ("Audio Download 403 Blocker — RESOLVED").
- **Correction recorded:** ACE-Step's REST `/v1/audio` route has no allowlist and no "allowed directories" config. It serves only files inside `app.state.temp_audio_dir = $ACESTEP_TMPDIR/api_audio`, and the path in the returned URL is the *server's* absolute path — so the original "add the client cache dir to the server's allowed-paths config" option (A) was inapplicable, as were options B–D. No application code change was needed.
- **Server-side change referenced (remote host, not part of this repo):** created `C:\Users\Clem\ACE-Step-1.5\.env` with `ACESTEP_TMPDIR=C:\Users\Clem\ACE-Step-1.5\.cache\acestep\tmp` (file was absent; git-ignored so it survives updates), restarted the stopped REST service, and re-verified end-to-end.
- **Honest caveat kept in the report:** the pinned directory equals the previous default, so the functional fix was restarting the stopped service; the `.env` pin makes the served directory deterministic. ACL boundary rows (403 outside / 404 inside) are retained so the guard is not misread as removed.
- **Structural fix:** added missing blank lines before three headings that were glued to preceding list items/paragraphs, so they render as headings.
- **Changed files:** `UAT_REPORT.md` (currently untracked in git — no commit was made).
- **Remaining open item in the report:** MODERATE local PyTorch/CUDA CC 7.0 note only.
<!-- SECTION:IMPLEMENTATION_NOTES:END -->
## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
UAT_REPORT.md no longer reports the ACE-Step `/v1/audio` HTTP 403 as an open blocker. The Executive Summary row and Overall Verdict now record the resolved state; the two pre-fix `[FAIL]` entries became `[RESOLVED]` / `[PASS]` with the original failure text retained as historical context; and the former "CRITICAL: Audio Download 403 Blocker" remediation section was replaced by "Audio Download 403 Blocker — RESOLVED", which documents the corrected root cause (no allowlist; `temp_audio_dir = $ACESTEP_TMPDIR/api_audio`; the URL carries the server's path), the `.env` pin and service restart applied on the HTPC, the verification evidence (task `cea2021e-3a39-4479-a88a-8689e21bb253`, `GET /v1/audio` → HTTP 200, 3,072,088 bytes, 8.00 s, mean -22.7 dB / peak -1.0 dB), the retained ACL boundary behaviour (403 outside / 404 inside), the superseded A–D options, and operational notes (service does not survive reboot; `ACESTEP_API_KEY` unset). Verification: grep for stale blocker wording returns no matches, markdown fences/tables are balanced, and the trailing duplicate section's stale 403 claim was corrected. The only outstanding item left in the report is the pre-existing MODERATE local PyTorch/CUDA CC 7.0 note.
<!-- SECTION:FINAL_SUMMARY:END -->
## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 UAT_REPORT.md edited and re-read for consistency
- [x] #2 No stale 'FAIL'/'blocker' claims about audio download remain (grep verified)
- [x] #3 Report states the honest caveat that the pinned dir equals the previous default, so the real fix was restarting the stopped service
- [x] #4 Task notes list changed files and the verification commands
<!-- DOD:END -->

## Run History
<!-- SECTION:RUN_HISTORY:BEGIN -->
<!-- RUN_HISTORY_ENTRY:BEGIN -->
```yaml
event_id: run-d1ca8c8fb0554cba99e4b95a9b79ea07
type: record_run
actor: dsh-agent
timestamp: '2026-10-06T04:57:29.244326Z'
result: succeeded
task_id: TASK-1
files:
- UAT_REPORT.md
verification:
- grep -nE 'FAIL|critical production blocker|WARNING|allowed-paths|only failure|blocks
  the download|will raise' UAT_REPORT.md -> no matches
- 'python3 sanity: code fences balanced (12), no malformed table rows, 27 headings'
- 'live re-test 2026-10-05: GET /health -> models_initialized:true; release_task cea2021e-3a39-4479-a88a-8689e21bb253
  -> succeeded; GET /v1/audio?path=... -> HTTP 200, 3072088 bytes, 8.00 s, 48 kHz
  stereo'
- 'ACL boundary probes: inside pinned dir -> 404 (allowed), /cache/acestep/tmp/api_audio/probe.wav
  -> 403, outside dir -> 403'
```
Rewrote UAT_REPORT.md's ACE-Step audio-download findings from an open 403 blocker to a resolved, evidence-backed state; corrected the root cause (no allowlist; temp_audio_dir = $ACESTEP_TMPDIR/api_audio; server-side path) and documented the .env pin + restart on the HTPC with the HTTP 200 re-test evidence.
<!-- RUN_HISTORY_ENTRY:END -->
<!-- SECTION:RUN_HISTORY:END -->
