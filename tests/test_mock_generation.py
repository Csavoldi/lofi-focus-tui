from lofi_focus_tui.composition import create_blueprint
from lofi_focus_tui.domain import EnergyLevel, SessionRequest
from lofi_focus_tui.generation.mock import MockModelAdapter
from lofi_focus_tui.presets import expand_preset


def test_mock_adapter_returns_deterministic_audio_metadata():
    plan = expand_preset(SessionRequest(preset="deep_work", duration_minutes=30, energy=EnergyLevel.STEADY))
    blueprint = create_blueprint(plan)

    result = MockModelAdapter().generate(blueprint, duration_seconds=10)

    assert result.sample_rate == 44100
    assert result.duration_seconds == 10
    assert result.audio.shape[0] == 441000
    assert result.metadata["session_id"] == blueprint.session_id
