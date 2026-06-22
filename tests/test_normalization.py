import numpy as np

from lofi_focus_tui.audio.normalization import (
    apply_fade,
    crossfade,
    is_clipped,
    is_silent,
    peak,
    rms,
)


def test_rms_and_peak_handle_empty_and_non_empty_audio():
    assert rms(np.array([], dtype=np.float32)) == 0.0
    assert peak(np.array([], dtype=np.float32)) == 0.0

    audio = np.array([-0.5, 0.25, 0.5], dtype=np.float32)

    assert rms(audio) == np.float32(np.sqrt(0.1875))
    assert peak(audio) == 0.5


def test_silence_and_clipping_detection():
    assert is_silent(np.zeros(100, dtype=np.float32)) is True
    assert is_silent(np.full(100, 0.01, dtype=np.float32)) is False

    assert is_clipped(np.array([0.0, 0.25, -0.98], dtype=np.float32), threshold=0.99) is False
    assert is_clipped(np.array([0.0, 0.25, -0.995], dtype=np.float32), threshold=0.99) is True


def test_apply_fade_shapes_audio_edges_without_changing_length():
    audio = np.ones(10, dtype=np.float32)

    faded = apply_fade(audio, sample_rate=10, fade_seconds=0.2)

    assert faded.shape == audio.shape
    assert faded[0] == 0.0
    assert faded[1] == 0.5
    assert faded[2] == 1.0
    assert faded[-2] == 0.5
    assert faded[-1] == 0.0


def test_crossfade_overlaps_audio_by_requested_duration():
    left = np.ones(6, dtype=np.float32)
    right = np.zeros(6, dtype=np.float32)

    mixed = crossfade(left, right, sample_rate=10, seconds=0.2)

    assert mixed.shape == (10,)
    np.testing.assert_allclose(mixed[:4], np.ones(4, dtype=np.float32))
    np.testing.assert_allclose(mixed[4:6], np.array([1.0, 0.5], dtype=np.float32))
    np.testing.assert_allclose(mixed[6:], np.zeros(4, dtype=np.float32))
