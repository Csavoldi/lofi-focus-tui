import json
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from threading import Event, Lock, Thread

import numpy as np
import pytest

from lofi_focus_tui import composition
from lofi_focus_tui.audio.output import OutputManager
from lofi_focus_tui.backend.session_manager import SessionManager
from lofi_focus_tui.domain import BackendState, EnergyLevel, SessionRequest
from lofi_focus_tui.generation.base import GenerationCancelledError, GenerationResult
from lofi_focus_tui.generation.mock import MockModelAdapter
from lofi_focus_tui.generation.settings import GenerationSettings
from lofi_focus_tui.history import HistoryStore


def make_request(generation=None):
    return SessionRequest(
        focus="deep_work",
        preset="classic_lofi",
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


class CooperativeShutdownModel:
    name = "cooperative-shutdown"

    def __init__(self) -> None:
        self.started = Event()
        self.cancel_seen = Event()
        self.closed = Event()
        self.close_calls = 0

    def generate(self, blueprint, duration_seconds, settings=None, cancel_event=None):
        self.started.set()
        assert cancel_event is not None
        cancel_event.wait(timeout=2.5)
        self.cancel_seen.set()
        raise GenerationCancelledError("generation cancelled")

    def close(self) -> None:
        self.close_calls += 1
        self.closed.set()


class DelayedShutdownModel:
    name = "delayed-shutdown"

    def __init__(self) -> None:
        self.started = Event()
        self.release = Event()
        self.closed = Event()

    def generate(self, blueprint, duration_seconds, settings=None):
        self.started.set()
        self.release.wait()
        return GenerationResult(
            audio=np.zeros(duration_seconds * 44100, dtype=np.float32),
            sample_rate=44100,
            duration_seconds=duration_seconds,
            metadata={"session_id": blueprint.session_id, "backend": self.name},
        )

    def close(self) -> None:
        self.closed.set()


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


class CancelAwareChunkModel:
    name = "cancel-aware-chunk"

    def __init__(self) -> None:
        self.calls = 0
        self.started_second = Event()
        self.release_second = Event()

    def generate(self, blueprint, duration_seconds, settings=None, cancel_event=None):
        self.calls += 1
        if self.calls == 2:
            self.started_second.set()
            self.release_second.wait(timeout=1.0)
        return GenerationResult(
            audio=np.full(duration_seconds * 10, 0.05, dtype=np.float32),
            sample_rate=10,
            duration_seconds=duration_seconds,
            metadata={"session_id": blueprint.session_id, "backend": self.name},
        )


class CancelAwareSequentialModel:
    name = "cancel-aware-sequential"

    def __init__(self) -> None:
        self._lock = Lock()
        self.started = [Event(), Event()]
        self.release = [Event(), Event()]
        self.cancel_seen = []
        self.call_count = 0

    def generate(self, blueprint, duration_seconds, settings=None, cancel_event=None):
        with self._lock:
            call_index = self.call_count
            self.call_count += 1
        self.started[call_index].set()
        self.release[call_index].wait(timeout=1.0)
        cancelled = cancel_event is not None and cancel_event.is_set()
        self.cancel_seen.append(cancelled)
        if cancelled:
            raise GenerationCancelledError("generation cancelled")
        return GenerationResult(
            audio=np.zeros(duration_seconds * 44100, dtype=np.float32),
            sample_rate=44100,
            duration_seconds=duration_seconds,
            metadata={"session_id": blueprint.session_id, "backend": self.name},
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


class OrdinaryWarningModel:
    name = "ordinary-warning"

    def __init__(self) -> None:
        self.blueprints = []
        self.values = [0.05, 0.30, 0.30]

    def generate(self, blueprint, duration_seconds, settings=None):
        self.blueprints.append(blueprint)
        value = self.values[len(self.blueprints) - 1]
        return GenerationResult(
            audio=np.full(duration_seconds * 10, value, dtype=np.float32),
            sample_rate=10,
            duration_seconds=duration_seconds,
            metadata={"session_id": blueprint.session_id, "backend": self.name},
        )


class AlwaysBadBoundaryModel:
    name = "always-bad-boundary"

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, blueprint, duration_seconds, settings=None):
        self.calls += 1
        value = 0.05 if self.calls == 1 else 0.90
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

    request = make_request().model_copy(update={"focus": "coding", "preset": "ambient_tape"})
    manager.start_session(request)
    final_status = manager.wait_for_active_task()

    assert final_status.state == BackendState.PLAYING
    assert final_status.output_path is not None
    audio_path = Path(final_status.output_path)
    assert audio_path.exists()
    record = history_store.list(limit=1)[0]
    assert record.audio_path == str(audio_path)
    assert record.focus == "coding"
    assert record.preset == "ambient_tape"
    assert final_status.recent_sessions == [f"{record.session_id[:8]} ambient_tape"]
    metadata = json.loads(Path(record.metadata_path).read_text(encoding="utf-8"))
    assert metadata["request"]["focus"] == record.focus == "coding"
    assert metadata["request"]["preset"] == record.preset == "ambient_tape"
    assert metadata["plan"]["focus"] == record.focus
    assert metadata["plan"]["preset"] == record.preset
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
    assert playback.loaded.duration_seconds == 296.0
    assert playback.loaded.audio.shape == (2960,)


def test_chunked_generation_reuses_one_prompt_blueprint_lineage(monkeypatch):
    base_calls = []
    base_blueprints = []
    chunk_calls = []

    def record_base(plan):
        base_calls.append((plan,))
        blueprint = composition.create_blueprint(plan)
        base_blueprints.append(blueprint)
        return blueprint

    def record_chunk(plan, chunk_index, chunk_count, **kwargs):
        chunk_calls.append((plan, chunk_index, chunk_count, kwargs))
        return composition.create_chunk_blueprint(plan, chunk_index, chunk_count, **kwargs)

    monkeypatch.setattr(
        "lofi_focus_tui.backend.session_manager.create_blueprint", record_base
    )
    monkeypatch.setattr(
        "lofi_focus_tui.backend.session_manager.create_chunk_blueprint", record_chunk
    )

    model = OrdinaryWarningModel()
    manager = SessionManager(model=model, playback=RecordingPlayback(), chunk_seconds=100)
    request = make_request().model_copy(
        update={
            "duration_minutes": 5,
            "energy": EnergyLevel.HIGH,
            "prompt": "late-night rainy room",
            "vocal_mode": "vocals",
        }
    )

    manager.start_session(request)
    manager.wait_for_active_task()

    plan = base_calls[0][0]
    blueprint = base_blueprints[0]
    assert len(base_calls) == 1
    assert len(chunk_calls) == 3
    assert base_calls[0][0] is chunk_calls[0][0]
    assert all(call[0] is base_calls[0][0] for call in chunk_calls)
    assert all(call[3]["base_blueprint"] is blueprint for call in chunk_calls)
    assert chunk_calls == [
        (plan, 0, 3, {"continuation_constraints": [], "base_blueprint": blueprint}),
        (
            plan,
            1,
            3,
            {"continuation_constraints": [], "base_blueprint": blueprint},
        ),
        (
            plan,
            2,
            3,
            {
                "continuation_constraints": [
                    "match the previous chunk's loudness at the transition"
                ],
                "base_blueprint": blueprint,
            },
        ),
    ]
    assert all(chunk.prompt == "late-night rainy room" for chunk in model.blueprints)
    assert all(chunk.energy == EnergyLevel.HIGH for chunk in model.blueprints)
    assert all(chunk.vocal_mode == "vocals" for chunk in model.blueprints)
    assert model.blueprints[2].continuation_constraints == [
        "match the previous chunk's loudness at the transition"
    ]


def test_five_minute_session_uses_one_five_minute_chunk():
    model = ChunkRecordingModel()
    manager = SessionManager(model=model, playback=RecordingPlayback(), chunk_seconds=600)

    manager.start_session(make_request().model_copy(update={"duration_minutes": 5}))
    manager.wait_for_active_task()

    assert [duration for _blueprint, duration, _settings in model.calls] == [300]


def test_longer_session_uses_ten_minute_chunks_and_final_remainder():
    model = ChunkRecordingModel()
    manager = SessionManager(model=model, playback=RecordingPlayback(), chunk_seconds=600)

    manager.start_session(make_request().model_copy(update={"duration_minutes": 11}))
    manager.wait_for_active_task()

    assert [duration for _blueprint, duration, _settings in model.calls] == [600, 60]


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
    assert "avoid a sharp transient at the transition" in (
        model.blueprints[2].continuation_constraints
    )


def test_ordinary_boundary_warning_updates_next_prompt_without_retrying():
    model = OrdinaryWarningModel()
    manager = SessionManager(model=model, playback=RecordingPlayback(), chunk_seconds=100)

    manager.start_session(make_request().model_copy(update={"duration_minutes": 5}))
    final_status = manager.wait_for_active_task()

    assert final_status.state == BackendState.PLAYING
    assert len(model.blueprints) == 3
    assert model.blueprints[2].continuation_constraints == [
        "match the previous chunk's loudness at the transition"
    ]


def test_chunk_metadata_records_profiles_boundaries_and_handoffs():
    model = OrdinaryWarningModel()
    playback = RecordingPlayback()
    manager = SessionManager(model=model, playback=playback, chunk_seconds=100)

    manager.start_session(make_request().model_copy(update={"duration_minutes": 5}))
    manager.wait_for_active_task()

    chunks = playback.loaded.metadata["chunks"]
    assert len(chunks) == 3
    assert chunks[0]["profile"]["sample_rate"] == 10
    assert chunks[1]["boundary"]["warnings"] == ["loudness jump"]
    assert chunks[1]["handoff"] == [
        "match the previous chunk's loudness at the transition"
    ]
    assert chunks[1]["retry_count"] == 0


def test_failed_severe_retry_reports_continuity_error():
    model = AlwaysBadBoundaryModel()
    manager = SessionManager(model=model, playback=RecordingPlayback(), chunk_seconds=150)

    manager.start_session(make_request().model_copy(update={"duration_minutes": 5}))
    final_status = manager.wait_for_active_task()

    assert final_status.state == BackendState.ERROR
    assert "chunk continuity failed" in final_status.error
    assert model.calls == 3


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


def test_stop_session_cancels_chunked_generation_before_later_chunks_complete():
    model = CancelAwareChunkModel()
    manager = SessionManager(model=model, chunk_seconds=60)

    manager.start_session(make_request().model_copy(update={"duration_minutes": 3}))
    assert model.started_second.wait(timeout=1.0)
    stopped_status = manager.stop_session()
    model.release_second.set()
    final_status = manager.wait_for_active_task()

    assert stopped_status.state == BackendState.IDLE
    assert final_status.state == BackendState.IDLE
    assert model.calls == 2


def test_starting_new_session_cancels_previous_cancellable_task():
    model = CancelAwareSequentialModel()
    manager = SessionManager(model=model)

    manager.start_session(make_request())
    assert model.started[0].wait(timeout=1.0)
    second_status = manager.start_session(make_request())
    model.release[0].set()
    assert model.started[1].wait(timeout=1.0)
    model.release[1].set()
    final_status = manager.wait_for_active_task()

    assert model.cancel_seen[0] is True
    assert second_status.active_task_id == final_status.active_task_id
    assert final_status.state == BackendState.PLAYING


def test_session_status_reports_disabled_playback_mode():
    manager = SessionManager(model=MockModelAdapter())

    manager.start_session(make_request())
    final_status = manager.wait_for_active_task()

    assert final_status.playback == "disabled"
    assert final_status.message == "generated; playback disabled"


def test_shutdown_cancels_active_task_stops_playback_and_waits_at_most_two_seconds():
    model = DelayedShutdownModel()
    playback = RecordingPlayback()
    manager = SessionManager(model=model, playback=playback)

    status = manager.start_session(make_request())
    assert model.started.wait(timeout=1.0)

    started_at = time.monotonic()
    manager.shutdown()
    elapsed = time.monotonic() - started_at

    assert elapsed < 2.2
    assert manager._tasks[status.active_task_id].cancel_event.is_set()
    assert model.closed.is_set() is False
    assert playback.stopped is True

    model.release.set()
    manager.wait_for_active_task(timeout=1.0)
    assert model.closed.is_set()


def test_repeated_shutdown_calls_are_noops():
    model = CooperativeShutdownModel()
    manager = SessionManager(model=model)

    manager.start_session(make_request())
    assert model.started.wait(timeout=1.0)
    manager.shutdown()
    manager.shutdown()

    assert model.close_calls == 1


def test_new_sessions_controls_and_export_raise_after_shutdown(tmp_path):
    manager = SessionManager(model=RecordingModel())
    manager.shutdown()

    operations = (
        lambda: manager.start_session(make_request()),
        manager.pause_session,
        manager.resume_session,
        lambda: manager.adjust_volume(0.1),
        lambda: manager.seek_playback(1.0),
        manager.restart_playback,
        manager.stop_session,
        lambda: manager.export_current(str(tmp_path)),
    )
    for operation in operations:
        with pytest.raises(RuntimeError, match="^session manager is closed$"):
            operation()


def test_export_releases_manager_locks_before_copy(tmp_path):
    class BlockingOutputManager(OutputManager):
        def __init__(self, base_dir):
            super().__init__(base_dir)
            self.export_started = Event()
            self.release_export = Event()

        def export_session(self, audio_path, directory):
            self.export_started.set()
            self.release_export.wait(timeout=2.0)
            return super().export_session(audio_path, directory)

    class ProbingPlayback(RecordingPlayback):
        def __init__(self):
            super().__init__()
            self.pause_called = Event()

        def pause(self):
            self.pause_called.set()
            return super().pause()

    output_manager = BlockingOutputManager(tmp_path / "outputs")
    playback = ProbingPlayback()
    manager = SessionManager(
        model=RecordingModel(),
        playback=playback,
        output_manager=output_manager,
        render_seconds_limit=1,
    )
    export_errors = []
    playback_errors = []

    def run_export():
        try:
            manager.export_current(str(tmp_path / "exports"))
        except BaseException as exc:
            export_errors.append(exc)

    def run_pause():
        try:
            manager.pause_session()
        except BaseException as exc:
            playback_errors.append(exc)

    export_thread = None
    pause_thread = None
    try:
        manager.start_session(make_request())
        assert manager.wait_for_active_task(timeout=1.0).output_path is not None

        export_thread = Thread(target=run_export)
        export_thread.start()
        assert output_manager.export_started.wait(timeout=1.0)

        pause_thread = Thread(target=run_pause)
        pause_thread.start()
        assert playback.pause_called.wait(timeout=1.0)
    finally:
        output_manager.release_export.set()
        if export_thread is not None and export_thread.ident is not None:
            export_thread.join(timeout=1.0)
        if pause_thread is not None and pause_thread.ident is not None:
            pause_thread.join(timeout=1.0)
        manager.shutdown()

    if export_thread is not None:
        assert not export_thread.is_alive()
    if pause_thread is not None:
        assert not pause_thread.is_alive()
    assert export_errors == []
    assert playback_errors == []


def test_status_paths_do_not_read_history_while_state_lock_is_held(tmp_path):
    class LockProbeHistoryStore(HistoryStore):
        def __init__(self, path):
            super().__init__(path)
            self.manager = None
            self.lock_free = []

        def list(self, limit=20):
            if self.manager is not None:
                acquired = self.manager._lock.acquire(blocking=False)
                self.lock_free.append(acquired)
                if acquired:
                    self.manager._lock.release()
            return super().list(limit=limit)

    history_store = LockProbeHistoryStore(tmp_path / "history.jsonl")
    manager = SessionManager(model=RecordingModel(), history_store=history_store)
    history_store.manager = manager

    manager.start_session(make_request())
    manager.wait_for_active_task(timeout=1.0)
    manager.stop_session()
    manager.shutdown()

    assert history_store.lock_free
    assert all(history_store.lock_free)


def test_commit_lock_is_released_before_history_and_playback_io(tmp_path):
    class ProbingHistoryStore(HistoryStore):
        def __init__(self, path):
            super().__init__(path)
            self.manager = None
            self.commit_lock_free = []
            self.history_lock_held = []

        def _probe_commit_lock(self):
            acquired = self.manager._commit_lock.acquire(blocking=False)
            self.commit_lock_free.append(acquired)
            if acquired:
                self.manager._commit_lock.release()

        def _probe_history_lock(self):
            acquired = self.manager._history_lock.acquire(blocking=False)
            self.history_lock_held.append(not acquired)
            if acquired:
                self.manager._history_lock.release()

        def append(self, record):
            self._probe_commit_lock()
            self._probe_history_lock()
            super().append(record)

        def list(self, limit=20):
            if self.manager is not None:
                self._probe_commit_lock()
                self._probe_history_lock()
            return super().list(limit=limit)

    class ProbingPlayback(RecordingPlayback):
        def __init__(self):
            super().__init__()
            self.manager = None
            self.commit_lock_free = None

        def load(self, result):
            acquired = self.manager._commit_lock.acquire(blocking=False)
            self.commit_lock_free = acquired
            if acquired:
                self.manager._commit_lock.release()
            super().load(result)

    history_store = ProbingHistoryStore(tmp_path / "history.jsonl")
    playback = ProbingPlayback()
    manager = SessionManager(
        model=RecordingModel(),
        playback=playback,
        output_manager=OutputManager(tmp_path / "outputs"),
        history_store=history_store,
        render_seconds_limit=1,
    )
    history_store.manager = manager
    playback.manager = manager

    manager.start_session(make_request())
    try:
        status = manager.wait_for_active_task(timeout=1.0)
        assert status.state == BackendState.PLAYING
        assert history_store.commit_lock_free
        assert all(history_store.commit_lock_free)
        assert history_store.history_lock_held
        assert all(history_store.history_lock_held)
        assert playback.commit_lock_free is True
    finally:
        manager.shutdown()


def test_queued_future_cancellation_returns_and_discards_future():
    script = textwrap.dedent(
        """
        import numpy as np
        from threading import Event

        from lofi_focus_tui.backend.session_manager import SessionManager
        from lofi_focus_tui.domain import EnergyLevel, SessionRequest
        from lofi_focus_tui.generation.base import GenerationResult

        class BlockingModel:
            name = "blocking"

            def __init__(self):
                self.started = Event()
                self.release = Event()

            def generate(self, blueprint, duration_seconds, settings=None):
                self.started.set()
                self.release.wait(timeout=5.0)
                return GenerationResult(
                    audio=np.zeros(duration_seconds * 44100, dtype=np.float32),
                    sample_rate=44100,
                    duration_seconds=duration_seconds,
                    metadata={"session_id": blueprint.session_id, "backend": self.name},
                )

        request = SessionRequest(
            preset="classic_lofi",
            duration_minutes=5,
            energy=EnergyLevel.STEADY,
        )
        model = BlockingModel()
        manager = SessionManager(model=model, render_seconds_limit=1)
        manager.start_session(request)
        assert model.started.wait(timeout=1.0)
        manager.start_session(request)
        queued = manager._active_future
        assert queued is not None
        assert not queued.running()
        manager.stop_session()
        assert queued.cancelled()
        assert queued not in manager._futures
        model.release.set()
        manager.shutdown()
        """
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path.cwd(),
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            timeout=5.0,
        )
    except subprocess.TimeoutExpired as exc:
        pytest.fail(f"queued future cancellation hung: {exc}")
    assert result.returncode == 0, result.stderr


def test_stop_session_rejects_closed_before_blocked_history_read(tmp_path):
    class BlockingHistoryStore(HistoryStore):
        def __init__(self, path):
            super().__init__(path)
            self.block_list = False
            self.release_list = Event()

        def list(self, limit=20):
            if self.block_list:
                self.release_list.wait(timeout=5.0)
            return super().list(limit=limit)

    history_store = BlockingHistoryStore(tmp_path / "history.jsonl")
    manager = SessionManager(model=RecordingModel(), history_store=history_store)
    manager.shutdown()
    history_store.block_list = True
    stop_errors = []

    def run_stop():
        try:
            manager.stop_session()
        except BaseException as exc:
            stop_errors.append(exc)

    stop_thread = Thread(target=run_stop, daemon=True)
    started_at = time.monotonic()
    stop_thread.start()
    try:
        stop_thread.join(timeout=0.5)
        elapsed = time.monotonic() - started_at
        assert not stop_thread.is_alive()
        assert elapsed < 0.5
    finally:
        history_store.release_list.set()
        stop_thread.join(timeout=1.0)

    assert len(stop_errors) == 1
    assert str(stop_errors[0]) == "session manager is closed"


@pytest.mark.parametrize("failure", ["wav", "metadata"])
def test_active_output_write_failure_cleans_partial_artifacts(tmp_path, failure):
    output_manager = OutputManager(tmp_path / "outputs")
    if failure == "wav":
        def failing_save_wav(result, directory, filename="audio.wav"):
            (directory / filename).write_bytes(b"partial audio")
            raise OSError("save wav failed")

        output_manager.save_wav = failing_save_wav
    else:
        def failing_save_metadata(metadata, directory):
            (directory / "metadata.json").write_text("partial metadata", encoding="utf-8")
            raise OSError("save metadata failed")

        output_manager.save_metadata = failing_save_metadata

    manager = SessionManager(
        model=RecordingModel(),
        output_manager=output_manager,
        render_seconds_limit=1,
    )
    manager.start_session(make_request())
    try:
        status = manager.wait_for_active_task(timeout=1.0)
        assert status.state == BackendState.ERROR
        assert not list((tmp_path / "outputs").rglob("audio.wav"))
        assert not list((tmp_path / "outputs").rglob("metadata.json"))
        assert list((tmp_path / "outputs").iterdir()) == []
    finally:
        manager.shutdown()


def test_history_append_failure_cleans_record_and_artifacts(tmp_path):
    class FailingHistoryStore(HistoryStore):
        def append(self, record):
            super().append(record)
            raise OSError("history append failed")

    history_store = FailingHistoryStore(tmp_path / "history.jsonl")
    manager = SessionManager(
        model=RecordingModel(),
        output_manager=OutputManager(tmp_path / "outputs"),
        history_store=history_store,
        render_seconds_limit=1,
    )
    manager.start_session(make_request())
    try:
        status = manager.wait_for_active_task(timeout=1.0)
        assert status.state == BackendState.ERROR
        assert history_store.list(limit=5) == []
        assert not list((tmp_path / "outputs").rglob("audio.wav"))
        assert not list((tmp_path / "outputs").rglob("metadata.json"))
        assert list((tmp_path / "outputs").iterdir()) == []
    finally:
        manager.shutdown()


def test_playback_failure_rolls_back_record_and_artifacts(tmp_path):
    class FailingPlayback(RecordingPlayback):
        def load(self, result):
            raise OSError("playback load failed")

    history_store = HistoryStore(tmp_path / "history.jsonl")
    manager = SessionManager(
        model=RecordingModel(),
        playback=FailingPlayback(),
        output_manager=OutputManager(tmp_path / "outputs"),
        history_store=history_store,
        render_seconds_limit=1,
    )
    manager.start_session(make_request())
    try:
        status = manager.wait_for_active_task(timeout=1.0)
        assert status.state == BackendState.ERROR
        assert history_store.list(limit=5) == []
        assert not list((tmp_path / "outputs").rglob("audio.wav"))
        assert not list((tmp_path / "outputs").rglob("metadata.json"))
        assert list((tmp_path / "outputs").iterdir()) == []
    finally:
        manager.shutdown()


def test_shutdown_does_not_wait_for_blocked_history_snapshot(tmp_path):
    class BlockingHistoryStore(HistoryStore):
        def __init__(self, path):
            super().__init__(path)
            self.block_list = False
            self.release_list = Event()

        def list(self, limit=20):
            if self.block_list:
                self.release_list.wait(timeout=5.0)
            return super().list(limit=limit)

    history_store = BlockingHistoryStore(tmp_path / "history.jsonl")
    manager = SessionManager(model=RecordingModel(), history_store=history_store)
    history_store.block_list = True
    shutdown_errors = []

    def run_shutdown():
        try:
            manager.shutdown()
        except BaseException as exc:
            shutdown_errors.append(exc)

    shutdown_thread = Thread(target=run_shutdown, daemon=True)
    started_at = time.monotonic()
    shutdown_thread.start()
    try:
        shutdown_thread.join(timeout=2.3)
        elapsed = time.monotonic() - started_at
        assert not shutdown_thread.is_alive()
        assert elapsed < 2.2
        assert shutdown_errors == []
        assert manager.health().message == "closed"
    finally:
        history_store.release_list.set()
        shutdown_thread.join(timeout=1.0)


def test_shutdown_does_not_wait_for_blocked_output_commit(tmp_path):
    model = DelayedShutdownModel()
    playback = RecordingPlayback()
    output_manager = OutputManager(tmp_path / "outputs")
    history_store = HistoryStore(tmp_path / "history.jsonl")
    save_started = Event()
    release_save = Event()
    original_save_wav = output_manager.save_wav

    def blocked_save_wav(result, directory, filename="audio.wav"):
        save_started.set()
        release_save.wait()
        return original_save_wav(result, directory, filename)

    output_manager.save_wav = blocked_save_wav
    manager = SessionManager(
        model=model,
        playback=playback,
        output_manager=output_manager,
        history_store=history_store,
        render_seconds_limit=1,
    )

    manager.start_session(make_request())
    assert model.started.wait(timeout=1.0)
    model.release.set()
    assert save_started.wait(timeout=1.0)

    shutdown_errors = []

    def run_shutdown():
        try:
            manager.shutdown()
        except BaseException as exc:
            shutdown_errors.append(exc)

    shutdown_thread = Thread(
        target=run_shutdown,
        daemon=True,
    )
    started_at = time.monotonic()
    shutdown_thread.start()
    try:
        shutdown_thread.join(timeout=2.3)
        elapsed = time.monotonic() - started_at
        assert not shutdown_thread.is_alive()
        assert elapsed < 2.2
        assert shutdown_errors == []
        assert manager.health().message == "closed"
        assert history_store.list(limit=5) == []
    finally:
        release_save.set()
        shutdown_thread.join(timeout=1.0)

    manager.wait_for_active_task(timeout=1.0)
    assert model.closed.is_set()
    assert history_store.list(limit=5) == []
    assert playback.loaded is None
    assert manager.health().message == "closed"
    assert not list((tmp_path / "outputs").rglob("audio.wav"))
    assert not list((tmp_path / "outputs").rglob("metadata.json"))


def test_shutdown_rolls_back_history_append_after_close(tmp_path):
    class BlockingHistoryStore(HistoryStore):
        def __init__(self, path):
            super().__init__(path)
            self.append_started = Event()
            self.append_written = Event()
            self.release_append = Event()
            self.release_append_return = Event()

        def append(self, record):
            self.append_started.set()
            self.release_append.wait(timeout=5.0)
            super().append(record)
            self.append_written.set()
            self.release_append_return.wait(timeout=5.0)

        def list(self, limit=20):
            if self.append_started.is_set() and not self.append_written.is_set():
                self.append_written.wait(timeout=1.0)
            return super().list(limit=limit)

    model = RecordingModel()
    playback = RecordingPlayback()
    output_manager = OutputManager(tmp_path / "outputs")
    history_store = BlockingHistoryStore(tmp_path / "history.jsonl")
    manager = SessionManager(
        model=model,
        playback=playback,
        output_manager=output_manager,
        history_store=history_store,
        render_seconds_limit=1,
    )

    manager.start_session(make_request())
    assert history_store.append_started.wait(timeout=1.0)
    with manager._lock:
        session_id = manager._status.active_session_id
        manager._status = manager._status.model_copy(
            update={"recent_sessions": [f"{session_id[:8]} classic_lofi"]}
        )

    shutdown_errors = []

    def run_shutdown():
        try:
            manager.shutdown()
        except BaseException as exc:
            shutdown_errors.append(exc)

    shutdown_thread = Thread(target=run_shutdown, daemon=True)
    shutdown_thread.start()
    history_store.release_append.set()
    assert history_store.append_written.wait(timeout=1.0)
    try:
        shutdown_thread.join(timeout=2.3)
        assert not shutdown_thread.is_alive()
        assert shutdown_errors == []
        assert manager.health().message == "closed"
    finally:
        history_store.release_append_return.set()
        shutdown_thread.join(timeout=1.0)

    manager.wait_for_active_task(timeout=1.0)
    assert history_store.list(limit=5) == []
    assert playback.loaded is None
    assert manager.health().recent_sessions == []
    assert not list((tmp_path / "outputs").rglob("audio.wav"))
    assert not list((tmp_path / "outputs").rglob("metadata.json"))


def test_health_reports_idle_closed_after_shutdown():
    manager = SessionManager(model=RecordingModel())

    manager.shutdown()

    status = manager.health()
    assert status.state == BackendState.IDLE
    assert status.message == "closed"
    assert status.active_task_id is None


def test_blocked_worker_late_result_does_not_commit_or_restart_playback(tmp_path):
    model = DelayedShutdownModel()
    playback = RecordingPlayback()
    output_manager = OutputManager(tmp_path / "outputs")
    history_store = HistoryStore(tmp_path / "history.jsonl")
    manager = SessionManager(
        model=model,
        playback=playback,
        output_manager=output_manager,
        history_store=history_store,
        render_seconds_limit=1,
    )

    status = manager.start_session(make_request())
    assert model.started.wait(timeout=1.0)
    manager.shutdown()
    assert model.closed.is_set() is False

    model.release.set()
    manager.wait_for_active_task()

    task = manager._tasks[status.active_task_id]
    assert not list((tmp_path / "outputs").rglob("audio.wav"))
    assert not list((tmp_path / "outputs").rglob("metadata.json"))
    assert history_store.list(limit=5) == []
    assert task.output_path is None
    assert playback.loaded is None
    assert manager.health().message == "closed"
    assert model.closed.is_set()


def test_cleanup_happens_after_cooperative_worker_stops():
    model = CooperativeShutdownModel()
    manager = SessionManager(model=model)

    manager.start_session(make_request())
    assert model.started.wait(timeout=1.0)
    manager.shutdown()

    assert model.closed.is_set()


def test_delayed_cleanup_waits_for_worker_to_stop():
    model = DelayedShutdownModel()
    manager = SessionManager(model=model)

    manager.start_session(make_request())
    assert model.started.wait(timeout=1.0)
    manager.shutdown()

    assert model.closed.is_set() is False
    model.release.set()
    manager.wait_for_active_task()

    assert model.closed.is_set()
