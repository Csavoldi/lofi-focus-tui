"""Post-generation quality analysis and prompt feedback.

The producer loop: after a session completes, analyze the rendered audio
(AudioBox Aesthetics scores via its Python API when installed, plus
dependency-free MIR measurements), translate the report into prompt
adjustments, and persist them so the next session's caption asks for what
the last take lacked.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

# Human-rater aesthetic axes from AudioBox Aesthetics run on a 1-10 scale;
# below these thresholds the producer rules ask the next prompt for more.
SCORE_THRESHOLDS = {"CE": 6.0, "CU": 6.0, "PQ": 6.0}
DIP_RATIO_FLOOR = 0.03  # p10/p90 below this reads as hiccupy gaps
SUSTAINED_FLOOR = 0.7

_RULES = {
    "CE": "memorable melodic hook with richer harmonic movement",
    "CU": "steady, unobtrusive background character suited for focus",
    "PQ": "clean, polished, well-balanced production",
}


@dataclass(frozen=True)
class QualityScores:
    ce: float | None = None
    cu: float | None = None
    pc: float | None = None
    pq: float | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "QualityScores":
        def pick(*names: str) -> float | None:
            for name in names:
                value = data.get(name)
                if isinstance(value, (int, float)):
                    return float(value)
            return None

        return cls(
            ce=pick("CE", "ce"), cu=pick("CU", "cu"), pc=pick("PC", "pc"), pq=pick("PQ", "pq")
        )


@dataclass(frozen=True)
class QualityReport:
    scores: QualityScores = field(default_factory=QualityScores)
    dip_ratio: float | None = None
    sustained_fraction: float | None = None
    suggestions: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "scores": {
                "CE": self.scores.ce,
                "CU": self.scores.cu,
                "PC": self.scores.pc,
                "PQ": self.scores.pq,
            },
            "dip_ratio": self.dip_ratio,
            "sustained_fraction": self.sustained_fraction,
            "suggestions": list(self.suggestions),
        }


def mir_profile(audio: np.ndarray, sample_rate: int) -> dict[str, float]:
    """Dependency-free loudness-envelope measurements (numpy only).

    dip_ratio: p10/p90 of the 100 ms RMS envelope — how deep the dips between
    beat events go (low values are the perceived hiccups). sustained_fraction:
    share of windows where a background bed is audible above 30% of the median.
    """
    samples = np.asarray(audio, dtype=np.float32)
    mono = samples.mean(axis=1) if samples.ndim > 1 else samples
    window = max(1, int(sample_rate * 0.1))
    levels = []
    for start in range(0, len(mono) - window + 1, window):
        piece = mono[start : start + window]
        levels.append(float(np.sqrt(np.mean(np.square(piece)))))
    if not levels:
        return {"dip_ratio": 1.0, "sustained_fraction": 1.0}
    array = np.array(levels)
    p90, p10 = np.percentile(array, [90, 10])
    median = float(np.median(array))
    return {
        "dip_ratio": float(p10 / max(p90, 1e-9)),
        "sustained_fraction": float(np.mean(array > 0.3 * median)) if median > 0 else 1.0,
    }


def suggest_adjustments(
    report: QualityReport,
    thresholds: dict | None = None,
    dip_floor: float | None = None,
) -> tuple[str, ...]:
    """Producer rules: translate a report into caption asks for the next take.

    Thresholds default to the standard targets; a refinement policy passes
    its own so stricter policies generate proportionally stricter asks.
    """
    thresholds = thresholds or SCORE_THRESHOLDS
    dip_floor = DIP_RATIO_FLOOR if dip_floor is None else dip_floor
    suggestions: list[str] = []
    for axis, phrase in _RULES.items():
        value = getattr(report.scores, axis.lower())
        minimum = thresholds.get(axis)
        if (
            value is not None
            and minimum is not None
            and value < minimum
            and phrase not in suggestions
        ):
            suggestions.append(phrase)
    # Both bed rules target the same gap problem; the dip measurement is the
    # stronger signal, so it subsumes the sustained-bed ask.
    if report.dip_ratio is not None and report.dip_ratio < dip_floor:
        suggestions.append("dense continuous pad bed with chords held throughout")
    elif report.sustained_fraction is not None and report.sustained_fraction < SUSTAINED_FLOOR:
        suggestions.append("constant sustained background texture under the beat")
    return tuple(suggestions[:3])


def build_report(
    audio: np.ndarray, sample_rate: int, scores: QualityScores | None = None
) -> QualityReport:
    measurements = mir_profile(audio, sample_rate)
    base = QualityReport(
        scores=scores or QualityScores(),
        dip_ratio=measurements["dip_ratio"],
        sustained_fraction=measurements["sustained_fraction"],
    )
    return QualityReport(
        scores=base.scores,
        dip_ratio=base.dip_ratio,
        sustained_fraction=base.sustained_fraction,
        suggestions=suggest_adjustments(base),
    )


class AudioboxAnalyzer:
    """Scores audio through AudioBox Aesthetics' Python API, in-process.

    ``audiobox_aesthetics`` (and torch) are optional dependencies: the import
    happens lazily and any failure disables scoring — the report then carries
    only the local MIR measurements. A predictor instance can be injected for
    tests.
    """

    def __init__(self, excerpt_seconds: float = 60.0, predictor: Any = None) -> None:
        self.excerpt_seconds = excerpt_seconds
        self._predictor = predictor
        # Last scoring failure, surfaced in reports so silent None scores
        # are diagnosable (import failures, model errors, thread issues).
        self.last_error: str | None = None

    def _load_predictor(self) -> Any:
        from audiobox_aesthetics.infer import initialize_predictor

        return initialize_predictor()

    def scores_for(self, audio: np.ndarray, sample_rate: int) -> QualityScores | None:
        self.last_error = None
        try:
            if self._predictor is None:
                self._predictor = self._load_predictor()
            excerpt = self._excerpt(audio, sample_rate)
            import torch

            waveform = torch.from_numpy(np.ascontiguousarray(excerpt, dtype=np.float32))[None, :]
            results = self._predictor.forward([{"path": waveform, "sample_rate": sample_rate}])
            payload = results[0] if isinstance(results, list) else results
            if isinstance(payload, dict):
                return QualityScores.from_dict(payload)
            self.last_error = f"unexpected analyzer output: {type(payload).__name__}"
        except Exception as exc:  # noqa: BLE001 - surfaced via last_error for reports
            self.last_error = f"{type(exc).__name__}: {exc}"
        return None

    def _excerpt(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        samples = np.asarray(audio, dtype=np.float32)
        mono = samples.mean(axis=1) if samples.ndim > 1 else samples
        length = int(self.excerpt_seconds * sample_rate)
        if len(mono) <= length:
            return mono
        start = (len(mono) - length) // 2
        return mono[start : start + length]
