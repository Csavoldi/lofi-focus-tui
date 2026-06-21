from threading import Event, Lock

import numpy as np

from lofi_focus_tui.backend.session_manager import SessionManager
from lofi_focus_tui.domain import BackendState, EnergyLevel, SessionRequest
from lofi_focus_tui.generation.base import GenerationResult
from lofi_focus_tui.generation.mock import MockModelAdapter
from lofi_focus_tui.generation.settings import GenerationSettings


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


def test_start_session_passes_generation_settings_to_model():
    model = RecordingModel()
    manager = SessionManager(model=model)
    settings = GenerationSettings(inference_steps=12, seed=99)

    manager.start_session(make_request(generation=settings))
    manager.wait_for_active_task()

    assert model.settings == settings


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
