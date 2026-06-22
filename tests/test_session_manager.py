import json
from pathlib import Path
from threading import Event, Lock

import numpy as np

from lofi_focus_tui.audio.output import OutputManager
from lofi_focus_tui.backend.session_manager import SessionManager
from lofi_focus_tui.domain import BackendState, EnergyLevel, SessionRequest
from lofi_focus_tui.generation.base import GenerationResult
from lofi_focus_tui.generation.mock import MockModelAdapter
from lofi_focus_tui.generation.settings import GenerationSettings
from lofi_focus_tui.history import HistoryStore


def make_request(generation=None):
    return SessionRequest(
        preset="deep_work",
        duration_minutes=30,
        energy=EnergyLevel.STEADY,
        style_tags=["lofi"],
        avoid_tags=["vocals"],
        generation=generation,
    )


class BlockingRecordingModel:
    name = "blocking-recording"

    def __init__(self) -> None:
        self.started = Event()
        self.release = Event()
        self.settings = None
        self.duration_seconds = None

    def generate(self, blueprint, duration_seconds, settings=None):
        self.started.set()
        self.release.wait(timeout=1.0)
        self.settings = settings
        self.duration_seconds = duration_seconds
        return GenerationResult(
            audio=np.zeros(duration_seconds * 44100, dtype=np.float32),
            sample_rate=44100,
            duration_seconds=duration_seconds,
            metadata={
                "session_id": blueprint.session_id,
                "backend": self.name,
                "output_path": f"{blueprint.session_id}.wav",
            },
        )


def test_start_session_returns_generating_before_generation_finishes():
    model = BlockingRecordingModel()
    manager = SessionManager(model=model)
    status = manager.start_session(
        make_request(),
    )

    assert status.state == BackendState.GENERATING
    assert status.active_session_id is not None
    assert status.active_task_id is not None
    assert status.progress == 0.0
    assert status.backend == "blocking-recording"

    model.release.set()
    final_status = manager.wait_for_active_task()

    assert final_status.state == BackendState.PLAYING
    assert final_status.progress == 1.0
    assert final_status.active_task_id == status.active_task_id
    assert final_status.output_path is not None
    assert final_status.output_path.endswith(".wav")


def test_start_session_eventually_reports_playing_status():
    manager = SessionManager(model=MockModelAdapter())
    status = manager.start_session(make_request())
    final_status = manager.wait_for_active_task()

    assert status.state == "generating"
    assert final_status.state == "playing"
    assert final_status.active_session_id is not None
    assert final_status.backend == "mock"


class RecordingModel:
    name = "recording"

    def __init__(self):
        self.settings = None
        self.duration_seconds = None

    def generate(self, blueprint, duration_seconds, settings=None):
        self.settings = settings
        self.duration_seconds = duration_seconds
        return GenerationResult(
            audio=np.zeros(duration_seconds * 44100, dtype=np.float32),
            sample_rate=44100,
            duration_seconds=duration_seconds,
            metadata={"session_id": blueprint.session_id, "backend": self.name},
        )


class RecordingPlayback:
    def __init__(self) -> None:
        self.loaded = None
        self.paused = False
        self.resumed = False
        self.stopped = False

    def load(self, result):
        self.loaded = result

    def pause(self) -> bool:
        self.paused = True
        return True

    def resume(self) -> bool:
        self.resumed = True
        return True

    def stop(self) -> None:
        self.stopped = True


class SequencedBlockingModel:
    name = "sequenced-blocking"

    def __init__(self) -> None:
        self._lock = Lock()
        self.started = [Event(), Event()]
        self.release = [Event(), Event()]
        self.call_count = 0

    def generate(self, blueprint, duration_seconds, settings=None):
        with self._lock:
            call_index = self.call_count
            self.call_count += 1
        self.started[call_index].set()
        self.release[call_index].wait(timeout=1.0)
        return GenerationResult(
            audio=np.zeros(duration_seconds * 44100, dtype=np.float32),
            sample_rate=44100,
            duration_seconds=duration_seconds,
            metadata={"session_id": blueprint.session_id, "backend": self.name},
        )


class FirstQuickSecondBlockingModel:
    name = "first-quick-second-blocking"

    def __init__(self) -> None:
        self._lock = Lock()
        self.call_count = 0
        self.second_started = Event()
        self.release_second = Event()

    def generate(self, blueprint, duration_seconds, settings=None):
        with self._lock:
            self.call_count += 1
            call_count = self.call_count
        if call_count == 2:
            self.second_started.set()
            self.release_second.wait(timeout=1.0)
        return GenerationResult(
            audio=np.zeros(duration_seconds * 44100, dtype=np.float32),
            sample_rate=44100,
            duration_seconds=duration_seconds,
            metadata={"session_id": blueprint.session_id, "backend": self.name},
        )


class ChunkRecordingModel:
    name = "chunk-recording"

    def __init__(self) -> None:
        self.calls = []

    def generate(self, blueprint, duration_seconds, settings=None):
        self.calls.append((blueprint, duration_seconds, settings))
        value = 0.05 + (len(self.calls) * 0.001)
        return GenerationResult(
            audio=np.full(duration_seconds * 10, value, dtype=np.float32),
            sample_rate=10,
            duration_seconds=duration_seconds,
            metadata={
                "session_id": blueprint.session_id,
                "backend": self.name,
                "chunk": str(len(self.calls)),
            },
        )


class BoundaryRetryModel:
    name = "boundary-retry"

    def __init__(self) -> None:
        self.blueprints = []
        self.values = [0.05, 0.9, 0.052]

    def generate(self, blueprint, duration_seconds, settings=None):
        self.blueprints.append(blueprint)
        value = self.values[len(self.blueprints) - 1]
        return GenerationResult(
            audio=np.full(duration_seconds * 10, value, dtype=np.float32),
            sample_rate=10,
            duration_seconds=duration_seconds,
            metadata={"session_id": blueprint.session_id, "backend": self.name},
        )


def test_start_session_passes_generation_settings_to_model():
    model = RecordingModel()
    manager = SessionManager(model=model)
    settings = GenerationSettings(inference_steps=12, seed=99)

    manager.start_session(make_request(generation=settings))
    manager.wait_for_active_task()

    assert model.settings == settings


def test_session_manager_uses_injected_playback_manager():
    playback = RecordingPlayback()
    manager = SessionManager(model=MockModelAdapter(), playback=playback)

    manager.start_session(make_request())
    final_status = manager.wait_for_active_task()
    manager.pause_session()
    manager.resume_session()
    manager.stop_session()

    assert final_status.state == BackendState.PLAYING
    assert playback.loaded is not None
    assert playback.paused is True
    assert playback.resumed is True
    assert playback.stopped is True


def test_stop_session_keeps_stopped_status_after_generation_finishes():
    model = BlockingRecordingModel()
    manager = SessionManager(model=model)

    manager.start_session(make_request())
    assert model.started.wait(timeout=1.0)
    stopped_status = manager.stop_session()
    model.release.set()
    final_status = manager.wait_for_active_task()

    assert stopped_status.state == BackendState.IDLE
    assert final_status.state == BackendState.IDLE
    assert final_status.message == "stopped"
    assert manager.playback.current is None


def test_stop_session_clears_loaded_playback():
    manager = SessionManager(model=MockModelAdapter())

    manager.start_session(make_request())
    manager.wait_for_active_task()
    assert manager.playback.current is not None

    status = manager.stop_session()

    assert status.state == BackendState.IDLE
    assert manager.playback.current is None
    assert manager.playback.paused is False


def test_starting_new_session_stops_existing_playback():
    model = FirstQuickSecondBlockingModel()
    manager = SessionManager(model=model)

    manager.start_session(make_request())
    first_status = manager.wait_for_active_task()
    assert first_status.state == BackendState.PLAYING
    assert manager.playback.current is not None

    second_status = manager.start_session(make_request())

    assert second_status.state == BackendState.GENERATING
    assert manager.playback.current is None

    model.release_second.set()
    final_status = manager.wait_for_active_task()
    assert final_status.state == BackendState.PLAYING


def test_resume_without_loaded_audio_does_not_report_playing():
    manager = SessionManager(model=MockModelAdapter())

    status = manager.resume_session()

    assert status.state == BackendState.IDLE
    assert status.message == "ready"


def test_new_session_ignores_previous_task_completion():
    model = SequencedBlockingModel()
    manager = SessionManager(model=model)

    first_status = manager.start_session(make_request())
    assert model.started[0].wait(timeout=1.0)
    second_status = manager.start_session(make_request())

    model.release[0].set()
    assert model.started[1].wait(timeout=1.0)

    current_status = manager.health()
    assert current_status.active_task_id == second_status.active_task_id
    assert current_status.active_task_id != first_status.active_task_id
    assert current_status.state == BackendState.GENERATING

    model.release[1].set()
    final_status = manager.wait_for_active_task()

    assert final_status.state == BackendState.PLAYING
    assert final_status.active_task_id == second_status.active_task_id


def test_generation_status_uses_legacy_path_metadata_as_output_path():
    class PathMetadataModel:
        name = "path-metadata"

        def generate(self, blueprint, duration_seconds, settings=None):
            return GenerationResult(
                audio=np.zeros(duration_seconds * 44100, dtype=np.float32),
                sample_rate=44100,
                duration_seconds=duration_seconds,
                metadata={
                    "session_id": blueprint.session_id,
                    "backend": self.name,
                    "path": "rendered.wav",
                },
            )

    manager = SessionManager(model=PathMetadataModel())

    manager.start_session(make_request())
    final_status = manager.wait_for_active_task()

    assert final_status.output_path == "rendered.wav"


def test_successful_generation_persists_output_and_history(tmp_path):
    output_manager = OutputManager(tmp_path / "outputs")
    history_store = HistoryStore(tmp_path / "history.jsonl")
    manager = SessionManager(
        model=MockModelAdapter(),
        output_manager=output_manager,
        history_store=history_store,
        render_seconds_limit=1,
    )

    manager.start_session(make_request())
    final_status = manager.wait_for_active_task()

    assert final_status.state == BackendState.PLAYING
    assert final_status.output_path is not None
    audio_path = Path(final_status.output_path)
    assert audio_path.exists()
    record = history_store.list(limit=1)[0]
    assert record.audio_path == str(audio_path)
    assert record.preset == "deep_work"
    assert final_status.recent_sessions == [f"{record.session_id[:8]} deep_work"]
    metadata = json.loads(Path(record.metadata_path).read_text(encoding="utf-8"))
    assert metadata["request"]["preset"] == "deep_work"
    assert metadata["blueprint"]["session_id"] == record.session_id
    assert metadata["seed"] == record.seed


def test_start_session_uses_generation_defaults_when_request_omits_settings():
    model = RecordingModel()
    defaults = GenerationSettings(inference_steps=18, seed=77)
    manager = SessionManager(model=model, generation_defaults=defaults)

    manager.start_session(make_request())
    manager.wait_for_active_task()

    assert model.settings == defaults


def test_start_session_request_generation_overrides_defaults():
    model = RecordingModel()
    defaults = GenerationSettings(inference_steps=18, seed=77)
    request_settings = GenerationSettings(inference_steps=12, seed=99)
    manager = SessionManager(model=model, generation_defaults=defaults)

    manager.start_session(make_request(generation=request_settings))
    manager.wait_for_active_task()

    assert model.settings == request_settings


def test_start_session_uses_configured_render_seconds_limit():
    model = RecordingModel()
    manager = SessionManager(model=model, render_seconds_limit=12)

    manager.start_session(make_request())
    manager.wait_for_active_task()

    assert model.duration_seconds == 12


def test_chunked_generation_splits_long_session_and_reports_progress():
    model = ChunkRecordingModel()
    playback = RecordingPlayback()
    manager = SessionManager(model=model, playback=playback, chunk_seconds=60)

    status = manager.start_session(make_request().model_copy(update={"duration_minutes": 5}))
    final_status = manager.wait_for_active_task()

    assert status.chunk_count == 5
    assert status.chunk_index == 0
    assert final_status.state == BackendState.PLAYING
    assert final_status.chunk_count == 5
    assert final_status.chunk_index == 5
    assert [duration for _blueprint, duration, _settings in model.calls] == [60, 60, 60, 60, 60]
    assert "chunk 1 of 5" in " ".join(model.calls[0][0].texture_layers)
    assert "chunk 5 of 5" in " ".join(model.calls[-1][0].texture_layers)
    assert playback.loaded.duration_seconds == 300
    assert playback.loaded.audio.shape == (2960,)


def test_chunked_generation_retries_failed_boundary_once():
    model = BoundaryRetryModel()
    manager = SessionManager(model=model, playback=RecordingPlayback(), chunk_seconds=150)

    manager.start_session(make_request().model_copy(update={"duration_minutes": 5}))
    final_status = manager.wait_for_active_task()

    assert final_status.state == BackendState.PLAYING
    assert final_status.chunk_count == 2
    assert final_status.chunk_index == 2
    assert len(model.blueprints) == 3
    assert model.blueprints[1].seed == model.blueprints[0].seed
    assert model.blueprints[2].seed == model.blueprints[0].seed + 2


class FailingModel:
    name = "failing"

    def generate(self, blueprint, duration_seconds, settings=None):
        raise RuntimeError("generation exploded")


def test_generation_error_updates_backend_status():
    manager = SessionManager(model=FailingModel())

    status = manager.start_session(make_request())
    final_status = manager.wait_for_active_task()

    assert status.state == BackendState.GENERATING
    assert final_status.state == BackendState.ERROR
    assert final_status.error == "generation exploded"
    assert final_status.message == "generation failed"
