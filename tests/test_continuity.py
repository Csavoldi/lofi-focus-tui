import numpy as np
import pytest

from lofi_focus_tui.audio.continuity import ContinuityReport, analyze_boundary


def test_boundary_detects_loudness_jump():
    left = np.zeros(44100, dtype=np.float32)
    right = np.ones(44100, dtype=np.float32)

    report = analyze_boundary(left, right)

    assert isinstance(report, ContinuityReport)
    assert report.accepted is False
    assert "loudness jump" in report.reasons


def test_boundary_report_includes_metrics_and_warnings():
    left = np.full(100, 0.05, dtype=np.float32)
    right = np.full(100, 0.06, dtype=np.float32)

    report = analyze_boundary(left, right)

    assert report.left_rms > 0.0
    assert report.right_rms > 0.0
    assert report.boundary_delta == pytest.approx(0.01)
    assert report.warnings == []
    assert report.reasons == report.warnings


def test_boundary_rejects_silent_audio():
    left = np.zeros(100, dtype=np.float32)
    right = np.full(100, 0.05, dtype=np.float32)

    report = analyze_boundary(left, right)

    assert report.accepted is False
    assert "silent audio" in report.warnings


def test_boundary_rejects_clipped_audio():
    left = np.full(100, 0.05, dtype=np.float32)
    right = np.array([0.05, 0.995], dtype=np.float32)

    report = analyze_boundary(left, right)

    assert report.accepted is False
    assert "clipping" in report.warnings


def test_boundary_accepts_similar_audio():
    left = np.full(44100, 0.05, dtype=np.float32)
    right = np.full(44100, 0.052, dtype=np.float32)

    report = analyze_boundary(left, right)

    assert report.accepted is True
