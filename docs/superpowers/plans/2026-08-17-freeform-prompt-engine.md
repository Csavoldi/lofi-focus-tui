# Freeform Prompt Engine Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, freeform-first ACE-Step prompt path that preserves the existing category controls, supports explicit instrumental/vocal mode, and optionally enriches HTTP prompts through `/format_input`.

**Architecture:** Add `prompt` and `vocal_mode` to the existing request → plan → blueprint flow. Put canonical local composition and 512-character truncation in one small prompt-engine module, then let HTTP adapters enrich that local prompt while embedded and mock adapters keep their existing generation contracts. Reuse the existing session/chunk and TUI flows; do not add a prompt database, provider abstraction, or new dependency.

**Tech Stack:** Python 3.10+, Pydantic 2, httpx, Textual, pytest, pytest-asyncio, existing ACE-Step adapters.

**Reference:** `docs/superpowers/specs/2026-08-17-freeform-prompt-engine-design.md`

---

## Chunk 1: Request propagation and deterministic local composition

### Task 1: Add validated prompt and vocal-mode fields

**Files:**
- Modify: `src/lofi_focus_tui/domain.py:38-138`
- Test: `tests/test_prompt_engine.py` (create)

- [ ] **Step 1: Write failing model tests.**

  Define this fixture helper before the tests:

  ```python
  def make_request(**overrides):
      values = {
          "preset": "classic_lofi",
          "duration_minutes": 30,
          "energy": EnergyLevel.STEADY,
      }
      values.update(overrides)
      return SessionRequest(**values)
  ```

  Add tests for these exact invariants:

  ```python
  def test_prompt_is_stripped_and_whitespace_only_becomes_empty():
      request = make_request(prompt="  rainy room  ")
      assert request.prompt == "rainy room"
      assert make_request(prompt=" \t\n ").prompt == ""

  @pytest.mark.parametrize("length", [511, 512])
  def test_prompt_accepts_normalized_unicode_lengths(length):
      assert len(make_request(prompt=f"  {'x' * length}  ").prompt) == length

  def test_prompt_rejects_normalized_length_over_512():
      with pytest.raises(ValidationError):
          make_request(prompt=f"  {'x' * 513}  ")

  def test_prompt_rejects_non_string_values_with_validation_error():
      with pytest.raises(ValidationError):
          make_request(prompt=123)

  @pytest.mark.parametrize("value", [" VOCALS ", "Instrumental"])
  def test_vocal_mode_is_normalized(value):
      assert make_request(vocal_mode=value).vocal_mode == value.strip().lower()
  ```

  Also assert that omitted fields produce `prompt == ""` and
  `vocal_mode == "instrumental"`, while blank/non-string vocal-mode inputs
  are rejected. Validate the same defaults and `mode="before"` vocal-mode
  normalization on `SessionPlan` and `CompositionBlueprint` by validating
  `model_dump()` payloads with the new fields removed. Use `len(str)`
  semantics; do not test byte length.

- [ ] **Step 2: Run the focused tests and verify failure.**

  Run:

  ```bash
  PYTHONPATH=src pytest -q tests/test_prompt_engine.py -k "prompt or vocal_mode"
  ```

  Expected: FAIL because the new fields and validators do not exist.

- [ ] **Step 3: Implement the smallest model change.**

  In `SessionRequest`, add `prompt: str = ""` and
  `vocal_mode: Literal["instrumental", "vocals"] = "instrumental"`.
  Normalize `prompt` with a guarded `mode="before"` field validator that
  returns non-string values unchanged for Pydantic to reject, otherwise strips
  surrounding whitespace, converts whitespace-only input to `""`, and raises
  when the normalized Unicode length exceeds 512. Normalize string vocal-mode
  values with a guarded `mode="before"` validator that returns
  `value.strip().lower()` for strings and otherwise returns the raw value for
  Pydantic to reject. Apply that validator to `SessionRequest`, `SessionPlan`,
  and `CompositionBlueprint`; let Pydantic reject blank and other values.

  Add the same defaulted fields to `SessionPlan`. Add `prompt`, `vocal_mode`,
  and `energy: EnergyLevel = EnergyLevel.STEADY` to
  `CompositionBlueprint` after its existing required fields so older direct
  constructors and serialized plans remain valid. Apply the same vocal-mode
  normalization on both downstream models. Do not add a second request model.

- [ ] **Step 4: Run the focused tests and verify they pass.**

  Run:

  ```bash
  PYTHONPATH=src pytest -q tests/test_prompt_engine.py -k "prompt or vocal_mode"
  ```

  Expected: PASS.

- [ ] **Step 5: Commit the model contract.**

  ```bash
  git add src/lofi_focus_tui/domain.py tests/test_prompt_engine.py
  git commit -m "feat: add prompt and vocal mode fields"
  ```

### Task 2: Preserve fields through preset and blueprint creation

**Files:**
- Modify: `src/lofi_focus_tui/presets.py:8-38`
- Modify: `src/lofi_focus_tui/composition.py:5-61`
- Test: `tests/test_prompt_engine.py`
- Test: `tests/test_presets.py`
- Test: `tests/test_composition.py`

- [ ] **Step 1: Write failing propagation and avoid-tag tests.**

  Build one request with `prompt="late-night rainy room"` and vocal mode,
  expand it, create a blueprint, then create a chunk. Assert the exact prompt,
  vocal mode, and energy survive all four objects. Add tests that instrumental
  mode adds the automatic `vocals` avoid trait, while vocal mode removes
  legacy `vocals`/`no_vocals`/` NO VOCALS ` values but preserves other tags with
  the existing underscore-to-space transformation and original casing.

  Add a chunk test that passes a base blueprint and proves prompt, energy,
  vocal mode, seed, and session identity are copied without re-planning. Create
  the base first, then monkeypatch `composition.create_blueprint` with a spy
  that raises if called; the base-blueprint path must still succeed and the
  spy count must remain zero.

- [ ] **Step 2: Run the focused tests and verify failure.**

  ```bash
  PYTHONPATH=src pytest -q tests/test_prompt_engine.py tests/test_presets.py tests/test_composition.py
  ```

  Expected: FAIL on missing propagation, vocal-mode filtering, and the base
  blueprint argument.

- [ ] **Step 3: Implement propagation and chunk reuse.**

  In `expand_preset()`, copy `request.prompt` and `request.vocal_mode` into
  `SessionPlan`. Normalize legacy avoid tags with
  `tag.replace("_", " ").strip().lower()` only for comparison against
  `{"vocals", "no vocals"}`. In vocal mode skip those two values; in
  instrumental mode add `vocals`; preserve all other transformed tags and the
  existing `sharp transients` and `sudden drops` traits.

  In `create_blueprint()`, copy prompt, vocal mode, and energy. Extend
  `create_chunk_blueprint()` with an optional
  `base_blueprint: CompositionBlueprint | None = None`; use it directly when
  supplied, otherwise retain the existing direct-caller behavior of creating a
  base blueprint from the plan. Apply only the existing chunk context updates
  with `model_copy(update=...)`.

- [ ] **Step 4: Run the focused tests and verify they pass.**

  ```bash
  PYTHONPATH=src pytest -q tests/test_prompt_engine.py tests/test_presets.py tests/test_composition.py
  ```

  Expected: PASS.

- [ ] **Step 5: Commit the propagation change.**

  ```bash
  git add src/lofi_focus_tui/presets.py src/lofi_focus_tui/composition.py tests/test_prompt_engine.py tests/test_presets.py tests/test_composition.py
  git commit -m "feat: propagate prompt intent through blueprints"
  ```

### Task 3: Implement the canonical local prompt engine

**Files:**
- Create: `src/lofi_focus_tui/generation/prompt_engine.py`
- Modify: `src/lofi_focus_tui/generation/ace_step.py:108-126`
- Test: `tests/test_prompt_engine.py`
- Test: `tests/test_ace_step_adapter.py:70-90`

- [ ] **Step 1: Write failing golden-output tests.**

  Add a blueprint fixture containing every field and assert this exact output
  (the fixture uses `prompt="rainy room"`,
  `texture_layers=[" dusty tape ", "", "soft piano"]`, `motif="motif"`,
  `drum_feel="drums"`, `bass_behavior="bass"`, `energy=EnergyLevel.STEADY`,
  `focus="deep_work"`,
  `focus_constraints=["minimal variation", " stable tempo ", "", "no abrupt changes"]`,
  `tempo_bpm=80`, `key_center="D minor"`, `meter="4/4"`,
  `arrangement_sections=["warmup", "", "steady_work"]`,
  `boundary_constraints=[" stable tempo ", ""]`,
  `continuation_constraints=["carry motif"]`, and instrumental mode):

  ```text
  rainy room. Optional musical context: dusty tape, soft piano, motif, drums, bass, steady energy: balanced movement for ordinary focus work, deep_work focus: minimal variation, stable tempo, no abrupt changes. Technical direction: 80 BPM, D minor, meter 4/4, arrangement: warmup, steady_work, stable tempo, carry motif. Vocal direction: instrumental, no vocals
  ```

  Repeat the fixture with `vocal_mode="vocals"` and assert the exact final
  suffix is `Vocal direction: vocals allowed`.

  Test category-only output, deterministic repeatability, empty list items,
  mixed whitespace, normalized user wording first, and the literal `. `
  separator. Add these exact append-boundary cases: 512 `x` characters
  followed by a suffix returns the 512 `x` characters unchanged; 509 `x`
  characters followed by `tail` returns 509 `x` characters plus `. t`; 510
  `x` characters followed by `tail` returns exactly the 510 `x` characters
  with no separator or suffix. Assert a truncated output is at most 512 characters,
  has no trailing whitespace, and never ends with a dangling `. `.

  Add tests for `compose_enriched_prompt()`: no user prompt returns the
  stripped caption directly; a user prompt returns the user wording followed
  by `. ` and the caption under the same 512-character append rule.

- [ ] **Step 2: Run the prompt-engine tests and verify failure.**

  ```bash
  PYTHONPATH=src pytest -q tests/test_prompt_engine.py tests/test_ace_step_adapter.py::test_blueprint_prompt_includes_focus_recipes_and_boundaries
  ```

  Expected: FAIL because the module and canonical output do not exist.

- [ ] **Step 3: Implement the focused engine.**

  In `prompt_engine.py`, define `MAX_PROMPT_LENGTH = 512`, a shared helper
  that strips/discards parts, and `append_prompt_parts(parts)` that uses the
  literal `. ` separator. Before appending a non-first part, require at least
  `len(separator) + 1` remaining characters. Compute the fitting prefix,
  `rstrip()` it, append the separator only when the prefix is non-empty, and
  stop after truncation. This is the single length/truncation implementation.

  Implement `compose_local_prompt(blueprint)` with exactly this source order:
  user prompt; musical context from texture layers, motif, drum feel, bass
  behavior, `f"{blueprint.energy.value} energy: ..."`, and the focus item when
  constraints exist; technical direction from BPM, key, meter, arrangement
  when sections exist, boundary items, and continuation items; then the vocal
  direction. Strip every scalar/list item and flatten list items as defined in
  the spec. Use the existing `ENERGY_OPTIONS` descriptions; do not create a
  style/energy/focus matrix or independently append style/preset text.

  Implement `compose_enriched_prompt(blueprint, caption)` with the normalized
  user prompt first when present, otherwise the stripped caption directly.
  Keep `_blueprint_to_prompt()` in `ace_step.py` as a compatibility wrapper
  delegating to `compose_local_prompt()` so existing imports continue to work.

- [ ] **Step 4: Run the prompt-engine tests and verify they pass.**

  ```bash
  PYTHONPATH=src pytest -q tests/test_prompt_engine.py tests/test_ace_step_adapter.py::test_blueprint_prompt_includes_focus_recipes_and_boundaries
  ```

  Expected: PASS.

- [ ] **Step 5: Commit the deterministic engine.**

  ```bash
  git add src/lofi_focus_tui/generation/prompt_engine.py src/lofi_focus_tui/generation/ace_step.py tests/test_prompt_engine.py tests/test_ace_step_adapter.py
  git commit -m "feat: add deterministic prompt composition"
  ```

## Chunk 2: ACE-Step adapters and session lineage

### Task 4: Add HTTP enrichment and explicit vocal payloads

**Files:**
- Modify: `src/lofi_focus_tui/generation/http_ace_step.py:1-151`
- Modify: `src/lofi_focus_tui/generation/ace_step.py:51-103`
- Test: `tests/test_http_ace_step.py`
- Test: `tests/test_ace_step_adapter.py`

- [ ] **Step 1: Write failing HTTP and embedded adapter tests.**

  Extend the mock HTTP transport tests to return a valid `/format_input`
  response and assert request order is exactly `/format_input`,
  `/release_task`, `/query_result`, `/v1/audio`. Assert the format request has
  the local prompt, `headers=adapter._headers()` (including the bearer token),
  exact enrichment lyrics (`[Instrumental]` or `""`), temperature `0.85`,
  `response.raise_for_status()`, timeout capped at
  `min(30.0, timeout_seconds)`, and the compact sorted `param_obj` string
  using the `duration_seconds` argument.
  Assert `/release_task.prompt` is the final enriched/fallback prompt and its
  instrumental/vocal lyrics and thinking fields are exact.

  Add parametrized fallback tests for connection/timeout/HTTP/invalid-JSON,
  non-dictionary/missing `data`, and missing/non-string/blank/overlong
  `caption`. For every failure assert exactly one `/format_input` call, the
  local prompt as `/release_task.prompt`, and successful generation. Separately
  test invalid optional lyrics (non-string, blank, and overlong) with a valid
  caption: the enriched caption must remain the final prompt, while the
  malformed lyrics are treated as missing. Add vocal tests with and without
  returned lyrics. Update embedded adapter tests to
  assert `[Instrumental]` in instrumental mode and `""` in vocal mode without
  adding a `thinking` argument. Add a RunPod request test that exercises the
  inherited HTTP vocal payload.

- [ ] **Step 2: Run the focused adapter tests and verify failure.**

  ```bash
  PYTHONPATH=src pytest -q tests/test_http_ace_step.py tests/test_ace_step_adapter.py
  ```

  Expected: FAIL on the missing enrichment request, changed request order, and
  new payload fields.

- [ ] **Step 3: Implement HTTP enrichment with non-fatal fallback.**

  Import the prompt-engine functions into `http_ace_step.py`. Before
  `/release_task`, compose the local prompt and POST once to `/format_input`
  using `headers=self._headers()` and call `response.raise_for_status()`
  before reading JSON.
  with:

  ```python
  {
      "prompt": local_prompt,
      "lyrics": "[Instrumental]" if blueprint.vocal_mode == "instrumental" else "",
      "temperature": 0.85,
      "param_obj": json.dumps(
          {
              "duration": int(duration_seconds),
              "bpm": int(blueprint.tempo_bpm),
              "key": blueprint.key_center,
              "time_signature": blueprint.meter.split("/", 1)[0],
              "language": "unknown",
          },
          sort_keys=True,
          separators=(",", ":"),
      ),
  }
  ```

  Use the exact per-request timeout `min(30.0, self.timeout_seconds)` and no
  retry. Accept only a non-empty stripped caption string of at most 512
  Unicode characters under a dictionary `data`; accept optional lyrics only
  when it is a non-empty stripped string of at most 4096 characters. Catch
  transport, HTTP, JSON, and schema failures at this boundary and fall back to
  the exact `local_prompt` string without calling `compose_enriched_prompt()`;
  this prevents duplicating the user wording. A valid caption calls
  `compose_enriched_prompt(blueprint, caption)`: with user wording it returns
  user wording plus `. ` plus the fitting caption, and without user wording it
  returns the stripped caption directly.

  Send the exact final prompt from `compose_enriched_prompt()` to
  `/release_task`. Use `[Instrumental]` and `thinking=False` for instrumental
  mode. For HTTP/RunPod vocal mode, use valid returned lyrics or `""` and
  `thinking=True`. Leave polling and download unchanged.

  In the embedded adapter, call `compose_local_prompt()` and send
  `[Instrumental]` for instrumental mode or `""` for vocal mode; preserve all
  existing pipeline flags and do not add `thinking`.

- [ ] **Step 4: Run the focused adapter tests and verify they pass.**

  ```bash
  PYTHONPATH=src pytest -q tests/test_http_ace_step.py tests/test_ace_step_adapter.py
  ```

  Expected: PASS.

- [ ] **Step 5: Commit the adapter integration.**

  ```bash
  git add src/lofi_focus_tui/generation/http_ace_step.py src/lofi_focus_tui/generation/ace_step.py tests/test_http_ace_step.py tests/test_ace_step_adapter.py
  git commit -m "feat: enrich ACE-Step prompts over HTTP"
  ```

### Task 5: Reuse one plan lineage for all chunks

**Files:**
- Modify: `src/lofi_focus_tui/backend/session_manager.py:312-337`
- Test: `tests/test_session_manager.py`

- [ ] **Step 1: Write a failing session-lineage test.**

  Monkeypatch the composition functions or use a spy around
  `create_blueprint()` and start a multi-chunk session with a freeform prompt
  and vocal mode. Assert one base blueprint is created, every chunk receives
  `base_blueprint=blueprint`, and every generated chunk blueprint retains the
  prompt, energy, and vocal mode. Keep the existing continuation handoff
  assertions.

- [ ] **Step 2: Run the focused test and verify failure.**

  ```bash
  PYTHONPATH=src pytest -q tests/test_session_manager.py -k "chunk or lineage"
  ```

  Expected: FAIL because the manager currently recreates a base blueprint for
  each chunk.

- [ ] **Step 3: Pass the base blueprint into chunk creation.**

  Change the multi-chunk call in `_generate_session_result()` to
  `create_chunk_blueprint(plan, chunk_index, chunk_count,
  continuation_constraints=handoff, base_blueprint=blueprint)`. In the test,
  monkeypatch `lofi_focus_tui.backend.session_manager.create_blueprint` and
  `lofi_focus_tui.backend.session_manager.create_chunk_blueprint` (the symbols
  imported directly by that module), record each call, and assert one base call
  with the exact `plan` object plus one chunk call per chunk with the exact
  positional `plan`, chunk index, and chunk count, the handoff keyword, and
  `base_blueprint=blueprint`. Do not alter
  timing, retries, boundary analysis, or playback.

- [ ] **Step 4: Run the focused test and the session-manager suite.**

  ```bash
  PYTHONPATH=src pytest -q tests/test_session_manager.py
  ```

  Expected: PASS.

- [ ] **Step 5: Commit the lineage fix.**

  ```bash
  git add src/lofi_focus_tui/backend/session_manager.py tests/test_session_manager.py
  git commit -m "fix: reuse session blueprint across chunks"
  ```

## Chunk 3: TUI, API compatibility, and verification

### Task 6: Add prompt summary rendering and the editor widget

**Files:**
- Modify: `src/lofi_focus_tui/tui/widgets.py:33-74`
- Modify: `src/lofi_focus_tui/tui/app.py:52-207`
- Test: `tests/test_tui_app.py`

- [ ] **Step 1: Write failing summary and editor tests.**

  Test that the session display includes instrumental/vocal mode and uses
  `(category-generated)` for an empty/whitespace prompt, the exact stripped
  prompt through 80 Unicode characters, and the first 77 characters plus `...`
  after that. Test that the main app composes an `Input(id="prompt")` with a
  raw Unicode `max_length=512`, starts blurred, and retains the editor value
  when category state changes.

- [ ] **Step 2: Run the focused widget tests and verify failure.**

  ```bash
  PYTHONPATH=src pytest -q tests/test_tui_app.py -k "summary or prompt"
  ```

  Expected: FAIL because the prompt summary, input widget, and new render
  arguments do not exist.

- [ ] **Step 3: Implement summary rendering and editor composition.**

  Add `prompt = ""` and `vocal_mode = "instrumental"` to `LofiFocusApp`.
  Add `prompt_summary()` in `widgets.py` using `prompt.strip()`, returning
  `(category-generated)` for empty text, the exact normalized text through 80
  characters, and `normalized[:77] + "..."` otherwise. Extend
  `render_session()` with prompt and vocal mode. Render an
  `Input(id="prompt", max_length=512)`, call `self.set_focus(None)` in
  `on_mount()` so it starts blurred, and keep its value synchronized with the
  app draft while category state changes; do not alter backend-client
  serialization. The displayed summary must be sourced from
  `editor.value.strip()`, not a stale separate string.

- [ ] **Step 4: Run the focused widget tests and verify they pass.**

  ```bash
  PYTHONPATH=src pytest -q tests/test_tui_app.py -k "summary or prompt"
  ```

  Expected: PASS.

- [ ] **Step 5: Commit the summary/editor slice.**

  ```bash
  git add src/lofi_focus_tui/tui/widgets.py src/lofi_focus_tui/tui/app.py tests/test_tui_app.py
  git commit -m "feat: render freeform prompt editor"
  ```

### Task 7: Route TUI focus and build mode-aware requests

**Files:**
- Modify: `src/lofi_focus_tui/tui/app.py:52-207`
- Test: `tests/test_tui_app.py`

- [ ] **Step 1: Write failing focus, key-routing, and request tests.**

  Assert the editor starts blurred; `i` focuses it; Escape blurs without
  changing `editor.value`; Enter submits the value and blurs. While focused,
  Textual must keep ordinary command characters in the input: pressing `s`
  inserts `s` and makes no backend request, and pressing `v`, `1`, `p`, `2`,
  `3`, or `4` inserts text rather than dispatching an app action. While
  unfocused, `s` starts a session, `v` toggles vocal mode, and the existing
  category keys keep their actions. Test whitespace-boundary summaries use
  exactly `editor.value.strip()` and refresh after text changes, Enter,
  Escape/blur, and category changes; the summary remains editor-derived after
  a backend status refresh.

  Add explicit editor-boundary tests: 512 Unicode characters are accepted and
  `pilot.write("x" * 513)` leaves exactly 512 characters because the Textual
  input boundary caps raw input; the resulting request still passes the
  model's normalized 512-character check.
  Assert instrumental requests carry `prompt=<stripped editor value>`,
  `vocal_mode="instrumental"`, and `avoid_tags=["vocals"]`; vocal requests
  carry `vocal_mode="vocals"` and an empty legacy avoid-tag list.

- [ ] **Step 2: Run the focused routing tests and verify failure.**

  ```bash
  PYTHONPATH=src pytest -q tests/test_tui_app.py -k "focus or key or vocal or request or boundary"
  ```

  Expected: FAIL because the bindings, focus handlers, mode state, and request
  fields are not implemented.

- [ ] **Step 3: Implement explicit focus and action routing.**

  Add `i`, `v`, and `escape` bindings. Implement `i` to focus the prompt
  input, Escape to blur it, and prompt `Input.Submitted`/`Input.Changed`
  handlers to update the display from the current `editor.value.strip()`
  without replacing the editor text. Guard app actions that would conflict with focused editing;
  Textual's focused `Input` handles printable command characters, while the
  same keys dispatch the existing app actions when no widget is focused.
  Refresh the display after input, submit, blur, and category changes.

  Build `SessionRequest` from the stripped editor value and selected mode;
  use `avoid_tags=["vocals"]` only for instrumental mode and `[]` for vocal
  mode. Keep prompt wording independent from the vocal toggle.

- [ ] **Step 4: Run the full TUI test module and verify it passes.**

  ```bash
  PYTHONPATH=src pytest -q tests/test_tui_app.py
  ```

  Expected: PASS.

- [ ] **Step 5: Commit the TUI interaction slice.**

  ```bash
  git add src/lofi_focus_tui/tui/app.py tests/test_tui_app.py
  git commit -m "feat: add prompt editing and vocal mode controls"
  ```

### Task 8: Confirm API compatibility and complete verification

**Files:**
- Modify: `tests/test_backend_api.py`
- Modify: `tests/test_backend_client.py`
- Modify: `tests/test_presets.py`

- [ ] **Step 1: Add API/default regression tests.**

  Inject a `FakeManager` into `create_app(manager=fake_manager)` whose
  `start_session()` records its `SessionRequest` and returns a valid
  `BackendStatus(state="generating", message="generating", backend="mock",
  device="cpu")`. POST a legacy session payload without `prompt` or
  `vocal_mode` and assert the fake received `prompt=""` and
  `vocal_mode="instrumental"`. Assert the backend-client request serializes
  explicit prompt/vocal fields when supplied. Keep endpoint paths and response
  contracts unchanged.

- [ ] **Step 2: Run the API regression tests unchanged.**

  ```bash
  PYTHONPATH=src pytest -q tests/test_backend_api.py tests/test_backend_client.py tests/test_presets.py
  ```

  Expected: PASS. Do not modify tests during this verification step; any
  payload assertion changes belong in the earlier adapter/TUI tasks.

- [ ] **Step 3: Run the complete test and lint checks.**

  ```bash
  PYTHONPATH=src pytest -q
  ruff check src tests
  git diff --check 9492f72..HEAD
  git diff --check
  ```

  Expected: all existing and new tests pass, with the existing live ACE-Step
  skip preserved; Ruff and whitespace checks pass.

- [ ] **Step 4: Review the final diff for scope.**

  Run:

  ```bash
  git diff --name-only 9492f72..HEAD
  git diff --name-only
  git ls-files --others --exclude-standard
  ```

  Expected: the union of these three outputs contains only the approved
  source/test/plan allowlist
  (`src/lofi_focus_tui/domain.py`, `presets.py`, `composition.py`,
  `generation/prompt_engine.py`, `generation/ace_step.py`,
  `generation/http_ace_step.py`, `backend/session_manager.py`,
  `tui/widgets.py`, `tui/app.py`, the explicitly listed `tests/` files, and
  this plan);
  no `config.toml`, `config.example.toml`, `.superpowers/`, unrelated source,
  or new dependency appears. Also confirm no audio, polling, chunk stitching,
  playback, or export behavior changed beyond prompt/vocal payload fields.

- [ ] **Step 5: Commit the verified compatibility/test changes.**

  ```bash
  git add tests/test_backend_api.py tests/test_backend_client.py tests/test_presets.py
  git commit -m "test: cover prompt engine compatibility"
  ```

### Execution handoff

After the plan is approved, execute it in the isolated worktree using
`superpowers:subagent-driven-development`, with a fresh worker for each
independent task and review checkpoints after each task. Before claiming
completion, use `superpowers:verification-before-completion` and report the
actual test/lint results.
