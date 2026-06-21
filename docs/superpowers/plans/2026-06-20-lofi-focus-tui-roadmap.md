# Lofi Focus TUI Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `lofi-focus-tui` from a session-first prototype into a usable daily focus-music tool with configurable sessions, real playback, observable generation, session history, continuity, and optional remote ACE-Step execution.

**Architecture:** Keep the current split: Textual TUI talks to a local FastAPI backend; the backend owns session planning, generation, playback, device selection, cache, and continuity. Add focused modules instead of widening `SessionManager` or `LofiFocusApp`: configuration, generation settings, task state, output history, playback backend, and optional remote ACE-Step clients.

**Tech Stack:** Python 3.10+, Textual, FastAPI, httpx, Pydantic v2, NumPy, optional ACE-Step, optional playback library, pytest.

---

## Progress Legend

- [ ] Not started
- [/] In progress
- [x] Complete
- [!] Blocked

When a milestone starts, change its row in the progress table to `[/]`. When all acceptance criteria and verification commands pass, change it to `[x]` and add the commit hash.

## Current Status

- Roadmap created: 2026-06-20
- Implementation status: Milestone 2 complete
- Baseline verification status: `python -m ruff check src tests` and `python -m pytest -v` pass
- Local repo path: `C:\Users\GDesktop-1\Working\Github\lofi-focus-tui`

## Progress Table

| Status | Milestone | Outcome | Suggested Commit | Commit Hash |
| --- | --- | --- | --- | --- |
| [x] | 0. Repo hygiene and baseline | Local dev workflow and tests are reproducible | `chore: establish baseline quality checks` | 99d39f7486accd09292cb2b772ff5e42bcd224a4 |
| [x] | 1. Config and generation settings | Sessions and ACE-Step parameters are validated and configurable | `feat(config): add app config and generation settings` | a2c03ef5b3a9e248e1159c16058d484bd6b1b5aa |
| [x] | 2. Async backend task state | Session start returns quickly and `/status` reports generation progress | `feat(backend): add async session task state` | 376cd677131f21aeb48bd1bff064112c2f0e5130 |
| [ ] | 3. Real playback backend | Generated audio can be played, paused, resumed, stopped, and faded | `feat(audio): add local playback backend` |  |
| [ ] | 4. Session controls in the TUI | Users can configure and steer sessions from the Textual app | `feat(tui): add configurable session controls` |  |
| [ ] | 5. Output cache and history | Generated tracks, metadata, favorites, and replays persist across runs | `feat(history): persist session outputs and metadata` |  |
| [ ] | 6. Continuity and chunk queue | Long sessions are generated as coherent chunks with crossfades | `feat(audio): add chunk queue and continuity gates` |  |
| [ ] | 7. ACE-Step HTTP and cloud execution | Backend can use embedded, local HTTP, or RunPod-style ACE-Step execution | `feat(generation): add remote ace-step clients` |  |
| [ ] | 8. Quality, docs, and release polish | CLI diagnostics, CI checks, docs, and user-facing workflows are complete | `docs: add usage guide and release checklist` |  |

## Reference Inputs

- `Csavoldi/lofi-focus-tui`: current target repo.
- `frankbria/auto-music-gen`: useful reference for TOML config, validated generation request parameters, local ACE-Step HTTP client, RunPod client shape, progress polling, GPU checks, and output metadata. Do not copy the wizard UI wholesale; `lofi-focus-tui` should remain a persistent Textual session app.

## Product Principles

- Session-first: the primary workflow is "start and stay focused", not "generate a song and leave".
- Quiet by default: avoid vocals, drops, sharp transients, abrupt volume jumps, and distracting UI churn.
- Observable generation: long work must expose progress, errors, active backend, device, task ID, and output path.
- Local-first: mock and local generation remain first-class; remote execution is optional.
- Cache-first for usability: repeat sessions should be replayable and regenerable from saved metadata.

## Current Project Shape

Existing files that should remain the main extension points:

- `src/lofi_focus_tui/domain.py`: Pydantic models and enums.
- `src/lofi_focus_tui/presets.py`: preset-to-session-plan expansion.
- `src/lofi_focus_tui/composition.py`: session plan to composition blueprint.
- `src/lofi_focus_tui/backend/api.py`: FastAPI endpoints.
- `src/lofi_focus_tui/backend/session_manager.py`: backend orchestration.
- `src/lofi_focus_tui/tui/app.py`: Textual app shell.
- `src/lofi_focus_tui/tui/backend_client.py`: async HTTP client for TUI-to-backend calls.
- `src/lofi_focus_tui/generation/base.py`: model adapter protocol and result object.
- `src/lofi_focus_tui/generation/mock.py`: deterministic test generator.
- `src/lofi_focus_tui/generation/ace_step.py`: embedded ACE-Step adapter.
- `src/lofi_focus_tui/audio/playback.py`: playback facade.
- `src/lofi_focus_tui/audio/cache.py`: cache path helper.
- `src/lofi_focus_tui/audio/continuity.py`: boundary quality checks.
- `src/lofi_focus_tui/devices.py`: device selection.
- `tests/`: component tests for backend, TUI, presets, devices, continuity, and adapters.

## Target File Structure

Create these focused modules as milestones need them:

- `src/lofi_focus_tui/config.py`: TOML and environment config loading.
- `src/lofi_focus_tui/generation/settings.py`: validated generation settings and ACE-Step parameter mapping.
- `src/lofi_focus_tui/backend/tasks.py`: task state, progress, and worker abstractions.
- `src/lofi_focus_tui/backend/events.py`: optional event records for progress/status logs.
- `src/lofi_focus_tui/audio/player.py`: concrete playback implementation behind `PlaybackManager`.
- `src/lofi_focus_tui/audio/output.py`: output directory, metadata, and file naming.
- `src/lofi_focus_tui/audio/normalization.py`: loudness, clipping, silence, fade utilities.
- `src/lofi_focus_tui/history.py`: session history and favorite/replay lookup.
- `src/lofi_focus_tui/generation/http_ace_step.py`: local/remote ACE-Step HTTP client adapter.
- `src/lofi_focus_tui/generation/runpod.py`: optional RunPod pod lifecycle adapter.
- `src/lofi_focus_tui/diagnostics.py`: `lofi doctor` checks.
- `src/lofi_focus_tui/tui/widgets.py`: reusable Textual widgets once `app.py` grows beyond a small shell.

Add matching tests:

- `tests/test_config.py`
- `tests/test_generation_settings.py`
- `tests/test_backend_tasks.py`
- `tests/test_playback.py`
- `tests/test_output_history.py`
- `tests/test_normalization.py`
- `tests/test_http_ace_step.py`
- `tests/test_diagnostics.py`

---

## Milestone 0: Repo Hygiene and Baseline

**Status:** [x]

**Goal:** Establish a known-good baseline before changing behavior.

**Files:**
- Modify: `README.md`
- Modify: `pyproject.toml`
- Create: `docs/superpowers/plans/2026-06-20-lofi-focus-tui-roadmap.md`
- Test: existing `tests/*.py`

**Steps:**

- [x] Confirm the current test suite passes.

  Run:

  ```bash
  python -m pip install -e ".[dev]"
  pytest -v
  ```

  Expected: all existing tests pass.

- [x] Add lint tooling if the project accepts it.

  Preferred `pyproject.toml` additions:

  ```toml
  [project.optional-dependencies]
  dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.6",
  ]

  [tool.ruff]
  target-version = "py310"
  line-length = 100

  [tool.ruff.lint]
  select = ["E", "F", "I", "W"]
  ```

- [x] Verify formatting/lint command.

  Run:

  ```bash
  ruff check src tests
  pytest -v
  ```

  Expected: `ruff` reports no errors and pytest passes.

- [x] Update `README.md` with the development baseline.

  Add a short section:

  ````markdown
  ## Quality Checks

  ```bash
  ruff check src tests
  pytest -v
  ```
  ````

- [x] Commit the roadmap and baseline documentation.

  ```bash
  git add README.md pyproject.toml docs/superpowers/plans/2026-06-20-lofi-focus-tui-roadmap.md
  git commit -m "chore: establish baseline quality checks"
  ```

**Acceptance Criteria:**

- The roadmap is committed.
- Existing tests pass.
- A developer can run the documented local checks from a clean checkout.

---

## Milestone 1: Config and Generation Settings

**Status:** [x]

**Goal:** Move hard-coded defaults into validated config and model settings.

**Files:**
- Create: `src/lofi_focus_tui/config.py`
- Create: `src/lofi_focus_tui/generation/settings.py`
- Create: `config.example.toml`
- Modify: `src/lofi_focus_tui/domain.py`
- Modify: `src/lofi_focus_tui/generation/ace_step.py`
- Modify: `src/lofi_focus_tui/backend/api.py`
- Modify: `src/lofi_focus_tui/backend/session_manager.py`
- Test: `tests/test_config.py`
- Test: `tests/test_generation_settings.py`
- Test: `tests/test_ace_step_adapter.py`

**Steps:**

- [x] Add `AppConfig` in `src/lofi_focus_tui/config.py`.

  Required model shape:

  ```python
  from pathlib import Path
  from pydantic import BaseModel, Field


  class ServerConfig(BaseModel):
      host: str = "127.0.0.1"
      port: int = 8765


  class GenerationConfig(BaseModel):
      backend: str = "mock"
      output_format: str = "wav"
      inference_steps: int = Field(default=27, ge=1, le=100)
      guidance_scale: float = Field(default=15.0, ge=0.0, le=30.0)
      batch_size: int = Field(default=1, ge=1, le=8)
      chunk_seconds: int = Field(default=30, ge=10, le=600)


  class PlaybackConfig(BaseModel):
      volume: float = Field(default=0.8, ge=0.0, le=1.0)
      fade_seconds: float = Field(default=1.5, ge=0.0, le=10.0)


  class AppConfig(BaseModel):
      server: ServerConfig = Field(default_factory=ServerConfig)
      generation: GenerationConfig = Field(default_factory=GenerationConfig)
      playback: PlaybackConfig = Field(default_factory=PlaybackConfig)


  DEFAULT_CONFIG_PATHS = [
      Path("config.toml"),
      Path.home() / ".config" / "lofi-focus-tui" / "config.toml",
  ]
  ```

- [x] Implement `load_config(path: Path | None = None) -> AppConfig`.

  Behavior:

  - Load TOML from explicit path if provided and present.
  - Else load from `config.toml`.
  - Else load from `~/.config/lofi-focus-tui/config.toml`.
  - Else return defaults.
  - Override backend with `LOFI_BACKEND`.
  - Override ACE-Step checkpoint path with `ACESTEP_CHECKPOINT_PATH` once that field exists.

- [x] Add `tests/test_config.py`.

  Required tests:

  ```python
  from pathlib import Path

  from lofi_focus_tui.config import AppConfig, load_config


  def test_default_config_loads_without_file(tmp_path, monkeypatch):
      monkeypatch.chdir(tmp_path)
      config = load_config()

      assert isinstance(config, AppConfig)
      assert config.server.port == 8765
      assert config.generation.backend == "mock"


  def test_config_loads_from_explicit_toml(tmp_path):
      path = tmp_path / "config.toml"
      path.write_text(
          "[generation]\nbackend = \"ace-step\"\nchunk_seconds = 60\n",
          encoding="utf-8",
      )

      config = load_config(path)

      assert config.generation.backend == "ace-step"
      assert config.generation.chunk_seconds == 60


  def test_env_overrides_backend(tmp_path, monkeypatch):
      monkeypatch.chdir(tmp_path)
      monkeypatch.setenv("LOFI_BACKEND", "mock")

      config = load_config()

      assert config.generation.backend == "mock"
  ```

- [x] Add `GenerationSettings` in `src/lofi_focus_tui/generation/settings.py`.

  Required fields:

  ```python
  from pydantic import BaseModel, Field, field_validator

  VALID_OUTPUT_FORMATS = ("wav", "mp3", "flac", "opus", "aac")


  class GenerationSettings(BaseModel):
      output_format: str = "wav"
      inference_steps: int = Field(default=27, ge=1, le=100)
      guidance_scale: float = Field(default=15.0, ge=0.0, le=30.0)
      batch_size: int = Field(default=1, ge=1, le=8)
      seed: int = Field(default=-1, ge=-1)
      scheduler_type: str = "euler"
      cfg_type: str = "apg"
      omega_scale: float = Field(default=10.0, ge=0.0, le=20.0)

      @field_validator("output_format")
      @classmethod
      def validate_output_format(cls, value: str) -> str:
          if value not in VALID_OUTPUT_FORMATS:
              raise ValueError(f"output_format must be one of {VALID_OUTPUT_FORMATS}")
          return value
  ```

- [x] Extend `SessionRequest` in `domain.py`.

  Add optional settings:

  ```python
  generation: GenerationSettings | None = None
  seed: int | None = Field(default=None, ge=0)
  ```

  Import `GenerationSettings` from `lofi_focus_tui.generation.settings`.

- [x] Make `presets.expand_preset()` respect `request.seed`.

  If `request.seed` is provided, use it. Otherwise keep the current deterministic hash behavior.

- [x] Update `AceStepAdapter.generate()` to accept settings.

  Update the `ModelAdapter` protocol first:

  ```python
  def generate(
      self,
      blueprint: CompositionBlueprint,
      duration_seconds: int,
      settings: GenerationSettings | None = None,
  ) -> GenerationResult:
      ...
  ```

  In `AceStepAdapter`, merge defaults:

  ```python
  settings = settings or GenerationSettings(seed=blueprint.seed)
  seed = settings.seed if settings.seed >= 0 else blueprint.seed
  ```

  Use settings for `infer_step`, `guidance_scale`, `scheduler_type`, `cfg_type`, `omega_scale`, and output extension.

- [x] Update `MockModelAdapter.generate()` to match the new protocol.

  It should ignore settings except for seed if provided.

- [x] Add `config.example.toml`.

  ```toml
  [server]
  host = "127.0.0.1"
  port = 8765

  [generation]
  backend = "mock"
  output_format = "wav"
  inference_steps = 27
  guidance_scale = 15.0
  batch_size = 1
  chunk_seconds = 30

  [playback]
  volume = 0.8
  fade_seconds = 1.5
  ```

- [x] Verify tests.

  Run:

  ```bash
  pytest tests/test_config.py tests/test_generation_settings.py tests/test_ace_step_adapter.py -v
  pytest -v
  ```

  Expected: all tests pass.

- [x] Commit.

  ```bash
  git add config.example.toml src tests
  git commit -m "feat(config): add app config and generation settings"
  ```

**Acceptance Criteria:**

- No ACE-Step generation parameters are hard-coded in the adapter when a setting exists.
- `SessionRequest` can carry a seed and generation settings.
- Existing mock tests remain deterministic.
- Config defaults work without requiring a file.

---

## Milestone 2: Async Backend Task State

**Status:** [x]

**Goal:** Starting a session should not block the TUI while generation runs.

**Files:**
- Create: `src/lofi_focus_tui/backend/tasks.py`
- Modify: `src/lofi_focus_tui/domain.py`
- Modify: `src/lofi_focus_tui/backend/session_manager.py`
- Modify: `src/lofi_focus_tui/backend/api.py`
- Modify: `src/lofi_focus_tui/tui/backend_client.py`
- Test: `tests/test_backend_tasks.py`
- Test: `tests/test_backend_api.py`
- Test: `tests/test_session_manager.py`

**Steps:**

- [x] Add `BackendState` enum in `domain.py`.

  Values:

  ```python
  class BackendState(StrEnum):
      IDLE = "idle"
      PLANNING = "planning"
      GENERATING = "generating"
      READY = "ready"
      PLAYING = "playing"
      PAUSED = "paused"
      ERROR = "error"
  ```

- [x] Extend `BackendStatus`.

  Add:

  ```python
  progress: float = Field(default=0.0, ge=0.0, le=1.0)
  active_task_id: str | None = None
  output_path: str | None = None
  error: str | None = None
  ```

- [x] Create `GenerationTask` in `backend/tasks.py`.

  Required model:

  ```python
  from dataclasses import dataclass, field
  from time import monotonic


  @dataclass
  class GenerationTask:
      task_id: str
      session_id: str
      state: str = "planning"
      progress: float = 0.0
      message: str = "planning"
      error: str | None = None
      output_path: str | None = None
      started_at: float = field(default_factory=monotonic)
      updated_at: float = field(default_factory=monotonic)

      def update(self, state: str, message: str, progress: float) -> None:
          self.state = state
          self.message = message
          self.progress = max(0.0, min(1.0, progress))
          self.updated_at = monotonic()
  ```

- [x] Refactor `SessionManager.start_session()` into async task startup.

  Target behavior:

  - Validate device and request synchronously.
  - Create plan and blueprint synchronously.
  - Store a `GenerationTask`.
  - Return `BackendStatus(state="generating", progress=0.0)` quickly.
  - Run generation in a background thread using `asyncio.to_thread()` or `concurrent.futures`.

- [x] Add `SessionManager.poll()` or keep `health()` as the status source.

  `/status` should report:

  - `generating` while the worker runs.
  - `playing` once audio is loaded.
  - `error` with message if generation raises.

- [x] Update FastAPI endpoints to support async manager methods.

  `start_session` can remain `async def`; it should await the manager startup method if needed.

- [x] Add tests with a controllable fake model.

  Required behavior:

  ```python
  class SlowFakeModel:
      name = "slow-fake"

      def __init__(self):
          self.called = False

      def generate(self, blueprint, duration_seconds, settings=None):
          self.called = True
          return GenerationResult(
              audio=np.zeros(44100, dtype=np.float32),
              sample_rate=44100,
              duration_seconds=1,
              metadata={"session_id": blueprint.session_id, "backend": self.name},
          )
  ```

  Assert that starting a session first returns `generating` and a later status becomes `playing`.

- [x] Verify.

  Run:

  ```bash
  pytest tests/test_backend_tasks.py tests/test_backend_api.py tests/test_session_manager.py -v
  pytest -v
  ```

- [x] Commit.

  ```bash
  git add src/lofi_focus_tui/backend src/lofi_focus_tui/domain.py src/lofi_focus_tui/tui/backend_client.py tests
  git commit -m "feat(backend): add async session task state"
  ```

**Acceptance Criteria:**

- TUI can start a session without waiting for generation to finish.
- `/status` includes progress fields and task identity.
- Generation errors are visible through `/status`.

---

## Milestone 3: Real Playback Backend

**Status:** [ ]

**Goal:** Audio loaded by the backend should be audible and controllable.

**Files:**
- Create: `src/lofi_focus_tui/audio/player.py`
- Modify: `src/lofi_focus_tui/audio/playback.py`
- Modify: `src/lofi_focus_tui/backend/session_manager.py`
- Modify: `pyproject.toml`
- Test: `tests/test_playback.py`
- Test: `tests/test_session_manager.py`

**Steps:**

- [ ] Choose the playback dependency.

  Preferred first implementation:

  ```toml
  [project.optional-dependencies]
  playback = [
    "sounddevice>=0.4.7",
  ]
  ```

  Keep tests dependency-free by injecting a fake player.

- [ ] Create `Player` protocol in `audio/player.py`.

  ```python
  from typing import Protocol
  import numpy as np


  class Player(Protocol):
      def play(self, audio: np.ndarray, sample_rate: int, volume: float = 1.0) -> None:
          ...

      def pause(self) -> None:
          ...

      def resume(self) -> None:
          ...

      def stop(self) -> None:
          ...
  ```

- [ ] Add `NullPlayer` for tests and no-playback environments.

  It records last audio, sample rate, volume, and state.

- [ ] Add `SoundDevicePlayer`.

  Requirements:

  - Import `sounddevice` lazily inside the class so base install still works.
  - Convert mono float32 audio to a contiguous array.
  - Apply volume before playback.
  - Stop any existing playback before starting a new track.

- [ ] Refactor `PlaybackManager`.

  Constructor:

  ```python
  def __init__(self, player: Player | None = None, volume: float = 0.8) -> None:
      self.player = player or NullPlayer()
      self.volume = volume
      self.current: GenerationResult | None = None
      self.paused = False
  ```

  `load()` should call `self.player.play(result.audio, result.sample_rate, self.volume)`.

- [ ] Make `stop_session()` stop playback.

  In `SessionManager.stop_session()`, call `self.playback.stop()`.

- [ ] Add playback tests.

  Required assertions:

  - `load()` stores the current result.
  - `load()` calls `player.play`.
  - `pause()` calls `player.pause` and sets `paused`.
  - `resume()` calls `player.resume`.
  - `stop()` clears paused state and calls `player.stop`.

- [ ] Verify.

  Run:

  ```bash
  pytest tests/test_playback.py tests/test_session_manager.py -v
  pytest -v
  ```

- [ ] Commit.

  ```bash
  git add pyproject.toml src/lofi_focus_tui/audio src/lofi_focus_tui/backend/session_manager.py tests
  git commit -m "feat(audio): add local playback backend"
  ```

**Acceptance Criteria:**

- Mock generation can be heard when playback dependency is installed.
- Pause/resume/stop update both backend status and player state.
- Base tests pass without requiring a real audio device.

---

## Milestone 4: Session Controls in the TUI

**Status:** [ ]

**Goal:** Replace the hard-coded `s` action with usable controls.

**Files:**
- Modify: `src/lofi_focus_tui/tui/app.py`
- Modify: `src/lofi_focus_tui/tui/backend_client.py`
- Create: `src/lofi_focus_tui/tui/widgets.py`
- Modify: `src/lofi_focus_tui/domain.py`
- Test: `tests/test_tui_app.py`
- Test: `tests/test_backend_client.py`

**Steps:**

- [ ] Add backend client methods for pause, resume, and stop.

  Required methods:

  ```python
  async def pause_session(self) -> BackendStatus: ...
  async def resume_session(self) -> BackendStatus: ...
  async def stop_session(self) -> BackendStatus: ...
  ```

- [ ] Add periodic status polling in `LofiFocusApp`.

  On mount, call:

  ```python
  self.set_interval(1.0, self.refresh_status)
  ```

  Implement `refresh_status` as async and update the display from `/status`.

- [ ] Replace static render with a structured layout.

  Minimum widgets:

  - Status panel: state, backend, device, progress, message.
  - Session panel: preset, duration, energy, style tags.
  - Controls footer: start, pause/resume, stop.

- [ ] Add bindings.

  Required bindings:

  ```python
  BINDINGS = [
      ("s", "start_session", "Start"),
      ("space", "toggle_pause", "Pause/Resume"),
      ("x", "stop_session", "Stop"),
      ("r", "refresh_status", "Refresh"),
      ("q", "quit", "Quit"),
  ]
  ```

- [ ] Add editable defaults without building a complex wizard.

  First pass:

  - Number keys cycle energy.
  - Duration cycles through 25, 30, 45, 60, 90.
  - Preset cycles through `deep_work`, `reading`, `coding`, `wind_down`.
  - Style tags remain a comma-separated local field until a richer selector is needed.

- [ ] Add TUI tests.

  Required assertions:

  - Initial status renders.
  - Start sends the selected request, not hard-coded defaults.
  - Pause/resume calls the matching backend client method.
  - Stop calls the backend client.
  - Progress text updates after polling.

- [ ] Verify.

  Run:

  ```bash
  pytest tests/test_tui_app.py tests/test_backend_client.py -v
  pytest -v
  ```

- [ ] Commit.

  ```bash
  git add src/lofi_focus_tui/tui tests/test_tui_app.py tests/test_backend_client.py
  git commit -m "feat(tui): add configurable session controls"
  ```

**Acceptance Criteria:**

- A user can start, pause, resume, and stop from the TUI.
- The start request reflects user-selected session values.
- The TUI shows backend progress without manual refresh.

---

## Milestone 5: Output Cache and History

**Status:** [ ]

**Goal:** Persist generated audio and metadata so sessions can be replayed and varied.

**Files:**
- Create: `src/lofi_focus_tui/audio/output.py`
- Create: `src/lofi_focus_tui/history.py`
- Modify: `src/lofi_focus_tui/audio/cache.py`
- Modify: `src/lofi_focus_tui/generation/base.py`
- Modify: `src/lofi_focus_tui/backend/session_manager.py`
- Modify: `src/lofi_focus_tui/tui/app.py`
- Test: `tests/test_output_history.py`
- Test: `tests/test_session_manager.py`

**Steps:**

- [ ] Add `OutputManager`.

  Required methods:

  ```python
  class OutputManager:
      def __init__(self, base_dir: Path) -> None: ...
      def create_session_dir(self, session_id: str, preset: str) -> Path: ...
      def save_wav(self, result: GenerationResult, directory: Path, filename: str = "audio.wav") -> Path: ...
      def save_metadata(self, metadata: dict, directory: Path) -> Path: ...
  ```

- [ ] Use safe directory names.

  Slug behavior:

  - Lowercase.
  - Replace non-alphanumeric runs with `_`.
  - Trim leading/trailing `_`.
  - Limit slug to 40 characters.
  - Use `session` if slug is empty.

- [ ] Add `SessionRecord` in `history.py`.

  Fields:

  ```python
  session_id: str
  preset: str
  created_at: str
  duration_seconds: int
  audio_path: str
  metadata_path: str
  favorite: bool = False
  seed: int
  tags: list[str]
  ```

- [ ] Add `HistoryStore`.

  Use JSON lines at `cache/history.jsonl`.

  Methods:

  - `append(record: SessionRecord) -> None`
  - `list(limit: int = 20) -> list[SessionRecord]`
  - `mark_favorite(session_id: str, favorite: bool = True) -> bool`
  - `find(session_id: str) -> SessionRecord | None`

- [ ] Save output when generation completes.

  In `SessionManager`, after successful generation:

  - Create output dir.
  - Save audio.
  - Save metadata with request, plan, blueprint, settings, device, and generation metadata.
  - Append history record.
  - Put `output_path` in `BackendStatus`.

- [ ] Add TUI history panel.

  First pass can show the last 5 records with session ID prefix, preset, and favorite marker.

- [ ] Add tests.

  Required assertions:

  - Output directory is created.
  - WAV file is valid and non-empty.
  - Metadata JSON includes seed and blueprint.
  - History list returns newest records first.
  - Favorite flag persists.

- [ ] Verify.

  Run:

  ```bash
  pytest tests/test_output_history.py tests/test_session_manager.py -v
  pytest -v
  ```

- [ ] Commit.

  ```bash
  git add src/lofi_focus_tui/audio src/lofi_focus_tui/history.py src/lofi_focus_tui/backend src/lofi_focus_tui/tui tests
  git commit -m "feat(history): persist session outputs and metadata"
  ```

**Acceptance Criteria:**

- Every successful generation is saved with metadata.
- A user can see recent sessions in the TUI.
- Saved metadata is enough to regenerate a similar session.

---

## Milestone 6: Continuity and Chunk Queue

**Status:** [ ]

**Goal:** Support long sessions by generating coherent chunks with crossfades and quality checks.

**Files:**
- Create: `src/lofi_focus_tui/audio/normalization.py`
- Modify: `src/lofi_focus_tui/audio/continuity.py`
- Modify: `src/lofi_focus_tui/audio/playback.py`
- Modify: `src/lofi_focus_tui/backend/session_manager.py`
- Modify: `src/lofi_focus_tui/composition.py`
- Test: `tests/test_continuity.py`
- Test: `tests/test_normalization.py`
- Test: `tests/test_session_manager.py`

**Steps:**

- [ ] Add audio quality utilities.

  Required functions:

  ```python
  def rms(audio: np.ndarray) -> float: ...
  def peak(audio: np.ndarray) -> float: ...
  def is_silent(audio: np.ndarray, threshold: float = 1e-4) -> bool: ...
  def is_clipped(audio: np.ndarray, threshold: float = 0.99) -> bool: ...
  def apply_fade(audio: np.ndarray, sample_rate: int, fade_seconds: float) -> np.ndarray: ...
  def crossfade(left: np.ndarray, right: np.ndarray, sample_rate: int, seconds: float) -> np.ndarray: ...
  ```

- [ ] Expand `ContinuityReport`.

  Add:

  ```python
  left_rms: float
  right_rms: float
  boundary_delta: float
  warnings: list[str]
  ```

- [ ] Strengthen `analyze_boundary()`.

  Reject when:

  - Loudness jump exceeds 0.20 RMS.
  - Boundary sample delta exceeds 0.35.
  - Either side is silent.
  - Either side is clipped.

- [ ] Add chunk planning to composition.

  Add a function:

  ```python
  def create_chunk_blueprint(plan: SessionPlan, chunk_index: int, chunk_count: int) -> CompositionBlueprint:
      ...
  ```

  It must preserve seed, tempo, key center, motif, and boundary constraints while allowing section-specific texture changes.

- [ ] Generate session chunks.

  In `SessionManager`, when `duration_minutes * 60` exceeds `chunk_seconds`, generate multiple chunks:

  - Queue first chunk.
  - Start playback when first chunk is ready.
  - Generate next chunk while current chunk plays.
  - Crossfade accepted chunks.
  - If continuity fails, retry with the same seed plus chunk index offset once.

- [ ] Add status fields for chunk progress.

  Add to `BackendStatus`:

  ```python
  chunk_index: int = 0
  chunk_count: int = 0
  ```

- [ ] Add tests.

  Required assertions:

  - Crossfade output length is `len(left) + len(right) - fade_samples`.
  - Silent chunks fail continuity.
  - Clipped chunks fail continuity.
  - Session manager calculates chunk count correctly.
  - Chunk blueprints preserve key and tempo constraints.

- [ ] Verify.

  Run:

  ```bash
  pytest tests/test_continuity.py tests/test_normalization.py tests/test_session_manager.py -v
  pytest -v
  ```

- [ ] Commit.

  ```bash
  git add src/lofi_focus_tui/audio src/lofi_focus_tui/composition.py src/lofi_focus_tui/backend src/lofi_focus_tui/domain.py tests
  git commit -m "feat(audio): add chunk queue and continuity gates"
  ```

**Acceptance Criteria:**

- Long sessions are generated in chunks.
- Chunk transitions avoid obvious clicks, silence, clipping, and loudness jumps.
- Status reports chunk progress.

---

## Milestone 7: ACE-Step HTTP and Cloud Execution

**Status:** [ ]

**Goal:** Support embedded ACE-Step, local ACE-Step API, and optional cloud GPU execution.

**Files:**
- Create: `src/lofi_focus_tui/generation/http_ace_step.py`
- Create: `src/lofi_focus_tui/generation/runpod.py`
- Modify: `src/lofi_focus_tui/generation/ace_step.py`
- Modify: `src/lofi_focus_tui/generation/base.py`
- Modify: `src/lofi_focus_tui/config.py`
- Modify: `src/lofi_focus_tui/devices.py`
- Modify: `src/lofi_focus_tui/backend/api.py`
- Test: `tests/test_http_ace_step.py`
- Test: `tests/test_devices.py`

**Steps:**

- [ ] Add config sections.

  In `config.py`:

  ```python
  class AceStepHttpConfig(BaseModel):
      base_url: str = "http://127.0.0.1:8001"
      api_key: str = ""
      timeout_seconds: float = 1800.0


  class RunPodConfig(BaseModel):
      api_key: str = ""
      gpu_type: str = "NVIDIA GeForce RTX 4090"
      template_id: str = ""
      volume_id: str = ""
      auto_destroy: bool = True
  ```

- [ ] Create `AceStepHttpAdapter`.

  Required behavior:

  - Health check `GET /health`.
  - Submit `POST /release_task`.
  - Poll `POST /query_result`.
  - Download `GET /v1/audio?path=...`.
  - Convert downloaded WAV into `GenerationResult`.

- [ ] Add Pydantic response models.

  Models:

  - `TaskSubmission`
  - `AudioResult`
  - `TaskResult`

  Parse the ACE-Step double-encoded `result` field robustly.

- [ ] Add adapter selection.

  In backend startup, choose:

  - `mock` -> `MockModelAdapter`
  - `ace-step` -> `AceStepAdapter`
  - `ace-step-http` -> `AceStepHttpAdapter`
  - `runpod` -> `RunPodAceStepAdapter`

- [ ] Add RunPod support behind optional dependency.

  Add:

  ```toml
  [project.optional-dependencies]
  runpod = [
    "runpod>=1.7",
  ]
  ```

  Import `runpod` lazily.

- [ ] Add GPU diagnostics.

  Extend `devices.py` with optional NVIDIA VRAM detection using `nvidia-smi`.

  Required behavior:

  - Return no GPU if `nvidia-smi` is missing.
  - Estimate VRAM for duration and batch size.
  - Warn rather than fail when estimate is too high.

- [ ] Add tests with mocked HTTP transport.

  Required assertions:

  - Health check success and failure.
  - Submit task unwraps response envelope.
  - Poll parses succeeded, running, and failed states.
  - Download writes audio bytes.
  - Adapter returns `GenerationResult`.

- [ ] Verify.

  Run:

  ```bash
  pytest tests/test_http_ace_step.py tests/test_devices.py -v
  pytest -v
  ```

- [ ] Commit.

  ```bash
  git add pyproject.toml src/lofi_focus_tui/generation src/lofi_focus_tui/config.py src/lofi_focus_tui/devices.py tests
  git commit -m "feat(generation): add remote ace-step clients"
  ```

**Acceptance Criteria:**

- Users can choose embedded, local HTTP, or remote execution from config.
- Remote clients expose the same `ModelAdapter` behavior as local adapters.
- RunPod code is optional and does not affect base install.

---

## Milestone 8: Quality, Docs, and Release Polish

**Status:** [ ]

**Goal:** Make the app understandable, diagnosable, and releasable.

**Files:**
- Create: `src/lofi_focus_tui/diagnostics.py`
- Modify: `src/lofi_focus_tui/cli.py`
- Modify: `README.md`
- Create: `docs/usage.md`
- Create: `docs/configuration.md`
- Create: `docs/ace-step.md`
- Create: `.github/workflows/ci.yml`
- Test: `tests/test_diagnostics.py`

**Steps:**

- [ ] Add `lofi doctor`.

  Diagnostics checks:

  - Python version.
  - Config file load.
  - Backend port reachability.
  - Optional ACE-Step import.
  - Optional `sounddevice` import.
  - Cache directory writable.
  - Output directory writable.
  - GPU/device summary.

- [ ] Update CLI.

  Commands:

  - `lofi`: run Textual TUI.
  - `lofi-backend`: run FastAPI backend.
  - `lofi-doctor`: run diagnostics.

- [ ] Add docs.

  `docs/usage.md` must cover:

  - Starting backend.
  - Starting TUI.
  - Starting a mock session.
  - Starting an ACE-Step session.
  - Pause/resume/stop.
  - Replaying history.

  `docs/configuration.md` must cover every field in `config.example.toml`.

  `docs/ace-step.md` must cover embedded, HTTP, and RunPod modes.

- [ ] Add CI.

  `.github/workflows/ci.yml`:

  ```yaml
  name: CI

  on:
    push:
    pull_request:

  jobs:
    test:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v5
          with:
            python-version: "3.10"
        - run: python -m pip install -e ".[dev]"
        - run: ruff check src tests
        - run: pytest -v
  ```

- [ ] Add README quickstart.

  Keep it short:

  - Install.
  - Run backend.
  - Run TUI.
  - Run doctor.
  - Where outputs live.

- [ ] Verify.

  Run:

  ```bash
  ruff check src tests
  pytest -v
  ```

- [ ] Commit.

  ```bash
  git add README.md docs .github pyproject.toml src/lofi_focus_tui/cli.py src/lofi_focus_tui/diagnostics.py tests
  git commit -m "docs: add usage guide and release checklist"
  ```

**Acceptance Criteria:**

- A new user can run mock mode from README alone.
- `lofi-doctor` gives actionable output.
- CI runs lint and tests.

---

## Backlog After v0.2

These ideas are useful but should wait until the milestones above are stable:

- Ambient layer mixer: rain, vinyl, cafe room, tape hiss, brown noise.
- Live steering commands: calmer, more drums, less melody, darker, brighter, cooldown now.
- Prompt preview panel with final ACE-Step prompt.
- Quality badges: loopable, quiet, stable tempo, no clipping, non-silent.
- Session stats: total focus time, most-used presets, favorite seeds.
- Theme support for the TUI.
- Export bundled session packs.

## Risk Register

| Risk | Mitigation |
| --- | --- |
| ACE-Step generation blocks the backend | Move generation into background worker in Milestone 2 before adding remote execution |
| Audio playback breaks tests on CI | Keep concrete player injectable and use `NullPlayer` in tests |
| TUI becomes too large | Move reusable widgets to `src/lofi_focus_tui/tui/widgets.py` once layout grows |
| Long sessions create abrupt transitions | Implement chunk continuity gates before infinite/long-session UX |
| Remote GPU code adds mandatory dependency | Keep RunPod behind optional dependency and lazy imports |
| Hard-coded prompt settings reduce reproducibility | Persist settings, seed, plan, and blueprint in metadata |

## Execution Order

Implement in milestone order. Do not start Milestone 7 before Milestone 2 is complete, because remote generation needs task progress and error reporting. Do not start Milestone 6 before Milestone 3 is complete, because chunking depends on playback behavior. Milestone 8 can start after Milestone 4 if documentation is needed earlier, but CI should wait until lint tooling is settled.

## Self-Review Notes

- Spec coverage: the document covers config, generation settings, async backend, playback, TUI controls, history, continuity, remote generation, diagnostics, docs, and CI.
- Placeholder scan: no open-ended implementation markers are intentionally left; each milestone has concrete files, tests, verification commands, and commit boundaries.
- Type consistency: `GenerationSettings`, `BackendStatus`, `PlaybackManager`, `ModelAdapter`, `OutputManager`, and task-state names are used consistently across milestones.
