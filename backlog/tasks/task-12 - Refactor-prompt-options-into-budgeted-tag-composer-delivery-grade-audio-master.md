---
id: TASK-12
title: Refactor prompt options into budgeted tag composer + delivery-grade audio master
status: In Progress
created_date: 2026-10-15 19:56
updated_date: 2026-10-15 20:02
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Refactor user-selectable generation options into expanded cyclers (texture catalog + preset variant pins for keys/drums/bass, all defaulting to auto) feeding a new budgeted tag composer (≤12-tag caption with priority drops and conflict rules), upgrade the generation request per official ACE-Step-1.5 API.md (wav32 lossless source, thinking=true for all sessions, inference_steps 8→20 on turbo, model passthrough, doctor range updates), and add a delivery-grade master chain (true stereo preservation, equal-power crossfades, −14 LUFS / −1 dBTP, 24-bit TPDF-dithered WAV). Design doc: docs/superpowers/specs/2026-10-15-prompt-options-and-audio-quality-design.md.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:IMPLEMENTATION_NOTES:BEGIN -->
Spec review: dispatched spec-document-reviewer subagent; status Approved with 4 minor corrections + 1 advisory, all folded into the spec and committed (cb106d2 + amendment). Corrections: (1) smoothness phrase listed as sentence slot 6; (2) pins thread through SessionPlan/expand_preset, integration table updated; (3) user style pick deduplicated between genre-modifier and texture_layers slots; (4) 2-D audio shape standardized at adapter boundary incl. MockModelAdapter; advisory: playback gain-only path gets a −1 dBFS safety clip.
<!-- SECTION:IMPLEMENTATION_NOTES:END -->
## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->

<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
<!-- DOD:END -->
