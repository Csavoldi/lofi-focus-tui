from dataclasses import dataclass

import numpy as np

from lofi_focus_tui.audio.normalization import is_clipped, is_silent, rms


@dataclass(frozen=True)
class ContinuityReport:
    accepted: bool
    warnings: list[str]
    left_rms: float
    right_rms: float
    boundary_delta: float

    @property
    def reasons(self) -> list[str]:
        return self.warnings


def analyze_boundary(left: np.ndarray, right: np.ndarray) -> ContinuityReport:
    warnings: list[str] = []
    left_rms = rms(left)
    right_rms = rms(right)
    boundary_delta = _boundary_delta(left, right)

    if abs(left_rms - right_rms) > 0.20:
        warnings.append("loudness jump")
    if boundary_delta > 0.35:
        warnings.append("boundary click")
    if is_silent(left) or is_silent(right):
        warnings.append("silent audio")
    if is_clipped(left) or is_clipped(right):
        warnings.append("clipping")

    return ContinuityReport(
        accepted=not warnings,
        warnings=warnings,
        left_rms=left_rms,
        right_rms=right_rms,
        boundary_delta=boundary_delta,
    )


def _boundary_delta(left: np.ndarray, right: np.ndarray) -> float:
    if len(left) == 0 or len(right) == 0:
        return 0.0
    delta = np.asarray(right[0], dtype=np.float32) - np.asarray(left[-1], dtype=np.float32)
    return float(np.max(np.abs(delta)))
