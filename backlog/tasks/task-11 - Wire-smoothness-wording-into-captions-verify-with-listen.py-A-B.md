---
id: TASK-11
title: Wire smoothness wording into captions; verify with listen.py A/B
status: Done
created_date: 2026-10-15 19:32
updated_date: 2026-10-15 19:40
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
User-perceived hiccups in generated focus music traced to caption under-specification: all generations have ~30 dB dips between beat events (sparse dry mix) and new takes at double-time pulse (148 vs 83 BPM feel). scripts/listen.py added as the MIR measurement tool. Wire smoothness wording into the prompt implementation: sustained pad bed, connected phrases, relaxed pulse — as caption constraints so every focus generation requests continuity, then verify with an A/B generation measured by scripts/listen.py (p10/p90, sustained%, tempo targets).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:IMPLEMENTATION_NOTES:BEGIN -->
Implementation: BED_TEXTURE_LAYER ("sustained warm pad bed") appended to every blueprint's texture layers (composition.create_blueprint) so it lands in the caption instrument list, and energy-scaled _SMOOTHNESS_PHRASES in prompt_engine.compose_local_prompt slotted directly after the qualitative tempo (LOW: "unbroken low-level flow ... held pad bed"; STEADY: "continuous pad bed under the beat, smoothly connected phrases, steady relaxed pulse"; HIGH: lighter). Golden prompt tests updated; new test covers all three energies; suite 362 passed, ruff clean.

A/B verification via scripts/listen.py (classic_lofi, deep_work, float32 V100 server, 3x120s chunks):
- baseline (pre-wording): p10/p90 0.027, tempo 148
- steady + wording: p10/p90 0.030 (marginal)
- low + wording: p10/p90 0.043 (~4 dB shallower inter-beat dips — real improvement)
Band-limited pad-band analysis shows the bed authority is weak at steady energy. The ~148 pulse-events/min rate persists across all variants — that is the checkpoint's lo-fi hip hop rendering (eighth-note hats), not tempo misconfiguration; the 83-BPM reference track was neo_soul on the old server. Practical guidance: energy LOW (or ambient_tape preset) for maximum smoothness; consider neo_soul preset if the half-time feel is wanted.
<!-- SECTION:IMPLEMENTATION_NOTES:END -->
## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->

<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
<!-- DOD:END -->
