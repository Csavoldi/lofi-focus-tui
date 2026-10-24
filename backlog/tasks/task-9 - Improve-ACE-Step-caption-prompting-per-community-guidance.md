---
id: TASK-9
title: Improve ACE-Step caption prompting per community guidance
status: Done
created_date: 2026-10-15 16:58
updated_date: 2026-10-15 17:52
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Community guidance (r/LocalLLaMA ACE-Step 1.5 prompt tips, r/StableDiffusion ACE-Step 1.5 Architect system prompt, Comfy-Org HF tutorial) converges on: genre tags first and explicit; lead instruments named specifically; qualitative tempo in caption with BPM as metadata only; structure-tag-only lyrics for instrumentals with max one hyphenated modifier; short duration generations (90-120s) with batch-and-cherry-pick selection. Current engine misses the preset's genre name entirely (jazz_vinyl captions never say "jazz"), has no qualitative tempo slot, and orders the user prompt before the style stack.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ["Caption names the preset's genre (e.g. jazz_vinyl says \"jazz, vinyl\"), not just \"instrumental lo-fi\"", "Caption follows community-validated slot order: genre/style, lead instruments, qualitative tempo, vibe, arrangement", "Qualitative tempo descriptor derived from tempo range appears in captions; BPM stays metadata-only", "Key metadata uses full name capitalization (\"A Minor\")", "Unit tests updated and passing (test_prompt_engine, test_composition, test_options, test_presets)", "docs/ace-step.md prompting section reflects the new caption structure"]
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Add genre_tags to PresetOption for all 9 presets; thread through SessionPlan/CompositionBlueprint; reorder compose_local_prompt slots (genre stack first, user wording appended); add bpm-derived qualitative tempo phrase; capitalize key alias "A Minor"; update tests and docs.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:IMPLEMENTATION_NOTES:BEGIN -->
- options.py: added required PresetOption.genre_tags; all 9 presets now name their genre ("jazz, vinyl", "boom bap hip hop", ...) — previously jazz_vinyl captions never said "jazz", only the generic "instrumental lo-fi" umbrella.
- domain.py: CompositionBlueprint.genre_tags: str = "" (defaults keep stored payloads valid); composition.py threads preset.genre_tags into the blueprint.
- prompt_engine.py: compose_local_prompt reordered to community slot order (genre tags -> instruments -> qualitative tempo -> user wording/vibe -> focus -> section -> continuity); added _qualitative_tempo bpm bands (<80 slow, <100 easy mid-tempo, <120 steady up-tempo, else driving); key alias "A minor" -> "A Minor".
- Instrumental lyrics already conformed (structure tags only, single hyphenated modifier) — no change needed.
- Sources: r/LocalLLaMA 1r0904z (structured tags, short phrases), r/StableDiffusion 1r2vajw (ACE-Step 1.5 Architect system prompt: slot order, no BPM in caption, full key names, instrumental=structure-tags-only), Comfy-Org HF tutorial via r/comfyui 1l667xm (qualitative tempo, low-CFG/high-steps recipe, batch-and-cherry-pick, 90-120s duration sweet spot). r/StableDiffusion 1siju9k had no answers (question only).
Post-completion live findings on the V100 ACE-Step-1.5 deployment (2026-10-15): (1) /format_input LM enrichment is broken server-side ('SamplingParams' object has no attribute 'update') — the adapter silently falls back to the local caption, so enrichment is dead code on this service. (2) The service forces guidance_scale 7.0 -> 1.0 on turbo (no CFG) — caption adherence is inherently weak on turbo. (3) Multi-tag structured lyrics (e.g. '[Intro - mellow]\n[Main Theme - steady]') intermittently produce 'NaN or Inf latents' failures in the fp16 DiT on Volta; single-tag lyrics per chunk ('[Intro - steady]') are reliable. Config switched to chunk_seconds=120 so sessions get an Intro/Main/Outro arc through per-chunk tags. A/B listening files for old-vs-new caption at seed 4242 are under ~/Music/lofi-focus-tui/prompt-review/ab/.
V100 service remediation (2026-10-15, user-authorized): stopped huihui36b llama-server to free VRAM; downloaded acestep-v15-base; service unit now sets ACESTEP_CONFIG_PATH=acestep-v15-base and ACESTEP_LM_BACKEND=pt — the pt backend fixes the 'SamplingParams has no update' crash, so /format_input LM enrichment works again (verified: returns fluent rewritten captions). Base runs with live CFG (no guidance override; 32 steps @ guidance 4.0 per community recipe). Multi-tag structure lyrics ([Intro]/[Main Theme]/[Outro]) succeed on base — the NaN-latents failure was turbo-specific. Local config moved to steps=32/guidance=4.0/chunk_seconds=120. Review track with new prompt (classic_lofi, 'rainy midnight walk through neon city streets', seed 777) shows an actual dynamic arc (5s-window RMS 0.008 intro -> 0.193 body) unlike the flat ~0.15 profile of the turbo meander tracks.
User listening verdict (2026-10-15): the base+CFG+structure remediation track is 'way better' — the meandering complaint is resolved by guidance actually functioning (base checkpoint), structure lyrics providing an arrangement arc, and shorter chunks. Turbo-era A/B tracks (identical-sounding) confirmed caption wording was never the lever.
<!-- SECTION:IMPLEMENTATION_NOTES:END -->
## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Captions now follow the community-validated ACE-Step 1.5 slot order and name each preset's genre explicitly, add a bpm-derived qualitative tempo phrase, and emit the key as "A Minor". Verified by the full unit suite (358 passed) plus a live 10s generation against ACE-Step 1.5 on the V100 host (test_live_ace_step_http PASSED in 18s warm; evidence under .uat/ace-step-http/20261015T170618Z_ace_step_15_http_uat). Follow-ups not in scope here: base/sft checkpoint benchmark with the low-CFG/high-steps recipe (cfg 4, steps up to 65, er_sde/linear_quadratic), best-of-N batch selection, and shorter chunk durations (90-120s sweet spot per the HF tutorial vs current 300s default).
<!-- SECTION:FINAL_SUMMARY:END -->
## Definition of Done
<!-- DOD:BEGIN -->
<!-- DOD:END -->
