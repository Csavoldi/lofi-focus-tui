import numpy as np

from lofi_focus_tui.backend.session_manager import SessionManager
from lofi_focus_tui.domain import EnergyLevel, SessionRequest
from lofi_focus_tui.generation.base import GenerationResult
from lofi_focus_tui.generation.mock import MockModelAdapter
from lofi_focus_tui.generation.settings import GenerationSettings


def test_start_session_generates_playing_status():
    manager = SessionManager(model=MockModelAdapter())
    status = manager.start_session(
        SessionRequest(
            preset="deep_work",
            duration_minutes=30,
            energy=EnergyLevel.STEADY,
            style_tags=["lofi"],
            avoid_tags=["vocals"],
        )
    )

    assert status.state == "playing"
    assert status.active_session_id is not None
    assert status.backend == "mock"


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


def test_start_session_passes_generation_settings_to_model():
    model = RecordingModel()
    manager = SessionManager(model=model)
    settings = GenerationSettings(inference_steps=12, seed=99)

    manager.start_session(
        SessionRequest(
            preset="deep_work",
            duration_minutes=30,
            energy=EnergyLevel.STEADY,
            generation=settings,
        )
    )

    assert model.settings == settings


def test_start_session_uses_generation_defaults_when_request_omits_settings():
    model = RecordingModel()
    defaults = GenerationSettings(inference_steps=18, seed=77)
    manager = SessionManager(model=model, generation_defaults=defaults)

    manager.start_session(
        SessionRequest(
            preset="deep_work",
            duration_minutes=30,
            energy=EnergyLevel.STEADY,
        )
    )

    assert model.settings == defaults


def test_start_session_request_generation_overrides_defaults():
    model = RecordingModel()
    defaults = GenerationSettings(inference_steps=18, seed=77)
    request_settings = GenerationSettings(inference_steps=12, seed=99)
    manager = SessionManager(model=model, generation_defaults=defaults)

    manager.start_session(
        SessionRequest(
            preset="deep_work",
            duration_minutes=30,
            energy=EnergyLevel.STEADY,
            generation=request_settings,
        )
    )

    assert model.settings == request_settings


def test_start_session_uses_configured_render_seconds_limit():
    model = RecordingModel()
    manager = SessionManager(model=model, render_seconds_limit=12)

    manager.start_session(
        SessionRequest(
            preset="deep_work",
            duration_minutes=30,
            energy=EnergyLevel.STEADY,
        )
    )

    assert model.duration_seconds == 12
