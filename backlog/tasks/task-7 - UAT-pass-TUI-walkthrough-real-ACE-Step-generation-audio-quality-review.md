---
id: TASK-7
title: 'UAT pass: TUI walkthrough + real ACE-Step generation + audio quality review'
status: Done
created_date: 2026-10-15 15:17
updated_date: 2026-10-15 15:55
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Interactive UAT pass against the real ACE-Step-1.5 service now running as the Gradio UI at http://192.168.2.220:7860. Covers: TUI click-through with screen capture, real audio generation, audio quality analysis (metrics + spectrogram), export/playback/doctor checks, error UX, and a findings report.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:IMPLEMENTATION_NOTES:BEGIN -->
UAT executed 2026-10-15 against the running ACE-Step-1.5 Gradio service at 192.168.2.220:7860.

Method: REST-to-Gradio bridge (/tmp/uat_bridge.py on 127.0.0.1:8001) because the acestep-api REST wrapper (8001) is down and the app only speaks that protocol. App under test unchanged. TUI driven by keys in tmux with screen captures; audio assessed via LUFS/peak/LRA, band-energy timelines, click/clipping scans, and spectrogram image review.

Verified working: option cycling + guide + prompt/vocal toggles; real 5-min generation (~130s) and playback (pause/resume/volume/seek/restart/stop/quit); export writes audio.wav + complete metadata.json; chunked generation (2x150s) with visible chunk progress and 299.0s stitched actual vs 300 requested; error state + recovery without app restart (twice, after real remote failures); lofi-doctor clean; baseline pytest and live HTTP gate passed.

Findings recorded in UAT-FINDINGS-2026-10-15.md: P1 app incompatible with the actually-running Gradio deployment; P1 remote 600s VRAM stall on 300s chunks crashes session ~10min in with flat 50% progress and raw ReadError surfaced; P2 mono output (stereo via old REST service); P2 audible chunk seams (5-6s energy dip, both chunks fade at boundaries); P3 flat 50% happy-path progress, export modal Enter-hint missing, controls line omits keys, config drift 27/15 vs recommended 8/7.

Config left at: backend ace-step-http, base_url http://127.0.0.1:8001 (bridge, still running for retests), inference_steps 8, guidance_scale 7.0, chunk_seconds 600.
<!-- SECTION:IMPLEMENTATION_NOTES:END -->
## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Interactive UAT pass completed with real ACE-Step-1.5 generation (Gradio service at 7860 reached via a local REST-to-Gradio bridge because the acestep-api wrapper is down). All gates exercised; happy path (generation, playback, export, chunking, error recovery) works. 8 findings recorded with severities in UAT-FINDINGS-2026-10-15.md — headline: the app cannot talk to the currently-deployed Gradio service directly, and remote long-chunk VRAM stalls surface as a flat 50% wait ending in a raw ReadError. Audio quality: clean, focus-appropriate lofi (−21 LUFS, no clipping, coherent spectrograms); mono output and audible chunk-seam dips are the quality regressions to address.
<!-- SECTION:FINAL_SUMMARY:END -->
## Definition of Done
<!-- DOD:BEGIN -->
<!-- DOD:END -->
