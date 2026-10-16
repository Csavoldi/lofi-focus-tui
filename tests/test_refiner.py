from lofi_focus_tui.generation.refiner import PromptRefiner, RefinementPolicy
from lofi_focus_tui.quality import QualityReport, QualityScores


def good_report() -> QualityReport:
    return QualityReport(
        scores=QualityScores(ce=8.0, cu=8.0, pc=5.0, pq=8.0),
        dip_ratio=0.10,
        sustained_fraction=0.85,
    )


def bad_report() -> QualityReport:
    return QualityReport(
        scores=QualityScores(ce=4.0, cu=8.0, pc=5.0, pq=5.0),
        dip_ratio=0.02,
        sustained_fraction=0.5,
    )


def test_policy_accepts_good_reports_and_rejects_weak_ones():
    policy = RefinementPolicy()
    assert policy.accepts(good_report()) is True
    assert policy.accepts(bad_report()) is False


def test_policy_rank_prefers_high_scores_and_shallower_dips():
    policy = RefinementPolicy()
    assert policy.rank(good_report()) > policy.rank(bad_report())


def test_refiner_escalates_repeated_failures_and_caps_total():
    refiner = PromptRefiner()

    first = refiner.adjustments_for(bad_report())
    assert "memorable melodic hook with richer harmonic movement" in first
    assert len(first) <= 3

    # Same aspects fail again: wording escalates instead of repeating.
    second = refiner.adjustments_for(bad_report())
    assert "strong singable melodic hook carried through every section" in second
    assert len(second) <= 3


def test_refiner_rotates_seeds_deterministically():
    refiner = PromptRefiner()
    assert refiner.next_seed(100, 1) == refiner.next_seed(100, 1)
    assert refiner.next_seed(100, 1) != refiner.next_seed(100, 2)


def test_strict_policy_thresholds_drive_the_suggestions():
    # A policy stricter than the defaults must make good-by-default reports
    # actionable, otherwise refinement has nothing to apply and stalls.
    strict = RefinementPolicy(min_scores={"CE": 9.9, "CU": 9.9, "PQ": 9.9})
    refiner = PromptRefiner(strict)

    adjustments = refiner.adjustments_for(good_report())

    assert adjustments  # non-empty: the strict bar sees room to improve
    assert len(adjustments) <= 3
