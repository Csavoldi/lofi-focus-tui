---
id: TASK-14
title: 'Auto prompt refiner: iterate takes to quality targets without user work'
status: Done
created_date: 2026-10-15 20:52
updated_date: 2026-10-15 21:14
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Convert the quality loop into an automatic prompt-refinement product: a PromptRefiner (accept/reject policy on CE/CU/PQ + envelope metrics; escalating adjustment phrases; seed rotation) drives the session manager to regenerate takes before the user hears them, keeping the best attempt (config: [quality] auto_refine, max_refinement_attempts). An offline scripts/tune_prompts.py uses the same engine against the live backend to explore prompt variants per preset/energy and report the best-performing captions, so preset/option defaults get tuned without user effort. User guide updated.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:IMPLEMENTATION_NOTES:BEGIN -->
Manual-test follow-up: the user's first manual session (boom_bap, 14:07) recorded null scores — the analyzer had swallowed its exception silently. Reproduced the user's exact launch path (home dir, user config, venv): works (playing · quality PQ 8.0, metadata PQ 7.95, no analyzer_error). Likely cause of their null run: overlap with the concurrent scripted verification runs (checkpoint cache contention) or the mid-development code state at that timestamp. Hardened: AudioboxAnalyzer.last_error now captures the failure reason and is written into metadata quality.analyzer_error for diagnosability; also fixed the PQ status update zeroing the chunk counters. Suite 380 passed, ruff clean.
<!-- SECTION:IMPLEMENTATION_NOTES:END -->
## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Auto prompt refiner shipped, tested, and verified live. New generation/refiner.py: RefinementPolicy (accept/reject on CE/CU/PQ minimums + dip floor; rank() for best-take selection) and PromptRefiner (base phrases on first failure, escalated wording when the same aspect fails again, phrases dropped when their aspect recovers, capped at 3, deterministic seed rotation). SessionManager now runs generate -> score -> (reject? regenerate with adjusted prompt + fresh seed) -> deliver the best take before playback; status shows "refining take 2/2 · last PQ x.x"; every attempt's seed/adjustments/report recorded in metadata quality.refinement; the post-commit report reuses the refinement analysis (no double scoring). Policy thresholds now thread into suggestion generation (strict policies produce proportionally strict asks — gap found and fixed during live verification). Config: [quality] auto_refine (default true) + max_refinement_attempts (default 2, max 4). scripts/tune_prompts.py: offline prompt tuner against the live backend, ranked takes per preset/energy with winning adjustments, results appended to .uat/prompt-tuning/results.jsonl. Tests: test_refiner.py + three pipeline integration tests (retry path, keep-best-on-all-weak, disabled-without-analyzer); suite 380 passed, ruff clean. Live evidence: forced 9.9-bar session rejected take 1 (PQ 8.23), regenerated with all three adjustment phrases + rotated seed (take 2 PQ 8.27) and delivered the better take with full audit trail; tuner run on classic_lofi/low accepted take 1 (CE 7.93/CU 8.01/PQ 8.01, dip 0.101). docs/quality-loop.md and config.example.toml updated for the automatic behavior.
<!-- SECTION:FINAL_SUMMARY:END -->
## Definition of Done
<!-- DOD:BEGIN -->
<!-- DOD:END -->
