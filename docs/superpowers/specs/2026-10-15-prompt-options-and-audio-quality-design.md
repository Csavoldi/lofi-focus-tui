# Design: Prompt Options Refactor + Delivery-Grade Audio Quality

- **Date:** 2026-10-15
- **Status:** Approved design (Sections 1, 3, 4 user-approved; Section 2 unopposed — derived from official API.md and the "raise fixed defaults" decision, flagged for owner sign-off at review). Spec-document review: Approved; reviewer's four minor corrections folded in (smoothness-phrase slot, SessionPlan pin threading, style-pick deduplication between slots 1/3, in-process 2-D producers) plus the playback clip-guard note.
- **Backlog task:** TASK-12
- **Sources:** ACE-Step-1.5 official `docs/en/Tutorial.md`, `docs/en/ace_step_musicians_guide.md`, `docs/en/API.md`; deapi.ai prompting guide; AmbienceAI tutorial; ComfyUI ACE-Step 1.5 docs; dev.to 2026 guide; HN/r/LocalLLaMA prompt-tips thread; r/StableDiffusion "Suno 4.5 killer" settings thread; Zenn "Retake" article. Repo UAT findings (2026-10-15) and `scripts/listen.py` measurement harness.

## Goal

Make the user-tunable generation options both broader and safer, and make the saved output indistinguishable from a produced lofi upload on YouTube: full-frequency, true-stereo, 24-bit, streaming-loudness audio with clean seams, generated from polish-tier settings.

Non-goals: tonal coloring (EQ/saturation "character" chain), a separate Studio screen, repaint/cover workflows, best-of-N batch selection. These are recorded under Future Work.

## Decisions (user-resolved forks)

| Fork | Decision |
|---|---|
| Options UI shape | **Expanded cyclers only** — stay single-screen; add cyclers; no new screens |
| Tag integration mechanic | **Budgeted tag composer** — engine assembles captions under a tag budget with conflict rules |
| Audio quality depth | **Delivery-grade master** — loudness/stereo/format/crossfade; no coloration |
| Generation quality trade-off | **Raise fixed defaults** — polish tier for everyone; config-only overrides |

## Section 1 — Options model & budgeted tag composer

### 1.1 New cyclers (TUI)

Home screen keeps the single-pane layout; the session summary pane renders three labeled groups so the extra lines stay scannable:

```
  vibe ─────────────────────────
  focus:      deep work         [1]
  preset:     classic lofi      [p]
  style:      lofi, neo soul    [4]
  texture:    vinyl crackle     [8]   ← new catalog
  arrangement ──────────────────
  keys:       auto              [5]   ← preset variant pool
  drums:      auto              [6]   ← preset variant pool
  bass:       auto              [7]   ← preset variant pool
  session ─────────────────────
  duration:   30 min            [2]
  energy:     steady            [3]
```

- Keys `5`/`6`/`7`/`8` are free (current bindings: `1 2 3 4 p t i v s space x r e h`).
- **Keys/drums/bass** cycle the *active preset's* existing variant pools (`PresetVariant.motif` / `drum_feel` / `bass_behavior`, 10 each), prefixed with `auto`. Changing preset resets pins that don't exist in the new preset's pool (fall back to `auto`).
- **Texture** cycles a new global catalog (Section 1.2). Each preset declares a `default_texture`; the cycler starts there.
- `OptionGuideScreen` gains entries for all four cyclers.

### 1.2 New catalogs (`options.py`)

- `TEXTURE_OPTIONS` (~6, ids + caption phrases): `clean`, `vinyl_crackle` ("vinyl crackle"), `tape_saturation` ("tape saturation"), `warm_analog` ("warm analog character"), `cassette` ("soft cassette fuzz"), `room_air` ("gentle room air"). One selection at a time — production texture is a single dimension, not a multi-select.
- Each `PRESET_OPTIONS[preset]` gains `default_texture` (e.g. `classic_lofi → vinyl_crackle`, `ambient_tape → tape_saturation`, `synthwave → clean`).

### 1.3 Domain & composition changes

- `SessionRequest` (`domain.py`) gains `keys_choice: str | None = None`, `drums_choice`, `bass_choice` (None = auto), `texture: str | None = None` (None = preset default).
- The pins thread through `SessionPlan` and `expand_preset` (`presets.py`) the same way `style_tags → plan.style_traits` flows today — `SessionRequest → SessionPlan → blueprint` — before reaching `create_blueprint`.
- `create_blueprint` (`composition.py`): when a pin is set, validate it against the active preset's variant pool and use it instead of the seed pick; invalid pin → fall back to auto (and record a warning in the session metadata). Texture resolves to the effective value (request → preset default → `clean`) and is added to the blueprint.
- Blueprints stay deterministic for a given (preset, duration, style, seed, pins) — the deterministic-seed tests extend naturally.

### 1.4 Budgeted tag composer (`generation/tag_composer.py`, new)

Owns caption assembly; `prompt_engine.py` retains lyrics, metadata mapping, `/format_input` enrichment merge, and the 1024-char cap, and delegates to the composer.

**Slots, in the already-validated order:**

1. Genre block — preset's primary genre + **at most one modifier**: the user's `style_tags` pick replaces the preset's built-in modifier when set (never stacks two modifiers). Once the style pick occupies the genre-modifier slot it is **removed from `texture_layers`/slot 3**, where it flows today — no tag appears in both slots.
2. Mood/instrumental phrase — `"<mood> instrumental lo-fi"` as today.
3. Instruments — pinned (or seed-picked) motif + drum_feel + bass_behavior + texture layers (incl. the pad bed).
4. Production — effective texture phrase (Section 1.2).
5. Qualitative tempo — unchanged `_qualitative_tempo` (numeric BPM stays metadata-only, per official Tutorial).
6. Energy-scaled smoothness phrase — unchanged `_SMOOTHNESS_PHRASES` sentence (the measured anti-"~30 dB dip" fix); sentence-level, outside the tag budget.
7. User free-form prompt (unchanged, passes `prompt_safety`).
8. Focus phrase + section phrase (unchanged).
9. Continuity constraints, positively rewritten (unchanged).

**Budget rule:** slots 1–5 form the comma-tag block, capped at **12 substantive tags**. Overflow drops by priority (lowest first): extra mood adjectives → auxiliary descriptors → production texture → non-pinned instrument descriptors. Never dropped: primary genre, vocal-mode phrase, pinned instruments, qualitative tempo. Sentences (slots 6–9) are outside the tag budget.

**Conflict rules:** primary genre is mandatory and always the preset's own; one modifier max (1.4 rule above); pinned vocabulary is preset-scoped so pins cannot contradict the genre; contradictory free-text remains the job of `prompt_safety`.

### 1.5 UI state persistence

- New `UiStateStore` writing `~/.cache/lofi-focus-tui/ui_state.json` (atomic temp-file + `os.replace`, mirroring `HistoryStore`). Persists focus/preset/style/texture/keys/drums/bass/duration/energy/vocal-mode; loaded at startup; theme continues to come from config.

## Section 2 — Generation request (per official API.md) — *flagged: skipped approval, derived from docs*

- `audio_format`: `"wav"` → **`"wav32"`** (float32 WAV; server-side lossless transport). Decoupled from the local output format, which stays WAV and is mastered locally. Config override `audio_request_format` for older servers.
- `thinking`: **true for all sessions** (documented best-quality path — 5 Hz LM audio codes). Currently vocals-only. Config `enable_thinking = true` default; `lofi-doctor` reports when thinking is disabled. Latency impact documented in `docs/ace-step.md`.
- `inference_steps` default **8 → 20** (top of turbo's documented 1–20 range; community polish tier). `guidance_scale` stays 7.0 (documented base-only; harmless on turbo).
- `GenerationConfig` gains `model: str | None = None`, sent as `model` when set (e.g. base checkpoint users running 32–64 steps).
- `lofi-doctor` thresholds updated to documented ranges: turbo → warn outside 1–20; base/sft models → warn below 32; guidance warn above 10 (base-only note).

## Section 3 — Delivery-grade audio master

New `audio/master.py`; float32 in memory end-to-end; applied to the stitched session at save time.

```
server wav32 (48 kHz float)
  → decode preserving channels (see 3.1)
  → edge trim (existing) + equal-power crossfade (replaces linear)
  → measure integrated LUFS (BS.1770-4 K-weighting, numpy biquads)
  → linear gain to target −14 LUFS (config master.target_lufs)
  → true-peak limiter at −1 dBTP (4× oversampled, 5 ms lookahead, soft knee)
  → 24-bit PCM WAV + TPDF dither (soundfile PCM_24)
```

### 3.1 True stereo

- `read_wav_bytes` (`audio/wav.py`) stops averaging to mono: returns 2-D `(samples, channels)` float arrays (mono = `(n, 1)`). The 2-D shape is standardized at the **generation-adapter boundary** so in-process producers conform too — `MockModelAdapter` (`generation/mock.py`) and the embedded adapter emit `(n, 1)` — and the whole pipeline (`normalization.py`, `continuity.py`, `session_manager.py`, `playback.py`, `player.py`) handles 2-D only.
- `ensure_stereo` upmixes only genuine mono (duplicated channels), never collapses.

### 3.2 Crossfade

- `crossfade` switches from linear to **equal-power** (cos/sin) slopes, same 2.0 s default — removes the −3 dB loudness dip at chunk seams. `analyze_boundary` unchanged.

### 3.3 Mastering

- `measure_integrated_lufs(audio, sr)`: BS.1770-4 — K-weighting (stage-1 high-shelf +4 dB ≈ 1.68 kHz, stage-2 high-pass ≈ 38 Hz), 400 ms blocks / 75 % overlap, absolute −70 LUFS gate then relative −10 LU gate, L=R=1.0 weights.
- `apply_master(audio, sr, target_lufs, ceiling_dbtp)`: measure → bounded linear gain (±24 dB safety) → limiter → re-measure once if ceiling engagement pulled loudness down (max 2 iterations) → return mastered audio + metrics.
- `write_wav24`: soundfile `PCM_24` with TPDF dither applied at quantization.
- Session metadata records pre/post LUFS, applied gain, true-peak, and limiter engagement.
- **Live playback**: per-chunk *gain-only* loudness matching to the same target (measure + linear gain, no limiter) so listening during a session approximates the final file without pumping at boundaries; a hard safety clip at −1 dBFS guards the gain-up path since there is no limiter. The deliverable gets the full chain at save.
- Config: `[master] enabled = true, target_lufs = -14.0, ceiling_dbtp = -1.0`.
- Robustness: NaN/Inf guard (skip mastering, keep unmastered audio + metadata warning); gain bound; decode fallback — `soundfile` handles non-PCM/wav32 payloads if the `wave` fast path declines.

## Section 4 — Testing & verification

- **Composer:** budget/priority drop-order tests; one-modifier conflict rule; pinned-vs-auto blueprint tests; invalid-pin fallback; golden captions per preset (update existing goldens in `test_prompt_engine.py`; add `test_tag_composer.py`).
- **Payload:** `/release_task` assertions updated (`wav32`, `thinking=true`, `steps=20`, `model` passthrough); doctor range tests (`test_diagnostics.py`).
- **Audio:** BS.1770 anchor — 1 kHz sine at −20 dBFS in stereo must measure −20.0 LUFS (±0.1); limiter respects −1 dBTP on hot input; 24-bit round-trip via soundfile; equal-power crossfade power preservation (constant summed energy across the fade); wav.py channel preservation (2-D shape, no averaging); UI-state persistence round-trip.
- **Live gate (env-gated, marker-based):** real session against the LAN service — assert measured LUFS within ±0.5 LU of target, true-peak ≤ −1 dBTP, stereo channels present and (when server sends true stereo) uncorrelated, 24-bit file on disk; evidence recorded under `.uat/` per the existing harness.
- **Caption A/B:** composer output vs. current captions measured with `scripts/listen.py` (p10/p90 dynamics, sustained %, tempo feel) on a live generation, per the TASK-11 methodology.

## Integration points (current code)

| Change | Location |
|---|---|
| Cyclers + state + persistence | `tui/app.py` (state ~120–126, cyclers ~232–250, bindings 62–84), new `UiStateStore` |
| Catalogs | `options.py` (`TEXTURE_OPTIONS`, preset `default_texture`) |
| Request fields | `domain.py` (`SessionRequest`, `SessionPlan`), `presets.py` (`expand_preset` pin threading) |
| Pin resolution | `composition.py` (`create_blueprint` ~10–43) |
| Caption assembly | new `generation/tag_composer.py`; `prompt_engine.compose_local_prompt` (~133–161) delegates |
| API payload | `generation/http_ace_step.py` (`submit_task` payload ~226–242); `generation/settings.py`; `config.py` |
| Stereo decode | `audio/wav.py` (`read_wav_bytes` 17–35); 2-D plumbing through `normalization.py`, `continuity.py`, `backend/session_manager.py`, `audio/playback.py`, `audio/player.py` |
| Crossfade | `audio/normalization.py` (`crossfade` 121–152) |
| Master + 24-bit write | new `audio/master.py`; `audio/output.py` (`save_wav` → PCM_24); `backend/session_manager.py` save path (~824–885) |
| Doctor | `diagnostics.py` checks (~110–125) |

## Risks

- `thinking=true` lengthens session start and chunk handoffs (accepted under "raise fixed defaults"; config escape hatch + doctor visibility).
- Older server builds may reject `wav32` — config `audio_request_format` fallback, documented.
- 2-D audio plumbing touches many modules — contained by standardizing the array shape at the decode boundary and updating tests first.
- Turbo step cap means base-model users must set `model` for 32–64 step polish — documented, doctor-guided.

## Future work (explicitly out of scope)

Repaint-based seam repair (`task_type: repaint` + `src_audio_path` + `repainting_start/end`); best-of-N chunk selection (`batch_size ≤ 8` + server-side scoring); character master chain (EQ tilt/saturation); era/mood cyclers; Studio screen; the community "Retake" latent-seeding technique.
