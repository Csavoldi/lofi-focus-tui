# Audio Chunk Orchestration Implementation Plan

> **For agentic workers:** REQUIRED: Use `superpowers:executing-plans` to implement this plan. Subagents are unavailable in this side conversation, so execute it in the isolated worktree with the checkpoints below.

**Goal:** Generate longer focus sessions in 5/10-minute chunks and use deterministic audio feedback to improve continuity between chunks.

**Architecture:** Keep `SessionManager._generate_session_result` as the orchestration loop. Extend the existing continuity module with per-chunk profiles, severity, and continuation-note mapping; pass notes through an optional `CompositionBlueprint` field into the shared ACE-Step prompt builder; retain the current fixed crossfade and one retry for severe boundaries.

**Tech Stack:** Python 3.10+, NumPy, Pydantic, pytest, existing ACE-Step embedded and HTTP adapters.

---

## File map

- Modify `src/lofi_focus_tui/config.py`: make 600 seconds the safe default chunk cap while preserving the 10–600 validation range.
- Modify `config.example.toml`: show the new 600-second default.
- Modify `src/lofi_focus_tui/audio/continuity.py`: add deterministic chunk profiles, boundary severity, spectral-window comparison, continuation notes, and JSON-safe serialization.
- Modify `src/lofi_focus_tui/domain.py`: add optional continuation constraints to `CompositionBlueprint` without breaking existing blueprint fixtures.
- Modify `src/lofi_focus_tui/composition.py`: allow chunk blueprints to receive continuation constraints.
- Modify `src/lofi_focus_tui/generation/ace_step.py`: include continuation constraints in the shared prompt builder.
- Modify `src/lofi_focus_tui/backend/session_manager.py`: apply request-aware chunk sizing, carry handoffs, retry only severe boundaries, and persist per-chunk metadata.
- Modify `tests/test_config.py`: cover the new default and upper-bound validation.
- Modify `tests/test_continuity.py`: cover profiles, spectral windows, severity, notes, and serialization.
- Modify `tests/test_composition.py`: cover continuation constraints on chunk blueprints.
- Modify `tests/test_ace_step_adapter.py`: verify continuation constraints reach the embedded ACE-Step prompt.
- Modify `tests/test_http_ace_step.py`: verify the HTTP payload keeps its shape and receives the shared prompt notes.
- Modify `tests/test_session_manager.py`: cover 5/10-minute timing, ordinary handoffs, severe retry, failure, and metadata.
- Modify `docs/configuration.md` and `docs/usage.md`: document policy and fixed-crossfade behavior.

## Chunk 1: Configuration and timing policy

**Files:** `src/lofi_focus_tui/config.py`, `config.example.toml`, `tests/test_config.py`, `tests/test_session_manager.py`

- [ ] **Step 1: Write failing configuration tests.**

Add tests that assert:

```python
def test_generation_config_defaults_to_ten_minute_chunk_cap():
    assert GenerationConfig().chunk_seconds == 600


def test_generation_config_rejects_chunk_cap_above_ten_minutes():
    with pytest.raises(ValidationError):
        GenerationConfig(chunk_seconds=601)
```

Keep the existing test proving values below the cap are accepted.

- [ ] **Step 2: Run the focused tests and verify they fail for the missing default.**

Run:

```bash
pytest tests/test_config.py -q
```

Expected: the new default assertion fails because the current default is 30.

- [ ] **Step 3: Write failing timing tests for the request-aware policy.**

Use the existing `ChunkRecordingModel` and `RecordingPlayback` fixtures. With
`SessionManager(model=model, playback=playback, chunk_seconds=600)`, assert:

```python
request = make_request().model_copy(update={"duration_minutes": 5})
manager.start_session(request)
manager.wait_for_active_task()
assert [duration for _blueprint, duration, _settings in model.calls] == [300]
```

Add an 11-minute case asserting `[600, 60]`. Add a lower-cap regression case using
`chunk_seconds=60` and assert the existing `[60, ...]` behavior remains available.

- [ ] **Step 4: Run the timing tests and verify the policy assertions fail.**

Run:

```bash
pytest tests/test_session_manager.py -q -k 'chunked_generation or timing or duration'
```

Expected: the 5-minute and 11-minute cases fail because the manager currently uses the
configured value directly.

- [ ] **Step 5: Implement the smallest timing change.**

Change `GenerationConfig.chunk_seconds` default to `600` and the example config to `600`.
In `SessionManager._resolve_timing`, preserve the `None` path and render limit behavior.
For chunked sessions, select:

```python
target_seconds = 300 if requested_seconds <= 300 else 600
chunk_seconds = min(target_seconds, max(1, self.chunk_seconds))
```

Continue calculating the final remainder with the existing ceiling/list logic. Do not add a
new duration setting or change the 240-minute request validation.

- [ ] **Step 6: Run focused tests and confirm green.**

Run:

```bash
pytest tests/test_config.py tests/test_session_manager.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit the timing change.**

```bash
git add src/lofi_focus_tui/config.py config.example.toml tests/test_config.py tests/test_session_manager.py
git commit -m "feat: use quality-oriented chunk sizes"
```

## Chunk 2: Continuity profiles and prompt handoff primitives

**Files:** `src/lofi_focus_tui/audio/continuity.py`, `src/lofi_focus_tui/domain.py`, `src/lofi_focus_tui/composition.py`, `src/lofi_focus_tui/generation/ace_step.py`, `tests/test_continuity.py`, `tests/test_composition.py`, `tests/test_ace_step_adapter.py`, `tests/test_http_ace_step.py`

- [ ] **Step 1: Write failing continuity tests.**

Add tests for the public behavior, not implementation details:

```python
def test_chunk_profile_reports_audio_metrics_and_json_values():
    profile = analyze_chunk(np.full(100, 0.05, dtype=np.float32), sample_rate=10)
    assert profile.rms == pytest.approx(0.05)
    assert profile.peak == pytest.approx(0.05)
    assert profile.silent is False
    assert profile.clipped is False
    assert profile.to_dict()["duration_seconds"] == 10.0


def test_boundary_severity_distinguishes_large_loudness_jump():
    report = analyze_boundary(
        np.full(100, 0.05, dtype=np.float32),
        np.full(100, 0.90, dtype=np.float32),
        sample_rate=10,
    )
    assert report.accepted is False
    assert report.severe is True


def test_ordinary_loudness_warning_creates_next_chunk_note():
    report = analyze_boundary(
        np.full(100, 0.05, dtype=np.float32),
        np.full(100, 0.30, dtype=np.float32),
        sample_rate=10,
    )
    assert report.severe is False
    assert continuation_notes(report) == [
        "match the previous chunk's loudness at the transition"
    ]
```

Retain and update existing continuity tests so they still cover RMS, boundary delta,
silence, clipping, clean boundaries, and the `reasons` alias.

- [ ] **Step 2: Run continuity tests and verify the new tests fail.**

Run:

```bash
pytest tests/test_continuity.py -q
```

Expected: import/attribute failures for the new profile and severity APIs.

- [ ] **Step 3: Implement deterministic profile and severity support.**

In `audio/continuity.py`:

- Add a frozen `ChunkProfile` dataclass with `sample_rate`, `duration_seconds`, `rms`,
  `peak`, `silent`, `clipped`, and a scalar spectral-balance value.
- Add `analyze_chunk(audio, sample_rate)` using existing `rms`, `peak`, `is_silent`, and
  `is_clipped` helpers. Use a bounded short FFT window for spectral balance; handle empty
  and short arrays without raising.
- Extend `ContinuityReport` with `severe: bool`, `spectral_delta`, and JSON-safe `to_dict()`
  methods. Keep existing fields and `reasons` behavior.
- Let `analyze_boundary` accept an optional `sample_rate=44100`, compare bounded tail/head
  windows, and preserve current warning strings.
- Classify `silent audio`, `clipping`, and `boundary click` as severe. Classify a very large
  loudness jump as severe while retaining a smaller loudness jump as an ordinary warning.
  Spectral imbalance is an ordinary warning unless it also triggers an existing severe
  condition.
- Add `continuation_notes(report)` with a fixed warning-to-note mapping from the approved
  spec. Return an empty list for a clean report.

Use only NumPy and the standard library. Keep thresholds as module constants so the behavior
is deterministic and easy to tune after listening tests.

- [ ] **Step 4: Run continuity tests and confirm green.**

Run:

```bash
pytest tests/test_continuity.py -q
```

Expected: PASS.

- [ ] **Step 5: Write failing blueprint and prompt tests.**

Add a composition test that calls:

```python
blueprint = create_chunk_blueprint(
    plan, chunk_index=1, chunk_count=2,
    continuation_constraints=["avoid a sharp transient at the transition"],
)
assert blueprint.continuation_constraints == [
    "avoid a sharp transient at the transition"
]
```

Add embedded and HTTP adapter assertions that the same note appears in the generated prompt,
while the HTTP request still contains the existing payload keys and duration.

- [ ] **Step 6: Run the adapter/composition tests and verify they fail.**

Run:

```bash
pytest tests/test_composition.py tests/test_ace_step_adapter.py tests/test_http_ace_step.py -q
```

Expected: blueprint construction rejects the new keyword or the prompt omits the note.

- [ ] **Step 7: Implement the minimal handoff path.**

- Add `continuation_constraints: list[str] = Field(default_factory=list)` to
  `CompositionBlueprint`.
- Add an optional `continuation_constraints` argument to `create_chunk_blueprint` and copy
  it into the returned model.
- Append non-empty continuation constraints in `_blueprint_to_prompt` after the existing
  continuity language. The HTTP adapter continues importing this shared function; do not
  change its REST payload shape.

- [ ] **Step 8: Run focused tests and confirm green.**

Run:

```bash
pytest tests/test_composition.py tests/test_ace_step_adapter.py tests/test_http_ace_step.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit continuity and prompt primitives.**

```bash
git add src/lofi_focus_tui/audio/continuity.py src/lofi_focus_tui/domain.py src/lofi_focus_tui/composition.py src/lofi_focus_tui/generation/ace_step.py tests/test_continuity.py tests/test_composition.py tests/test_ace_step_adapter.py tests/test_http_ace_step.py
git commit -m "feat: add deterministic chunk handoff analysis"
```

## Chunk 3: Session orchestration, retry, and metadata

**Files:** `src/lofi_focus_tui/backend/session_manager.py`, `tests/test_session_manager.py`

- [ ] **Step 1: Write failing session-manager tests for handoff behavior.**

Add a model fixture that records every blueprint and returns controlled audio values. Assert:

- an ordinary boundary warning keeps the current chunk, adds a continuation note to the
  following blueprint, and makes no retry call;
- a severe boundary warning causes exactly one retry with the corrective note and the
  deterministic seed offset;
- a second severe failure ends in `BackendState.ERROR` with the continuity reason;
- clean two-chunk generation leaves the next blueprint without corrective notes.

Use small sample-rate-10 arrays in unit tests, as the existing chunk fixtures do, so tests do
not allocate real 10-minute waveforms.

- [ ] **Step 2: Run the new session tests and verify they fail.**

Run:

```bash
pytest tests/test_session_manager.py -q -k 'handoff or retry or metadata'
```

Expected: the manager currently retries every warning, never passes continuation notes, and
does not persist chunk metadata.

- [ ] **Step 3: Refactor the existing chunk loop minimally.**

In `_generate_session_result`:

1. Keep `handoff = []`, `chunk_results = []`, and `chunk_metadata = []` local to the call.
2. Pass the current handoff to `create_chunk_blueprint`.
3. Generate the chunk and analyze its profile.
4. If there is a previous result, analyze the boundary with the actual sample rate.
5. For an ordinary warning, keep the result and set the next handoff from
   `continuation_notes(report)`.
6. For a severe warning, retry once using a copied blueprint with the corrective notes and
   the existing deterministic seed-offset behavior. Re-analyze the retry; raise the existing
   continuity error if it remains severe/unaccepted.
7. Append one JSON-safe chunk record containing index, duration, profile, boundary report,
   handoff, and retry count.
8. Preserve existing cancellation checks and progress messages.

Keep `_retry_chunk_if_needed` if it remains clear, but change its contract so it only retries
severe reports and returns enough report/retry information for metadata. Do not introduce a
new orchestration class.

- [ ] **Step 4: Add chunk metadata to the existing stitch result.**

Pass `chunk_metadata` into `_stitch_chunk_results` and add it to the returned metadata under
`"chunks"`. Preserve the existing session id, chunk count, requested duration, actual
duration, sample-rate validation, and fixed `crossfade_seconds` behavior.

- [ ] **Step 5: Run focused session tests and confirm green.**

Run:

```bash
pytest tests/test_session_manager.py -q
```

Expected: PASS, including existing cancellation, render-limit, retry, and playback tests.

- [ ] **Step 6: Commit the orchestration behavior.**

```bash
git add src/lofi_focus_tui/backend/session_manager.py tests/test_session_manager.py
git commit -m "feat: orchestrate audio continuity handoffs"
```

## Chunk 4: Documentation and full verification

**Files:** `docs/configuration.md`, `docs/usage.md`

- [ ] **Step 1: Write documentation assertions/checklist.**

Confirm the docs will state:

- 5-minute sessions use a 5-minute chunk;
- longer sessions use chunks up to 10 minutes with a shorter final remainder;
- `generation.chunk_seconds` defaults to 600 and can be lowered but not raised above 600;
- boundaries use a fixed crossfade and deterministic continuation notes;
- severe continuity failures retry once and then fail clearly.

- [ ] **Step 2: Update the two focused docs.**

Keep the explanation short and user-facing. Do not document the deferred playback/export
features yet.

- [ ] **Step 3: Run lint and the full test suite.**

Run:

```bash
ruff check src tests
pytest -q
```

Expected: Ruff passes; pytest reports all non-live tests passing with the existing live test
skipped unless explicitly enabled.

- [ ] **Step 4: Inspect the final diff and status.**

Run:

```bash
git diff --check
git diff --stat HEAD~3..HEAD
git status --short --branch
```

Verify only the audio-orchestration commits and intended docs are present in the feature
worktree. Do not stage or alter unrelated files in the original workspace.

- [ ] **Step 5: Commit documentation and verification changes.**

```bash
git add docs/configuration.md docs/usage.md
git commit -m "docs: explain audio chunk orchestration"
```

