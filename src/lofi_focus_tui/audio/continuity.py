from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ContinuityReport:
    accepted: bool
    reasons: list[str]


def _rms(audio: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(audio.astype(np.float64)))))


def analyze_boundary(left: np.ndarray, right: np.ndarray) -> ContinuityReport:
    reasons: list[str] = []
    left_rms = _rms(left)
    right_rms = _rms(right)

    if abs(left_rms - right_rms) > 0.25:
        reasons.append("loudness jump")
    if len(left) and len(right) and abs(float(right[0]) - float(left[-1])) > 0.5:
        reasons.append("boundary click")

    return ContinuityReport(accepted=not reasons, reasons=reasons)
