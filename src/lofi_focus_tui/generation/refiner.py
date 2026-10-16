"""Automatic prompt refinement: iterate takes until they clear quality targets.

The refiner turns the quality loop into a product behaviour: when a finished
take scores below target, the session manager regenerates it with an adjusted
prompt (escalated phrasing + a fresh seed) before the user ever hears it, and
keeps the best attempt. The same engine powers the offline prompt tuner so
preset defaults improve without anyone reading reports by hand.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lofi_focus_tui.quality import (
    DIP_RATIO_FLOOR,
    SCORE_THRESHOLDS,
    QualityReport,
    suggest_adjustments,
)

# Escalated wording for aspects that failed a previous attempt: the second
# ask is stronger than a plain repeat.
_ESCALATIONS = {
    "memorable melodic hook with richer harmonic movement": (
        "strong singable melodic hook carried through every section"
    ),
    "clean, polished, well-balanced production": (
        "professional studio production, immaculately balanced mix"
    ),
    "steady, unobtrusive background character suited for focus": (
        "barely-there background character that never pulls attention"
    ),
    "dense continuous pad bed with chords held throughout": (
        "thick wall of sustained pads underneath, never dropping out"
    ),
    "constant sustained background texture under the beat": (
        "unbroken ambient texture woven through the entire track"
    ),
}


@dataclass(frozen=True)
class RefinementPolicy:
    max_attempts: int = 2  # total takes generated per session
    min_scores: dict = field(
        default_factory=lambda: {
            "CE": SCORE_THRESHOLDS["CE"],
            "CU": SCORE_THRESHOLDS["CU"],
            "PQ": SCORE_THRESHOLDS["PQ"],
        }
    )
    dip_ratio_floor: float = DIP_RATIO_FLOOR

    def accepts(self, report: QualityReport) -> bool:
        scores = report.to_dict()["scores"]
        for axis, minimum in self.min_scores.items():
            value = scores.get(axis)
            if value is not None and value < minimum:
                return False
        if report.dip_ratio is not None and report.dip_ratio < self.dip_ratio_floor:
            return False
        return True

    def rank(self, report: QualityReport) -> float:
        """Higher is better; used to keep the strongest take across attempts."""
        scores = report.to_dict()["scores"]
        total = sum(
            min(value, 10.0) for value in scores.values() if isinstance(value, (int, float))
        )
        dip_bonus = 0.0
        if report.dip_ratio is not None:
            dip_bonus = min(report.dip_ratio, 0.15) / 0.15 * 3.0
        return total + dip_bonus


class PromptRefiner:
    """Accumulates report-driven prompt adjustments across attempts."""

    def __init__(self, policy: RefinementPolicy | None = None) -> None:
        self.policy = policy or RefinementPolicy()
        self._applied: list[str] = []

    def adjustments_for(self, report: QualityReport) -> list[str]:
        """Phrases for the next attempt.

        Aspects failing for the first time get their base wording; aspects
        that already failed a previous attempt get the escalated wording.
        Previously applied phrases whose aspect stopped failing are dropped,
        keeping captions bounded.
        """
        failing = suggest_adjustments(
            report,
            thresholds=self.policy.min_scores,
            dip_floor=self.policy.dip_ratio_floor,
        )
        applied: list[str] = []
        for phrase in failing:
            if phrase in self._applied:
                replacement = _ESCALATIONS.get(phrase, phrase)
                if replacement not in applied:
                    applied.append(replacement)
            elif phrase not in applied:
                applied.append(phrase)
        self._applied = applied[:3]
        return list(self._applied)

    def next_seed(self, base_seed: int, attempt: int) -> int:
        return (base_seed + attempt * 997) % (2**31)

    def reset(self) -> None:
        self._applied = []
