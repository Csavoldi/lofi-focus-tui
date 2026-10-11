from dataclasses import dataclass

import numpy as np

from lofi_focus_tui.audio.normalization import is_clipped, is_silent, peak, rms

PROFILE_WINDOW_SECONDS = 1.0
LOUDNESS_WARNING_THRESHOLD = 0.20
LOUDNESS_SEVERE_THRESHOLD = 0.50
BOUNDARY_CLICK_THRESHOLD = 0.35
SPECTRAL_CHANGE_THRESHOLD = 0.25


@dataclass(frozen=True)
class ChunkProfile:
    sample_rate: int
    duration_seconds: float
    rms: float
    peak: float
    silent: bool
    clipped: bool
    spectral_balance: float

    def to_dict(self) -> dict[str, float | int | bool]:
        return {
            "sample_rate": self.sample_rate,
            "duration_seconds": self.duration_seconds,
            "rms": self.rms,
            "peak": self.peak,
            "silent": self.silent,
            "clipped": self.clipped,
            "spectral_balance": self.spectral_balance,
        }


@dataclass(frozen=True)
class ContinuityReport:
    accepted: bool
    severe: bool
    warnings: list[str]
    left_rms: float
    right_rms: float
    boundary_delta: float
    spectral_delta: float

    @property
    def reasons(self) -> list[str]:
        return self.warnings

    def to_dict(self) -> dict[str, bool | float | list[str]]:
        return {
            "accepted": self.accepted,
            "severe": self.severe,
            "warnings": list(self.warnings),
            "left_rms": self.left_rms,
            "right_rms": self.right_rms,
            "boundary_delta": self.boundary_delta,
            "spectral_delta": self.spectral_delta,
        }


def analyze_chunk(audio: np.ndarray, sample_rate: int) -> ChunkProfile:
    samples = np.asarray(audio, dtype=np.float32)
    duration_seconds = len(samples) / sample_rate if sample_rate > 0 else 0.0
    return ChunkProfile(
        sample_rate=sample_rate,
        duration_seconds=float(duration_seconds),
        rms=rms(samples),
        peak=peak(samples),
        silent=is_silent(samples),
        clipped=is_clipped(samples),
        spectral_balance=_spectral_balance(
            _window_samples(samples, sample_rate, from_end=True), sample_rate
        ),
    )


def analyze_boundary(
    left: np.ndarray,
    right: np.ndarray,
    sample_rate: int = 44100,
) -> ContinuityReport:
    warnings: list[str] = []
    left_profile = analyze_chunk(left, sample_rate)
    right_profile = analyze_chunk(right, sample_rate)
    loudness_delta = abs(left_profile.rms - right_profile.rms)
    boundary_delta = _boundary_delta(left, right)
    spectral_delta = abs(
        _spectral_balance(_window_samples(left, sample_rate, from_end=True), sample_rate)
        - _spectral_balance(_window_samples(right, sample_rate, from_end=False), sample_rate)
    )

    if loudness_delta > LOUDNESS_WARNING_THRESHOLD:
        warnings.append("loudness jump")
    if boundary_delta > BOUNDARY_CLICK_THRESHOLD:
        warnings.append("boundary click")
    if left_profile.silent or right_profile.silent:
        warnings.append("silent audio")
    if left_profile.clipped or right_profile.clipped:
        warnings.append("clipping")
    if spectral_delta > SPECTRAL_CHANGE_THRESHOLD:
        warnings.append("spectral change")

    severe_warnings = {"boundary click", "silent audio", "clipping"}
    severe = (
        loudness_delta > LOUDNESS_SEVERE_THRESHOLD
        or bool(severe_warnings.intersection(warnings))
    )
    return ContinuityReport(
        accepted=not warnings,
        severe=severe,
        warnings=warnings,
        left_rms=left_profile.rms,
        right_rms=right_profile.rms,
        boundary_delta=boundary_delta,
        spectral_delta=spectral_delta,
    )


def continuation_notes(report: ContinuityReport) -> list[str]:
    notes = {
        "loudness jump": "match the previous chunk's loudness at the transition",
        "boundary click": "avoid a sharp transient at the transition",
        "silent audio": "maintain continuous low-level texture through the transition",
        "clipping": "reduce peak density and avoid aggressive transients",
        "spectral change": "continue the established timbral balance into the next section",
    }
    return [notes[warning] for warning in report.warnings if warning in notes]


def _boundary_delta(left: np.ndarray, right: np.ndarray) -> float:
    if len(left) == 0 or len(right) == 0:
        return 0.0
    delta = np.asarray(right[0], dtype=np.float32) - np.asarray(left[-1], dtype=np.float32)
    return float(np.max(np.abs(delta)))


def _window_samples(audio: np.ndarray, sample_rate: int, from_end: bool) -> np.ndarray:
    samples = np.asarray(audio, dtype=np.float32)
    window_size = max(1, int(sample_rate * PROFILE_WINDOW_SECONDS))
    window_size = min(window_size, len(samples))
    if window_size == 0:
        return samples
    return samples[-window_size:] if from_end else samples[:window_size]


def _spectral_balance(audio: np.ndarray, sample_rate: int) -> float:
    samples = np.asarray(audio, dtype=np.float32)
    if samples.size == 0 or sample_rate <= 0:
        return 0.0
    if samples.ndim > 1:
        samples = np.mean(samples, axis=1)
    samples = samples.reshape(-1)
    if len(samples) < 2:
        return 0.0
    samples = samples - np.mean(samples)
    magnitudes = np.abs(np.fft.rfft(samples))
    magnitudes[0] = 0.0
    total = float(np.sum(magnitudes))
    if total == 0.0:
        return 0.0
    frequencies = np.fft.rfftfreq(len(samples), d=1.0 / sample_rate)
    centroid = float(np.dot(frequencies, magnitudes) / total)
    return centroid / max(1.0, sample_rate / 2.0)
