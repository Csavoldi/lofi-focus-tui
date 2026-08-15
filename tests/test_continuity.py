import numpy as np
import pytest

from lofi_focus_tui.audio.continuity import (
    ContinuityReport,
    analyze_boundary,
    analyze_chunk,
    continuation_notes,
)


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


def test_chunk_profile_reports_audio_metrics_and_json_values():
    profile = analyze_chunk(np.full(100, 0.05, dtype=np.float32), sample_rate=10)

    assert profile.rms == pytest.approx(0.05)
    assert profile.peak == pytest.approx(0.05)
    assert profile.silent is False
    assert profile.clipped is False
    assert profile.to_dict()["duration_seconds"] == pytest.approx(10.0)


def test_boundary_severity_distinguishes_large_loudness_jump():
    report = analyze_boundary(
        np.full(100, 0.05, dtype=np.float32),
        np.full(100, 0.90, dtype=np.float32),
        sample_rate=10,
    )

    assert report.accepted is False
    assert report.severe is True


def test_ordinary_loudness_warning_creates_next_chunk_note():
    report = analyze_boundary(
        np.full(100, 0.05, dtype=np.float32),
        np.full(100, 0.30, dtype=np.float32),
        sample_rate=10,
    )

    assert report.severe is False
    assert continuation_notes(report) == [
        "match the previous chunk's loudness at the transition"
    ]


def test_boundary_reports_spectral_change_as_ordinary_warning():
    sample_rate = 100
    time = np.arange(100, dtype=np.float32) / sample_rate
    left = 0.1 * np.sin(2 * np.pi * 2 * time)
    right = 0.1 * np.sin(2 * np.pi * 40 * time)

    report = analyze_boundary(left, right, sample_rate=sample_rate)

    assert "spectral change" in report.warnings
    assert report.severe is False
