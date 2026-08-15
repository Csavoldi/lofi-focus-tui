import numpy as np

from lofi_focus_tui.composition import create_blueprint
from lofi_focus_tui.domain import EnergyLevel, SessionRequest
from lofi_focus_tui.generation.mock import MockModelAdapter
from lofi_focus_tui.presets import expand_preset


def test_mock_adapter_returns_deterministic_audio_metadata():
    plan = expand_preset(
        SessionRequest(preset="deep_work", duration_minutes=30, energy=EnergyLevel.STEADY)
    )
    blueprint = create_blueprint(plan)

    result = MockModelAdapter().generate(blueprint, duration_seconds=10)

    assert result.sample_rate == 44100
    assert result.duration_seconds == 10
    assert result.audio.shape[0] == 441000
    assert result.metadata["session_id"] == blueprint.session_id


def test_mock_adapter_uses_a_soft_multi_tone_pad_instead_of_a_single_tone():
    plan = expand_preset(
        SessionRequest(
            preset="deep_work",
            duration_minutes=30,
            energy=EnergyLevel.STEADY,
            seed=0,
        )
    )
    blueprint = create_blueprint(plan)

    result = MockModelAdapter().generate(blueprint, duration_seconds=2)
    spectrum = np.abs(np.fft.rfft(result.audio * np.hanning(result.audio.size)))
    prominent_bins = np.flatnonzero(spectrum > spectrum.max() * 0.2)
    separated_peaks = prominent_bins[
        np.r_[True, np.diff(prominent_bins) > result.sample_rate / result.audio.size * 10]
    ]

    assert len(separated_peaks) >= 3
    assert np.max(np.abs(result.audio)) <= 0.05
