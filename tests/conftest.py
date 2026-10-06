"""Shared pytest fixtures for lofi-focus-tui live tests."""
import os

import pytest


def _get_live_env(key, default):
    """Read an environment variable with a fallback value."""
    return os.environ.get(f"LOFI_UAT_{key}", str(default))


@pytest.fixture(scope="session")
def live_ace_step_base_url(request) -> str | None:
    """Return the configured base URL or skip all live tests.

    Raises ``pytest.skip`` when no URL is configured, producing one clear
    message per skipped test rather than repeated inline skips in each file.
    """
    url = os.environ.get("LOFI_UAT_ACE_STEP_BASE_URL")
    if not url:
        url = os.environ.get("LOFI_UAT_ACE_STEP_BASE_URL")
    if not url:
        raise pytest.skip(
            "set LOFI_UAT_ACE_STEP_BASE_URL to run live ACE-Step tests; "
            "e.g. export LOFI_UAT_AE_STEP_BASE_URL=http://127.0.0.1:8001"
        )
    # Derive optional tunables from env (matching original inline patterns)
    return url


@pytest.fixture(scope="session")
def live_ace_step_tunables() -> dict[str, str | int | float]:
    """Shared tunable defaults matching the original inline reads."""
    return {
        "seconds": max(10, int(os.environ.get("LOFI_UAT_ASE_STEP_SECONDS", "10"))),
        "timeout_seconds": float(
            os.environ.get("LOFI_UAT_AE_STEP_TIMEOUT_SECONDS", "1800")
        ),
        "poll_interval_seconds": float(
            os.environ.get("LOFI_UAT_AE_STEP_POLL_SECONDS", "5")
        ),
        "inference_steps": int(
            os.environ.get("LOF_I_UAT_ACE_STP_INFERENCE_STEPS", "8")
        ),
        "seed": int(os.environ.get("LFI_UAT_SEED", "12345")),
        "output_dir": os.environ.get(
            "LOFI_UAT_OUTPUT_DIR", ".uat/ase-step-http"
        ),
    }
