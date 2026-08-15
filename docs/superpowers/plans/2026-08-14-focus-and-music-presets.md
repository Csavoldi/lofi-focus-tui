# Focus and Music Presets Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development to implement this plan. Each task uses TDD and two-stage spec/code-quality review.

**Goal:** Make focus goals and music presets independent, explain every selectable option in the TUI, and pass those choices into deterministic planning and ACE-STEP prompts.

**Architecture:** Add one shared option catalog for values and descriptions. Extend the request/plan/blueprint models with focus and recipe data, normalize legacy requests/history at the boundary, and keep the Textual app as a thin selector plus help view. Preserve existing duration/playback/server behavior.

**Tech Stack:** Python 3.10+, Pydantic, FastAPI, Textual, pytest.

---

## Chunk 1: Shared catalogs, request models, and history compatibility

### Task 1: Add the shared option catalog

**Files:**
- Create: `src/lofi_focus_tui/options.py`
- Test: `tests/test_options.py`

- [ ] **Step 1: Write failing catalog tests**

  Test that the shared catalog exposes exactly four focus values, four music preset values,
  three energy values, and four style values, and that every value has a non-empty
  description. Test that the legacy focus set is exactly
  `{deep_work, reading, coding, wind_down}` and distinct from the music preset set.
  Assert the exact descriptions: focus `deep_work` “sustained concentration and low
  distraction”, `reading` “spacious, calm, gentle pulse”, `coding` “forward momentum and
  a steady groove”, `wind_down` “soft, slow decompression”; preset `classic_lofi` “dusty
  keys, swung drums, round bass”, `neo_soul` “warm chords, pocketed rhythm, mellow bass”,
  `ambient_tape` “sparse pulse, wide pads, tape haze”, `jazz_vinyl` “brushed drums, jazz
  harmony, vinyl texture”; energy `low` “soft movement and a restrained pulse”, `steady`
  “balanced movement for ordinary focus work”, `high` “more rhythmic momentum while
  remaining non-distracting”; and the four exact style descriptions from the approved
  spec. Assert the exact focus constraint/arrangement rows and preset motif/drum/bass
  rows from the approved spec.

- [ ] **Step 2: Run the focused tests and verify RED**

  Run: `pytest tests/test_options.py -q`
  Expected: collection/import failure because `lofi_focus_tui.options` does not exist.

- [ ] **Step 3: Implement the minimal catalog**

  Add typed catalogs for `deep_work`, `reading`, `coding`, `wind_down`;
  `classic_lofi`, `neo_soul`, `ambient_tape`, `jazz_vinyl`; the existing energy values;
  and the existing style-tag strings. Store each description beside its value so the
  TUI and backend use one source of truth. The focus entries also own their exact
  `focus_constraints` and `arrangement_sections`; music preset entries also own their
  exact motif, drum feel, and bass behavior. Export `FOCUS_OPTIONS`, `PRESET_OPTIONS`,
  `ENERGY_OPTIONS`, `STYLE_OPTIONS`, and `LEGACY_FOCUS_VALUES`; downstream code imports
  these exports instead of retaining duplicate lists. Tests assert the exact catalog
  values, descriptions, and trait metadata from the approved spec. Define the canonical
  value types/catalogs in this module; reuse the existing `EnergyLevel` type by importing
  or re-exporting it without creating a second energy enum or a circular import. The
  exact catalog rows are the tables in
  `docs/superpowers/specs/2026-08-14-focus-and-preset-information-design.md`.

- [ ] **Step 4: Run the focused tests and verify GREEN**

  Run: `pytest tests/test_options.py -q`
  Expected: all catalog tests pass.

- [ ] **Step 5: Commit**

  ```bash
  git add src/lofi_focus_tui/options.py tests/test_options.py
  git commit -m "feat: add shared focus and music option catalogs"
  ```

### Task 2: Extend request/plan models and normalize legacy requests

**Files:**
- Modify: `src/lofi_focus_tui/domain.py`
- Modify: `src/lofi_focus_tui/presets.py`
- Test: `tests/test_presets.py`
- Test: `tests/test_backend_api.py`
- Test: `tests/test_session_manager.py`
- Test: `tests/test_backend_client.py`
- Test: `tests/test_composition.py`
- Test: `tests/test_ace_step_adapter.py`
- Test: `tests/test_tui_app.py`

- [ ] **Step 1: Write failing model tests**

  Cover these cases:

  ```python
  SessionRequest(preset="classic_lofi", duration_minutes=30, energy="steady").focus == "deep_work"
  SessionRequest(preset="reading", duration_minutes=30, energy="steady").focus == "reading"
  SessionRequest(focus="coding", preset="classic_lofi", duration_minutes=30, energy="steady").preset == "classic_lofi"
  ```

  Add parameterized tests for omitted and `focus=None` with all valid music presets,
  legacy focus-valued presets, explicit `focus="coding"` with legacy `preset="reading"`,
  and unknown focus/preset values. Test `expand_preset()` carries focus, music preset,
  and exact focus constraints into the plan for all four focus values, using the shared
  catalog for the expected lookup. Include `duration_minutes=30` in every request
  fixture so failures exercise migration rather than field construction. Explicit
  non-null focus plus a legacy focus-valued preset must fail validation. Add FastAPI
  request-boundary tests asserting HTTP 422 for invalid focus, invalid music preset, and
  explicit `focus="coding"` with legacy `preset="reading"`.

- [ ] **Step 2: Run the focused tests and verify RED**

  Run: `pytest tests/test_presets.py tests/test_backend_api.py -q`
  Expected: failures because `focus`, music preset validation, and focus constraints do
  not exist yet.

- [ ] **Step 3: Implement the minimal model migration**

  Add `focus` to `SessionRequest` with a pre-validation normalizer that treats missing and
  `null` focus the same. Legacy focus-valued presets migrate to matching focus plus
  `classic_lofi`; valid new presets default to `deep_work`. Add focus and
  `focus_constraints` to `SessionPlan`. Use shared enums/catalog values for validation.

- [ ] **Step 4: Update affected existing request callers**

  Update assertions and fixtures in `tests/test_presets.py`, `tests/test_session_manager.py`,
  `tests/test_backend_client.py`, `tests/test_composition.py`, and
  `tests/test_ace_step_adapter.py` and `tests/test_tui_app.py` so legacy
  `preset="deep_work"` cases assert the normalized focus/music-preset pair rather than
  relying on the old duplicate meaning. Use the non-default pair
  `focus="coding", preset="ambient_tape"` in the SessionManager persistence case and
  assert both values in the record plus `metadata["request"]["focus"]`,
  `metadata["request"]["preset"]`, `metadata["plan"]["focus"]`, and
  `metadata["plan"]["preset"]`.

- [ ] **Step 5: Run the focused tests and verify GREEN**

  Run: `pytest tests/test_presets.py tests/test_backend_api.py tests/test_session_manager.py tests/test_backend_client.py tests/test_composition.py tests/test_ace_step_adapter.py tests/test_tui_app.py -q`
  Expected: all model, migration, and API validation tests pass.

- [ ] **Step 6: Commit**

  ```bash
  git add src/lofi_focus_tui/domain.py src/lofi_focus_tui/presets.py tests/test_presets.py tests/test_backend_api.py tests/test_session_manager.py tests/test_backend_client.py tests/test_composition.py tests/test_ace_step_adapter.py tests/test_tui_app.py
  git commit -m "feat: separate focus from music preset requests"
  ```

### Task 3: Make history migration backward-compatible

**Files:**
- Modify: `src/lofi_focus_tui/history.py`
- Modify: `src/lofi_focus_tui/backend/session_manager.py`
- Test: `tests/test_output_history.py`
- Test: `tests/test_session_manager.py`

- [ ] **Step 1: Write failing history tests**

  Seed raw JSONL rows for all four old focus-valued presets, all four valid music presets,
  and an unknown value. Assert the exact table mapping: each old focus value maps to the
  same focus plus `classic_lofi`; each valid music preset maps to `deep_work` unchanged;
  and the unknown value maps to `deep_work`/`classic_lofi` plus one exact
  `legacy_preset:<old value>` tag. Assert that reading raw rows leaves the JSONL bytes
  unchanged, then perform a normal history write and assert the normalized fields persist.
  Test a second read/write does not duplicate that tag, and test an already-normalized row
  leaves its tags unchanged. Test a
  `SessionManager`-generated record and metadata persist both focus and music preset.

- [ ] **Step 2: Run the focused tests and verify RED**

  Run: `pytest tests/test_output_history.py tests/test_session_manager.py -q`
  Expected: failures because history records have no focus migration or new focus field.

- [ ] **Step 3: Implement read-time migration and new record persistence**

  Add `SessionRecord.focus` with a `deep_work` default and a pre-validation migration for
  raw legacy rows. Normalize before field validation, preserve normalized rows without
  duplicate legacy tags, and persist the normalized shape only on a later normal history
  write. Update `SessionManager` record creation so history and metadata include both
  focus and preset.

- [ ] **Step 4: Run the focused tests and verify GREEN**

  Run: `pytest tests/test_output_history.py tests/test_session_manager.py -q`
  Expected: all history compatibility and SessionManager persistence tests pass.

- [ ] **Step 5: Commit**

  ```bash
  git add src/lofi_focus_tui/history.py src/lofi_focus_tui/backend/session_manager.py tests/test_output_history.py tests/test_session_manager.py
  git commit -m "feat: migrate focus data in session history"
  ```

## Chunk 2: Planner and ACE-STEP prompt behavior

### Task 4: Apply focus and music recipes to blueprints and prompts

**Files:**
- Modify: `src/lofi_focus_tui/composition.py`
- Modify: `src/lofi_focus_tui/domain.py`
- Modify: `src/lofi_focus_tui/generation/ace_step.py`
- Test: `tests/test_composition.py`
- Test: `tests/test_ace_step_adapter.py`
- Test: `tests/test_http_ace_step.py`

- [ ] **Step 1: Write failing blueprint/prompt tests**

  Assert each focus produces its specified arrangement sections and exact constraints, and
  assert `blueprint.focus == plan.focus` plus the complete unchanged continuity boundary
  list (`preserve stable tempo`, `preserve key center`, `preserve shared motif`,
  `avoid abrupt section jumps`) with exact equality, replacing the old
  `avoid abrupt timbre changes` value if encountered. Also assert
  `blueprint.focus_constraints == plan.focus_constraints` and that arrangement sections
  equal the catalog labels.
  Assert each music preset produces its specified motif, drum feel, and bass behavior.
  Compare `coding+classic_lofi` with `coding+ambient_tape` and
  `coding+classic_lofi` with `reading+classic_lofi` to prove both independence axes;
  for each comparison assert `plan.duration_minutes == request.duration_minutes` and
  `plan.energy == request.energy` with a fixed seed. Assert `_blueprint_to_prompt()` includes focus, focus
  constraints, arrangement sections, and all four existing boundary constraints, so focus
  affects generated audio rather than only metadata. Add the same assertions for the
  `create_chunk_blueprint()` prompt path. Assert the HTTP adapter still sends the same
  payload shape with the expanded prompt. The HTTP test asserts the exact release-payload
  key set `{audio_duration, prompt, lyrics, thinking, inference_steps, guidance_scale,
  audio_format, batch_size, use_random_seed}`, plus only the existing conditional `seed`
  key.

- [ ] **Step 2: Run the focused tests and verify RED**

  Run: `pytest tests/test_composition.py tests/test_ace_step_adapter.py tests/test_http_ace_step.py -q`
  Expected: failures because the blueprint is currently hard-coded to one recipe and the
  prompt omits focus arrangement data.

- [ ] **Step 3: Implement the deterministic mappings**

  Add `focus` and `focus_constraints` to `CompositionBlueprint`. Copy `plan.focus` into
  `blueprint.focus` and assert/copy `blueprint.focus_constraints == plan.focus_constraints`.
  Task 2 owns population of
  `SessionPlan.focus_constraints`; this task consumes that plan field. Copy the exact
  focus constraints into the blueprint’s new `focus_constraints` field and copy catalog
  arrangement labels into `arrangement_sections`. Preserve the existing continuity
  `boundary_constraints` invariant, exactly `preserve stable tempo`, `preserve key center`,
  `preserve shared motif`, and `avoid abrupt section jumps`. Select the exact
  catalog-owned motif/drum/bass values for each music preset. Add blueprint focus,
  focus constraints, arrangement sections, and existing boundary constraints to the
  prompt without changing the ACE-STEP HTTP payload shape. Assert the exact release
  payload key set `{audio_duration, prompt, lyrics, thinking, inference_steps,
  guidance_scale, audio_format, batch_size, use_random_seed}`, plus only the existing
  conditional `seed` key, and add a
  `create_chunk_blueprint()` prompt test because chunk blueprints also go through the
  ACE-STEP adapter.

- [ ] **Step 4: Run the focused tests and verify GREEN**

  Run: `pytest tests/test_presets.py tests/test_composition.py tests/test_ace_step_adapter.py tests/test_http_ace_step.py -q`
  Expected: all planner, independent-combination, and prompt tests pass.

- [ ] **Step 5: Commit**

  ```bash
  git add src/lofi_focus_tui/domain.py src/lofi_focus_tui/composition.py src/lofi_focus_tui/generation/ace_step.py tests/test_composition.py tests/test_ace_step_adapter.py tests/test_http_ace_step.py
  git commit -m "feat: apply focus and music recipes to generation prompts"
  ```

## Chunk 3: TUI selections, descriptions, and help

### Task 5: Update the TUI model and main-screen descriptions

**Files:**
- Modify: `src/lofi_focus_tui/tui/app.py`
- Modify: `src/lofi_focus_tui/tui/widgets.py`
- Test: `tests/test_tui_app.py`

- [ ] **Step 1: Write failing TUI tests**

  Assert initial values are `focus=deep_work` and `preset=classic_lofi`. Assert the main
  screen renders distinct focus and preset lines with descriptions for focus, preset,
  energy, and style. Assert `1` cycles focus, `p` cycles music preset, `2` still cycles
  duration, and the generated request carries all four independent selections. Assert the
  complete non-help binding table (`1`, `p`, `2`, `3`, `4`, `s`, `space`, `x`, `r`, and
  `q`) remains registered.

- [ ] **Step 2: Run the focused tests and verify RED**

  Run: `pytest tests/test_tui_app.py -q`
  Expected: failures because the app has no focus state and still uses `1` for preset.

- [ ] **Step 3: Implement the minimal TUI changes**

  Add `self.focus`, change the initial preset to `classic_lofi`, use the shared catalog
  descriptions in rendering, explicitly import `FOCUS_OPTIONS`, `PRESET_OPTIONS`,
  `ENERGY_OPTIONS`, and `STYLE_OPTIONS`, delete the existing `PRESETS`, `ENERGIES`, and
  `STYLE_TAG_SETS` lists, and cycle/render directly from the shared catalogs. Update
  key bindings to `1` focus / `p` preset / `2` duration / `3` energy / `4` style, and include
  `focus` in `SessionRequest`. Leave `h` for Task 6.

- [ ] **Step 4: Run the focused tests and verify GREEN**

  Run: `pytest tests/test_tui_app.py -q`
  Expected: all TUI selection and rendering tests pass.

- [ ] **Step 5: Commit**

  ```bash
  git add src/lofi_focus_tui/tui/app.py src/lofi_focus_tui/tui/widgets.py tests/test_tui_app.py
  git commit -m "feat: show separate focus and music preset choices"
  ```

### Task 6: Add the option guide view

**Files:**
- Modify: `src/lofi_focus_tui/tui/app.py`
- Modify: `src/lofi_focus_tui/tui/widgets.py`
- Test: `tests/test_tui_app.py`

- [ ] **Step 1: Write failing help-view tests**

  Press `h` in a mounted app and assert the active guide screen displays all focus, music
  preset, energy, and style descriptions. Assert the guide is read-only while open: `1`,
  `p`, `2`, `3`, `4`, `s`, `space`, `x`, and `r` do not change selections or call the
  backend. `q` remains the global quit action while the guide is open via a guide-local
  `q -> app.quit` binding, and is tested. Assert `Escape` and `h` close it and return to
  the main view from a freshly opened guide; tests query `pilot.app.screen`, not the
  default-screen helper.

- [ ] **Step 2: Run the focused tests and verify RED**

  Run: `pytest tests/test_tui_app.py -q`
  Expected: failures because no guide action/view exists; the selection bindings from
  Task 5 remain intact.

- [ ] **Step 3: Implement the guide using existing Textual primitives**

  Add the `h` binding and a small modal/help screen or overlay using Textual’s built-in
  screen/widget APIs. Render the shared catalog, suppress selection/session actions while
  the guide is open, keep `q` as the global quit action via a guide-local binding, and
  handle `h` and `Escape` to close it. Use only the existing Textual dependency; do not
  add a new UI framework or settings system.

- [ ] **Step 4: Run the focused tests and verify GREEN**

  Run: `pytest tests/test_tui_app.py -q`
  Expected: all help-view tests pass.

- [ ] **Step 5: Commit**

  ```bash
  git add src/lofi_focus_tui/tui/app.py src/lofi_focus_tui/tui/widgets.py tests/test_tui_app.py
  git commit -m "feat: add TUI option guide"
  ```

## Chunk 4: Documentation and full verification

### Task 7: Document the new controls and option meanings

**Files:**
- Modify: `README.md`
- Modify: `docs/usage.md`
- Modify: `docs/configuration.md`
- Modify: `docs/user-acceptance-testing.md`

- [ ] **Step 1: Update documentation**

  In `README.md`, replace any stale combined `1       change focus preset` or
  “cycle preset” wording with the exact sentence “focus and music preset are separate
  request fields”, a pointer to `docs/usage.md`, and this exact key block:

  ```text
  1       change focus
  p       change music preset
  2       change duration
  3       change energy
  4       change style
  h       open option guide
  Escape  close option guide
  ```

  and a pointer to the full guide. Keep the screenshot/theme proof of concept unchanged.
  In `docs/usage.md`, replace stale bindings, list every option using these exact lines:
  `deep_work: sustained concentration and low distraction`, `reading: spacious, calm,
  gentle pulse`, `coding: forward momentum and a steady groove`, `wind_down: soft, slow
  decompression`; `classic_lofi: dusty keys, swung drums, round bass`, `neo_soul: warm
  chords, pocketed rhythm, mellow bass`, `ambient_tape: sparse pulse, wide pads, tape
  haze`, `jazz_vinyl: brushed drums, jazz harmony, vinyl texture`; `low: soft movement and
  a restrained pulse`, `steady: balanced movement for ordinary focus work`, `high: more
  rhythmic momentum while remaining non-distracting`; and the four exact style lines from
  the approved spec. Show the same exact key block and document `h`/`Escape` guide behavior.
  In `docs/configuration.md`, include the exact sentence “focus and music preset are
  separate API fields”, and document that API requests now carry separate `focus` and
  music `preset` fields, including omitted/null
  legacy normalization; explicitly state that omitted and `null` focus follow the same
  path, legacy focus-valued presets map to matching focus plus `classic_lofi`, and valid
  music `preset` values default the separate `focus` field to `deep_work`, with no
  TOML keys change. In
  `docs/user-acceptance-testing.md`, add
  an acceptance step that selects `focus=coding`, `preset=ambient_tape`,
  `energy=steady`, and `style_tags=["rainy", "mellow"]`, opens the guide, closes it with
  both `Escape` and `h` in separate fresh runs (with the exact lines “fresh run closes with
  Escape” and “fresh run closes with h”), and verifies the exact values
  `request.focus == "coding"`, `request.preset == "ambient_tape"`,
  `plan.focus == "coding"`, and `plan.preset == "ambient_tape"`, plus prompt content
  containing the concrete coding traits `consistent forward pulse`, `stable groove`, and
  `no abrupt changes`, plus the ambient-tape traits `sparse washed pad motif`, `minimal
  soft pulse`, and `long sustained low movement`.

- [ ] **Step 2: Run documentation checks**

  Run:

  ```bash
  set -e
  git diff --check
  for file in README.md docs/usage.md; do
    ! rg -q -F '1       change focus preset' "$file"
    ! rg -q -F 'cycle preset' "$file"
    rg -q -F -x '1       change focus' "$file"
    rg -q -F -x 'p       change music preset' "$file"
    rg -q -F -x '2       change duration' "$file"
    rg -q -F -x '3       change energy' "$file"
    rg -q -F -x '4       change style' "$file"
    rg -q -F -x 'h       open option guide' "$file"
    rg -q -F -x 'Escape  close option guide' "$file"
  done
  for phrase in \
    'deep_work: sustained concentration and low distraction' \
    'reading: spacious, calm, gentle pulse' \
    'coding: forward momentum and a steady groove' \
    'wind_down: soft, slow decompression' \
    'classic_lofi: dusty keys, swung drums, round bass' \
    'neo_soul: warm chords, pocketed rhythm, mellow bass' \
    'ambient_tape: sparse pulse, wide pads, tape haze' \
    'jazz_vinyl: brushed drums, jazz harmony, vinyl texture' \
    'low: soft movement and a restrained pulse' \
    'steady: balanced movement for ordinary focus work' \
    'high: more rhythmic momentum while remaining non-distracting' \
    'lofi, neo_soul: warm, dusty, chord-forward texture' \
    'ambient, tape: spacious, hazy, slowly moving texture' \
    'rainy, mellow: soft atmosphere and subdued detail' \
    'jazz, vinyl: brushed, tactile, lightly swinging texture'; do
    rg -q --fixed-strings "$phrase" docs/usage.md
  done
  rg -q --fixed-strings 'focus and music preset are separate request fields' README.md
  rg -q --fixed-strings 'docs/usage.md' README.md
  rg -q --fixed-strings 'focus and music preset are separate API fields' docs/configuration.md
  rg -q --fixed-strings 'omitted focus and null focus follow the same normalization path' docs/configuration.md
  rg -q --fixed-strings 'legacy focus-valued presets map to matching focus plus classic_lofi' docs/configuration.md
  rg -q --fixed-strings 'valid music preset values default the separate focus field to deep_work' docs/configuration.md
  rg -q --fixed-strings 'no TOML keys change' docs/configuration.md
  rg -q --fixed-strings 'focus=coding' docs/user-acceptance-testing.md
  rg -q --fixed-strings 'preset=ambient_tape' docs/user-acceptance-testing.md
  rg -q --fixed-strings 'energy=steady' docs/user-acceptance-testing.md
  rg -q --fixed-strings 'style_tags=["rainy", "mellow"]' docs/user-acceptance-testing.md
  rg -q --fixed-strings 'request.focus == "coding"' docs/user-acceptance-testing.md
  rg -q --fixed-strings 'request.preset == "ambient_tape"' docs/user-acceptance-testing.md
  rg -q --fixed-strings 'plan.focus == "coding"' docs/user-acceptance-testing.md
  rg -q --fixed-strings 'plan.preset == "ambient_tape"' docs/user-acceptance-testing.md
  rg -q --fixed-strings 'fresh run closes with Escape' docs/user-acceptance-testing.md
  rg -q --fixed-strings 'fresh run closes with h' docs/user-acceptance-testing.md
  rg -q --fixed-strings 'consistent forward pulse' docs/user-acceptance-testing.md
  rg -q --fixed-strings 'stable groove' docs/user-acceptance-testing.md
  rg -q --fixed-strings 'no abrupt changes' docs/user-acceptance-testing.md
  rg -q --fixed-strings 'sparse washed pad motif' docs/user-acceptance-testing.md
  rg -q --fixed-strings 'minimal soft pulse' docs/user-acceptance-testing.md
  rg -q --fixed-strings 'long sustained low movement' docs/user-acceptance-testing.md
  ```

  Expected: every command exits 0, proving the assigned files contain the required
  option families, exact bindings, guide behavior, and compatibility terms.

- [ ] **Step 3: Commit**

  ```bash
  git add README.md docs/usage.md docs/configuration.md docs/user-acceptance-testing.md
  git commit -m "docs: explain focus and music preset choices"
  ```

### Task 8: Run the complete verification suite

**Files:**
- No source changes expected.

- [ ] **Step 1: Run lint**

  Run: `ruff check src tests`
  Expected: exit 0.

- [ ] **Step 2: Run all tests**

  Run: `pytest -q`
  Expected: all tests pass; live ACE-STEP tests remain opt-in and are not run by default.

- [ ] **Step 3: Inspect the final diff and status**

  Run: `git branch --show-current && git log --oneline main..HEAD && git diff main...HEAD --stat && git status --short`
  Expected: current branch is `dev`; the log lists only planned implementation/spec/docs
  commits; the stat contains only planned paths; unrelated `config.example.toml` and
  `.superpowers/` changes remain uncommitted and untouched.
