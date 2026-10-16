---
id: TASK-13
title: 'Quality feedback pipeline: AudioBox Aesthetics report drives next prompt'
status: Done
created_date: 2026-10-15 20:06
updated_date: 2026-10-15 20:23
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Closed-loop quality refinement: after each generation, analyze the output (AudioBox Aesthetics CE/CU/PC/PQ via configurable command + local MIR profile), store the report in session metadata, translate scores/metrics into prompt adjustments (bed strength, percussion sparsity, production polish, variant rotation), persist them as refinement state, and apply them to the next session's caption. Analyzer runs wherever audiobox_aesthetics is installed (local or the V100 host via ssh wrapper); default backend none keeps the app dependency-free.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:IMPLEMENTATION_NOTES:BEGIN -->
User documentation added: docs/quality-loop.md (linked from README) covering the loop concept, score meanings and thresholds, where reports live (metadata.json quality block, refinement.json), the listen.py deep-dive/A-B workflow, manual control (seeding/resetting adjustments, disabling the backend), and a troubleshooting table. The manual-seeding snippet in the guide was executed verbatim to verify it works, then the refinement state was reset.
<!-- SECTION:IMPLEMENTATION_NOTES:END -->
## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Closed-loop producer pipeline shipped and verified live. New src/lofi_focus_tui/quality.py: QualityScores/QualityReport models, numpy-only MIR measurements (dip_ratio p10/p90 of 100ms RMS, sustained fraction), producer rules mapping reports to prompt adjustments (low CE/CU/PQ -> content/focus/production phrases; deep dips -> dense pad bed; capped at 3, dip rule subsumes sustained rule), and AudioboxAnalyzer calling AudioBox Aesthetics' Python API in-process (lazy import, optional dep, excerpt configurable, never fails a session — no subprocess, per security-hook review). CompositionBlueprint gained quality_adjustments, consumed by compose_local_prompt as a sentence-level slot after the smoothness phrase — integrates with the TASK-12 tag composer as a sentence-level element outside the tag budget. SessionManager: applies the persisted refinement state (~/.cache/lofi-focus-tui/refinement.json) to each new session's blueprint, analyzes after playback starts, writes the report into the session metadata.json ("quality" block), updates refinement state, and surfaces "playing · quality PQ x.x" in the TUI. Config [quality] backend none|audiobox (default none keeps the app dependency-free); audiobox_aesthetics installed into the app venv (CPU: 6.7s load, 3.7s/track). Tests: test_quality.py + test_quality_pipeline.py cover MIR, rules, analyzer, persistence, next-prompt carry-through, caption inclusion; suite 372 passed, ruff clean. Live E2E on the V100 service: session 1 scored CE 7.9/CU 8.3/PQ 8.2 with dip_ratio 0.099 (vs 0.027 pre-smoothness baseline) and correctly suggested nothing; a seeded low-score state carried both adjustment phrases into session 2's blueprint/caption (verified in metadata + server-side caption log) and session 2 scored PQ 8.3. Next step per maintainer: use this harness to batch-measure presets/options and tune them (the TASK-12 catalogs provide the levers).
<!-- SECTION:FINAL_SUMMARY:END -->
## Definition of Done
<!-- DOD:BEGIN -->
<!-- DOD:END -->
