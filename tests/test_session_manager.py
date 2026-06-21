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

    def generate(self, blueprint, duration_seconds, settings=None):
        self.settings = settings
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
