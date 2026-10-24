import numpy as np

from lofi_focus_tui.quality import (
    AudioboxAnalyzer,
    QualityReport,
    QualityScores,
    build_report,
    mir_profile,
    suggest_adjustments,
)


def test_mir_profile_measures_deep_dips_for_gated_audio():
    sr = 1000
    loud = np.full(int(0.5 * sr), 0.3, dtype=np.float32)
    quiet = np.full(int(0.5 * sr), 1e-4, dtype=np.float32)
    gated = np.tile(np.concatenate([loud, quiet]), 10)

    profile = mir_profile(gated, sr)

    assert profile["dip_ratio"] < 0.03
    assert profile["sustained_fraction"] < 0.7


def test_mir_profile_reports_smooth_audio_as_connected():
    sr = 1000
    smooth = np.full(10 * sr, 0.2, dtype=np.float32)

    profile = mir_profile(smooth, sr)

    assert profile["dip_ratio"] > 0.9
    assert profile["sustained_fraction"] > 0.9


def test_suggest_adjustments_translates_low_scores_into_prompt_asks():
    report = QualityReport(
        scores=QualityScores(ce=4.0, cu=7.0, pc=3.0, pq=5.5),
        dip_ratio=0.02,
        sustained_fraction=0.5,
    )

    suggestions = suggest_adjustments(report)

    assert "memorable melodic hook with richer harmonic movement" in suggestions
    assert "clean, polished, well-balanced production" in suggestions
    # The dip rule fired, so it subsumes the sustained-bed phrase (cap is 3).
    assert "dense continuous pad bed with chords held throughout" in suggestions
    assert "constant sustained background texture under the beat" not in suggestions
    # CU scored fine; its phrase must not appear.
    assert not any("background character" in s for s in suggestions)


def test_suggest_adjustments_stays_quiet_for_good_reports():
    report = QualityReport(
        scores=QualityScores(ce=8.0, cu=8.0, pc=5.0, pq=8.0),
        dip_ratio=0.08,
        sustained_fraction=0.85,
    )

    assert suggest_adjustments(report) == ()


def test_build_report_merges_scores_and_measurements():
    sr = 1000
    smooth = np.full(5 * sr, 0.2, dtype=np.float32)

    report = build_report(smooth, sr, QualityScores(ce=9.0, cu=9.0, pc=9.0, pq=5.0))

    assert report.scores.pq == 5.0
    assert report.dip_ratio > 0.9
    assert report.suggestions == ("clean, polished, well-balanced production",)
    payload = report.to_dict()
    assert payload["scores"]["PQ"] == 5.0
    assert payload["suggestions"] == ["clean, polished, well-balanced production"]


class _FakePredictor:
    def forward(self, inputs):
        return [{"CE": 7.0, "CU": 7.0, "PC": 4.0, "PQ": 9.0}]


def test_audiobox_analyzer_uses_injected_predictor_and_excerpt():
    sr = 100
    audio = np.full(300 * sr, 0.2, dtype=np.float32)  # 300s, mono
    seen = {}

    class Recorder(_FakePredictor):
        def forward(self, inputs):
            seen["length"] = int(inputs[0]["path"].shape[-1])
            seen["sr"] = inputs[0]["sample_rate"]
            return super().forward(inputs)

    analyzer = AudioboxAnalyzer(excerpt_seconds=60.0, predictor=Recorder())
    scores = analyzer.scores_for(audio, sr)

    assert scores == QualityScores(ce=7.0, cu=7.0, pc=4.0, pq=9.0)
    assert seen["length"] == 60 * sr
    assert seen["sr"] == sr


def test_audiobox_analyzer_returns_none_when_predictor_fails():
    class Boom:
        def forward(self, inputs):
            raise RuntimeError("model exploded")

    analyzer = AudioboxAnalyzer(excerpt_seconds=60.0, predictor=Boom())
    assert analyzer.scores_for(np.zeros(1000, dtype=np.float32), 100) is None
