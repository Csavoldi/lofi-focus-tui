# Playback Controls and Session Export Implementation Plan
> **For agentic workers:** REQUIRED: Use superpowers:executing-plans to execute this plan task-by-task.

**Goal:** Add live playback controls to the TUI and let users export the completed audio and metadata to a directory they choose.

**Architecture:** Keep playback state in `PlaybackManager` and expose small HTTP endpoints through the existing FastAPI server. Keep the TUI as a thin client, with a single-input export modal. Reuse the existing cached `audio.wav` and `metadata.json`; export copies them without changing the cache.

**Tech Stack:** Python, FastAPI/Pydantic, Textual, sounddevice, pathlib/shutil, pytest.

---

## Chunk 1: Playback primitives (TDD)

- [ ] Add failing tests for volume, seek, restart, and position/duration to `tests/test_playback.py`.
- [ ] Run `PYTHONPATH=src pytest -q tests/test_playback.py` and confirm the new tests fail for missing behavior.
- [ ] Extend `Player`, `NullPlayer`, and `SoundDevicePlayer` in `src/lofi_focus_tui/audio/player.py` with the minimum live-control behavior. Preserve raw audio and apply volume in the callback.
- [ ] Extend `PlaybackManager` in `src/lofi_focus_tui/audio/playback.py` with clamped volume adjustment and playback navigation.
- [ ] Run the playback tests and `ruff check src/lofi_focus_tui/audio tests/test_playback.py`.
- [ ] Commit: `feat: add playback navigation and volume controls`.

## Chunk 2: Export primitive (TDD)

- [ ] Add failing `OutputManager.export_session` tests covering destination creation, audio/metadata copying, re-export replacement, and invalid source paths.
- [ ] Run `PYTHONPATH=src pytest -q tests/test_output_history.py` and confirm the new tests fail before implementation.
- [ ] Implement the smallest `pathlib`/`shutil.copy2` export method in `src/lofi_focus_tui/audio/output.py`.
- [ ] Run the output tests and `ruff check src/lofi_focus_tui/audio/output.py tests/test_output_history.py`.
- [ ] Commit: `feat: add session audio export`.

## Chunk 3: Backend API and session wiring (TDD)

- [ ] Add failing API/session tests for volume, seek, restart, status playback fields, successful export, and no-audio export errors in `tests/test_backend_api.py`.
- [ ] Run the focused backend tests and confirm the new tests fail.
- [ ] Add validated request/response models and playback fields in `src/lofi_focus_tui/domain.py`.
- [ ] Add `SessionManager` control/export methods in `src/lofi_focus_tui/backend/session_manager.py` and the four endpoints in `src/lofi_focus_tui/backend/api.py`.
- [ ] Run focused backend tests, then `PYTHONPATH=src pytest -q tests/test_backend_api.py tests/test_session_manager.py`.
- [ ] Commit: `feat: expose playback and export endpoints`.

## Chunk 4: TUI client and controls (TDD)

- [ ] Add failing `BackendClient` tests for the new endpoints in `tests/test_backend_client.py`.
- [ ] Add failing TUI tests for key bindings, control actions, and export modal submit/cancel/error behavior in `tests/test_tui_app.py`.
- [ ] Run both focused test files and confirm the new tests fail.
- [ ] Implement client methods in `src/lofi_focus_tui/tui/backend_client.py` and the bindings/modal in `src/lofi_focus_tui/tui/app.py`.
- [ ] Update status rendering in `src/lofi_focus_tui/tui/widgets.py` with volume and position/duration.
- [ ] Run focused TUI/client tests and `ruff check src tests`.
- [ ] Commit: `feat: add TUI playback controls and export modal`.

## Chunk 5: Documentation and full verification

- [ ] Update `README.md` and `docs/usage.md` with the new keys and export behavior.
- [ ] Run `PYTHONPATH=src pytest -q`, `ruff check src tests`, and `python -m compileall -q src`.
- [ ] Review the final diff for unrelated changes and confirm the branch is clean apart from the intended commits.
- [ ] Use `superpowers:finishing-a-development-branch` to present integration options.

### Verification commands

```bash
PYTHONPATH=src pytest -q
ruff check src tests
python -m compileall -q src
```
