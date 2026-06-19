import numpy as np

from lofi_focus_tui.audio.continuity import ContinuityReport, analyze_boundary


def test_boundary_detects_loudness_jump():
    left = np.zeros(44100, dtype=np.float32)
    right = np.ones(44100, dtype=np.float32)

    report = analyze_boundary(left, right)

    assert isinstance(report, ContinuityReport)
    assert report.accepted is False
    assert "loudness jump" in report.reasons


def test_boundary_accepts_similar_audio():
    left = np.full(44100, 0.05, dtype=np.float32)
    right = np.full(44100, 0.052, dtype=np.float32)

    report = analyze_boundary(left, right)

    assert report.accepted is True
