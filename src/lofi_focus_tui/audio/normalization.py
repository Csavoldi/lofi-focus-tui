import numpy as np


def rms(audio: np.ndarray) -> float:
    samples = np.asarray(audio, dtype=np.float32)
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(samples))))


def peak(audio: np.ndarray) -> float:
    samples = np.asarray(audio, dtype=np.float32)
    if samples.size == 0:
        return 0.0
    return float(np.max(np.abs(samples)))


def is_silent(audio: np.ndarray, threshold: float = 1e-4) -> bool:
    return rms(audio) <= threshold


def is_clipped(audio: np.ndarray, threshold: float = 0.99) -> bool:
    return peak(audio) >= threshold


def ensure_stereo(audio: np.ndarray) -> np.ndarray:
    """Duplicate mono audio into two identical channels.

    Some backends (ACE-Step HTTP via the Gradio pipeline) return mono WAVs even
    though earlier deployments produced stereo; headphone listeners lose the
    stereo field when a single channel is passed through. Upmixing keeps the
    signal identical while restoring two-channel playback.
    """
    samples = np.asarray(audio, dtype=np.float32)
    if samples.ndim == 1:
        return np.stack([samples, samples], axis=1)
    return samples


# The model likes to close every generation like a finished song: a multi
# second fade-out at the end and a fade-in at the start. At internal chunk
# boundaries those fades stack into near-silence, so the seam trimmer cuts the
# quiet edges before the crossfade joins two energetic passages instead.
EDGE_WINDOW_SECONDS = 0.05
EDGE_SILENCE_RMS = 0.004
EDGE_RELATIVE_THRESHOLD = 0.35  # -9 dB against the chunk's own loud level
EDGE_MAX_TRIM_FRACTION = 0.15


def trim_edge_silence(
    audio: np.ndarray,
    sample_rate: int,
    edge: str,
    window_seconds: float = EDGE_WINDOW_SECONDS,
    threshold: float = EDGE_SILENCE_RMS,
    relative_threshold: float = EDGE_RELATIVE_THRESHOLD,
    max_trim_fraction: float = EDGE_MAX_TRIM_FRACTION,
) -> np.ndarray:
    """Trim a quiet fade from one edge of a chunk.

    Only the trailing (``edge="end"``) or leading (``edge="start"``) quiet
    region is removed, bounded by ``max_trim_fraction`` of the chunk, so a
    genuinely quiet or silent chunk is left intact. A window counts as quiet
    when it sits below an absolute silence floor or well below the chunk's own
    loud level, so gradual fades are caught too, not just digital silence.
    """
    if edge not in ("start", "end"):
        raise ValueError(f"edge must be 'start' or 'end', got {edge!r}")
    samples = np.asarray(audio, dtype=np.float32)
    if samples.size == 0 or is_silent(samples):
        return samples
    window = max(1, int(sample_rate * window_seconds))
    if len(samples) <= window:
        return samples
    max_trim = int(len(samples) * max_trim_fraction)
    mono = samples.mean(axis=1) if samples.ndim > 1 else samples

    levels = [
        float(np.sqrt(np.mean(np.square(mono[start : start + window]))))
        for start in range(0, len(mono) - window + 1, window)
    ]
    loud_reference = float(np.percentile(levels, 95)) if levels else 0.0
    effective_threshold = max(threshold, relative_threshold * loud_reference)

    first_loud_start: int | None = None
    last_loud_end = 0
    for index, level in enumerate(levels):
        if level > effective_threshold:
            if first_loud_start is None:
                first_loud_start = index * window
            last_loud_end = (index + 1) * window

    if edge == "start":
        trim = first_loud_start if first_loud_start is not None else len(samples)
    else:
        trim = len(samples) - last_loud_end if last_loud_end > 0 else len(samples)
    trim = min(trim, max_trim)

    if trim <= 0:
        return samples
    return samples[:-trim] if edge == "end" else samples[trim:]


def apply_fade(audio: np.ndarray, sample_rate: int, fade_seconds: float) -> np.ndarray:
    samples = np.asarray(audio, dtype=np.float32).copy()
    fade_samples = _fade_sample_count(samples, sample_rate, fade_seconds)
    if fade_samples == 0:
        return samples

    fade_in = np.linspace(0.0, 1.0, fade_samples + 1, dtype=np.float32)[:-1]
    fade_out = np.linspace(1.0, 0.0, fade_samples + 1, dtype=np.float32)[1:]
    if samples.ndim > 1:
        fade_in = fade_in[:, None]
        fade_out = fade_out[:, None]

    samples[:fade_samples] *= fade_in
    samples[-fade_samples:] *= fade_out
    return samples


def crossfade(
    left: np.ndarray,
    right: np.ndarray,
    sample_rate: int,
    seconds: float,
) -> np.ndarray:
    left_samples = np.asarray(left, dtype=np.float32)
    right_samples = np.asarray(right, dtype=np.float32)
    fade_samples = min(
        int(sample_rate * seconds),
        len(left_samples),
        len(right_samples),
    )
    if fade_samples <= 0:
        return np.concatenate([left_samples, right_samples])

    fade_out = np.linspace(1.0, 0.0, fade_samples, endpoint=False, dtype=np.float32)
    fade_in = 1.0 - fade_out
    if left_samples.ndim > 1:
        fade_in = fade_in[:, None]
        fade_out = fade_out[:, None]

    overlap = (left_samples[-fade_samples:] * fade_out) + (
        right_samples[:fade_samples] * fade_in
    )
    return np.concatenate(
        [
            left_samples[:-fade_samples],
            overlap,
            right_samples[fade_samples:],
        ]
    )


def _fade_sample_count(audio: np.ndarray, sample_rate: int, fade_seconds: float) -> int:
    if sample_rate <= 0 or fade_seconds <= 0.0 or len(audio) == 0:
        return 0
    return min(int(sample_rate * fade_seconds), len(audio) // 2)
