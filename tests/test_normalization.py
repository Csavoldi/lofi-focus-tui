import numpy as np

from lofi_focus_tui.audio.normalization import (
    apply_fade,
    crossfade,
    ensure_stereo,
    is_clipped,
    is_silent,
    peak,
    rms,
    trim_edge_silence,
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


def test_ensure_stereo_duplicates_mono_into_two_identical_channels():
    mono = np.array([0.0, 0.25, -0.5], dtype=np.float32)

    stereo = ensure_stereo(mono)

    assert stereo.shape == (3, 2)
    np.testing.assert_allclose(stereo[:, 0], mono)
    np.testing.assert_allclose(stereo[:, 1], mono)


def test_ensure_stereo_passes_stereo_through_unchanged():
    stereo = np.stack([np.ones(4, dtype=np.float32), np.zeros(4, dtype=np.float32)], axis=1)

    result = ensure_stereo(stereo)

    np.testing.assert_array_equal(result, stereo)


def test_trim_edge_silence_cuts_trailing_fade():
    # 1.8s of tone, then 0.2s of near-silence at 100 Hz sample rate (within
    # the 15% trim cap).
    sr = 100
    tone = np.full(int(1.8 * sr), 0.3, dtype=np.float32)
    quiet = np.full(int(0.2 * sr), 1e-5, dtype=np.float32)
    chunk = np.concatenate([tone, quiet])

    trimmed = trim_edge_silence(chunk, sr, edge="end")

    assert len(trimmed) == int(1.8 * sr)
    np.testing.assert_allclose(trimmed, tone)


def test_trim_edge_silence_cuts_leading_fade_but_keeps_loud_tail():
    sr = 100
    quiet = np.full(int(0.2 * sr), 1e-5, dtype=np.float32)
    tone = np.full(int(1.8 * sr), 0.3, dtype=np.float32)
    chunk = np.concatenate([quiet, tone])

    trimmed = trim_edge_silence(chunk, sr, edge="start")

    assert len(trimmed) == int(1.8 * sr)
    np.testing.assert_allclose(trimmed, tone)


def test_trim_edge_silence_leaves_energetic_and_fully_silent_audio_alone():
    sr = 100
    loud = np.full(2 * sr, 0.3, dtype=np.float32)
    np.testing.assert_array_equal(trim_edge_silence(loud, sr, edge="end"), loud)

    silent = np.zeros(2 * sr, dtype=np.float32)
    np.testing.assert_array_equal(trim_edge_silence(silent, sr, edge="end"), silent)


def test_trim_edge_silence_is_bounded_and_stereo_aware():
    sr = 100
    # Mostly quiet chunk: trimming must stop at the 15% cap, not eat the tone.
    quiet = np.full(int(8.5 * sr), 1e-5, dtype=np.float32)
    tone = np.full(int(1.5 * sr), 0.3, dtype=np.float32)
    chunk = np.stack([np.concatenate([quiet, tone])] * 2, axis=1)

    trimmed = trim_edge_silence(chunk, sr, edge="start")

    max_trim = int((len(quiet) + len(tone)) * 0.15)
    assert trimmed.shape == (int(10 * sr) - max_trim, 2)
