import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from lofi_focus_tui.audio.normalization import is_clipped, is_silent, peak, rms
from lofi_focus_tui.audio.output import OutputManager
from lofi_focus_tui.composition import create_blueprint
from lofi_focus_tui.domain import EnergyLevel, SessionRequest
from lofi_focus_tui.generation.http_ace_step import AceStepHttpAdapter
from lofi_focus_tui.generation.settings import GenerationSettings
from lofi_focus_tui.presets import expand_preset


def test_live_ace_step_15_http_generates_valid_focus_audio():
    base_url = os.environ.get("LOFI_UAT_ACE_STEP_BASE_URL")
    if not base_url:
        pytest.skip("set LOFI_UAT_ACE_STEP_BASE_URL to run the live ACE-Step-1.5 HTTP gate")

    duration_seconds = max(10, int(os.environ.get("LOFI_UAT_ACE_STEP_SECONDS", "10")))
    timeout_seconds = float(os.environ.get("LOFI_UAT_ACE_STEP_TIMEOUT_SECONDS", "1800"))
    poll_interval_seconds = float(os.environ.get("LOFI_UAT_ACE_STEP_POLL_SECONDS", "5"))
    inference_steps = int(os.environ.get("LOFI_UAT_ACE_STEP_INFERENCE_STEPS", "8"))
    seed = int(os.environ.get("LOFI_UAT_ACE_STEP_SEED", "12345"))
    output_root = Path(os.environ.get("LOFI_UAT_OUTPUT_DIR", ".uat/ace-step-http"))

    adapter = AceStepHttpAdapter(
        base_url=base_url,
        api_key=os.environ.get("LOFI_UAT_ACE_STEP_API_KEY", ""),
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
    )
    assert adapter.health(), f"ACE-Step-1.5 HTTP service is not healthy at {base_url}"

    request = SessionRequest(
        preset="deep_work",
        duration_minutes=5,
        energy=EnergyLevel.STEADY,
        style_tags=["lofi", "instrumental", "warm tape"],
        avoid_tags=["vocals", "speech", "harsh clipping"],
        seed=seed,
    )
    blueprint = create_blueprint(expand_preset(request))
    settings = GenerationSettings(
        output_format="wav",
        inference_steps=inference_steps,
        batch_size=1,
        seed=seed,
    )

    result = adapter.generate(
        blueprint=blueprint,
        duration_seconds=duration_seconds,
        settings=settings,
    )
    audio_rms = rms(result.audio)
    audio_peak = peak(result.audio)

    assert result.sample_rate > 0
    assert result.audio.size >= result.sample_rate * max(1, duration_seconds - 2)
    assert not is_silent(result.audio)
    assert not is_clipped(result.audio)

    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_manager = OutputManager(output_root)
    run_dir = output_manager.create_session_dir(run_id, "ace_step_15_http_uat")
    audio_path = output_manager.save_wav(result, run_dir)
    metadata_path = output_manager.save_metadata(
        {
            "base_url": base_url,
            "duration_seconds": duration_seconds,
            "inference_steps": inference_steps,
            "sample_rate": result.sample_rate,
            "samples": int(result.audio.size),
            "rms": audio_rms,
            "peak": audio_peak,
            "generation_metadata": result.metadata,
        },
        run_dir,
    )

    assert audio_path.exists()
    assert metadata_path.exists()
