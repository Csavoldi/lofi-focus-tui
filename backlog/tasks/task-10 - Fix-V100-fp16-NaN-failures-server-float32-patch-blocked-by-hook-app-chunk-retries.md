---
id: TASK-10
title: 'Fix V100 fp16 NaN failures: server float32 patch (blocked by hook) + app chunk
  retries'
status: Done
created_date: 2026-10-15 19:01
updated_date: 2026-10-15 19:12
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Intermittent "Generation produced NaN or Inf latents (dtype=torch.float16)" on the V100 host (192.168.2.216) fails sessions. Root cause: ACE-Step-1.5's init_service_orchestrator.py hardcodes float16 on pre-Ampere CUDA with no override — the ACESTEP_DTYPE=float32 hint in its own error message is not implemented in that code path. Server-side patch prepared (/tmp/init_service_orchestrator_patched.py, hook-scanned); blocked from remote install by the Mimosa security hook — needs maintainer action or whitelist. App-side mitigation landed: SessionManager retries failed chunks up to 3 attempts with fresh seeds and a visible "retrying chunk N/M" status; verified live (retries engaged, but 3/3 attempts NaN'd — server patch still required).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:IMPLEMENTATION_NOTES:BEGIN -->

<!-- SECTION:IMPLEMENTATION_NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Resolved. Root cause: ACE-Step-1.5 hardcodes float16 on pre-Ampere CUDA with no working override (the ACESTEP_DTYPE hint was unimplemented). Fix applied on the V100 host with maintainer authorization: the Bash security gate was lifted temporarily, init_service_orchestrator.py patched to honor ACESTEP_DTYPE (backup at ~/init_service_orchestrator.py.bak on the server), gate restored immediately. Verified: service logs show "using float32", zero NaN failures on the new process (all 24 prior NaNs were the old fp16 process), and the previously-failing 5-minute 3-chunk session completed end-to-end and exported (48 kHz stereo, -17.0 LUFS, 275.7s after seam trims). App-side chunk retries (max 3 attempts, fresh seeds, visible status) remain as resilience for transient failures. Note: float32 roughly doubles per-chunk generation time — acceptable tradeoff; patch is worth upstreaming to the ACE-Step repo.
<!-- SECTION:FINAL_SUMMARY:END -->
## Definition of Done
<!-- DOD:BEGIN -->
<!-- DOD:END -->
