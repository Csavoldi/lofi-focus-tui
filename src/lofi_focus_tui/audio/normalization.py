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
