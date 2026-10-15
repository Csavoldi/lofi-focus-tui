import importlib.util
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import httpx

from lofi_focus_tui.audio.cache import default_cache_dir, default_output_dir
from lofi_focus_tui.config import AppConfig, load_config
from lofi_focus_tui.devices import choose_device

DiagnosticStatus = Literal["ok", "warn", "fail"]
ImportChecker = Callable[[str], bool]
ServiceProbe = Callable[[str], bool]

# Turbo checkpoints are tuned for ~8 diffusion steps; far larger values only
# slow every generation down (guidance affects base/sft models only).
_RECOMMENDED_INFERENCE_STEPS = 8
_RECOMMENDED_GUIDANCE_SCALE = 7.0


@dataclass(frozen=True)
class DiagnosticCheck:
    name: str
    status: DiagnosticStatus
    message: str


def run_diagnostics(
    config_path: Path | None = None,
    cache_dir: Path | None = None,
    import_checker: ImportChecker | None = None,
    service_probe: ServiceProbe | None = None,
) -> list[DiagnosticCheck]:
    import_checker = import_checker or _module_available
    checks = [_check_python()]

    config: AppConfig | None = None
    try:
        config = load_config(config_path)
        checks.append(DiagnosticCheck("config", "ok", "loaded"))
    except Exception as exc:
        checks.append(DiagnosticCheck("config", "fail", str(exc)))

    checks.append(_check_optional_import("ace-step", "acestep", import_checker))
    checks.append(_check_optional_import("sounddevice", "sounddevice", import_checker))

    if config is not None:
        checks.append(_check_generation_settings(config))

    root = cache_dir or default_cache_dir()
    checks.append(_check_writable("cache", root))
    output_dir = (cache_dir / "outputs") if cache_dir else default_output_dir()
    checks.append(_check_writable("outputs", output_dir))

    if config is not None and config.generation.backend == "ace-step-http":
        checks.append(_check_ace_step_service(config, service_probe or _probe_http_service))

    device = choose_device("auto")
    device_status: DiagnosticStatus = "ok" if device.available else "warn"
    checks.append(DiagnosticCheck("device", device_status, f"{device.backend}: {device.name}"))
    return checks


def format_diagnostics(checks: list[DiagnosticCheck]) -> str:
    return "\n".join(f"[{check.status}] {check.name}: {check.message}" for check in checks)


def main() -> int:
    checks = run_diagnostics()
    print(format_diagnostics(checks))
    return 1 if any(check.status == "fail" for check in checks) else 0


def _check_python() -> DiagnosticCheck:
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    status: DiagnosticStatus = "ok" if sys.version_info >= (3, 10) else "fail"
    return DiagnosticCheck("python", status, version)


def _check_optional_import(
    name: str,
    module: str,
    import_checker: ImportChecker,
) -> DiagnosticCheck:
    if import_checker(module):
        return DiagnosticCheck(name, "ok", "installed")
    return DiagnosticCheck(name, "warn", "not installed")


def _check_writable(name: str, path: Path) -> DiagnosticCheck:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return DiagnosticCheck(name, "ok", str(path))
    except Exception as exc:
        return DiagnosticCheck(name, "fail", str(exc))


def _check_generation_settings(config: AppConfig) -> DiagnosticCheck:
    generation = config.generation
    drifted = (
        generation.inference_steps > 2 * _RECOMMENDED_INFERENCE_STEPS
        or generation.guidance_scale > _RECOMMENDED_GUIDANCE_SCALE + 3.0
    )
    summary = (
        f"inference_steps={generation.inference_steps}, "
        f"guidance_scale={generation.guidance_scale}"
    )
    if drifted:
        return DiagnosticCheck(
            "generation settings",
            "warn",
            f"{summary} is far from the turbo recommendation "
            f"({_RECOMMENDED_INFERENCE_STEPS} / {_RECOMMENDED_GUIDANCE_SCALE:g}); "
            "generations will be slower with no quality gain — see docs/ace-step.md",
        )
    return DiagnosticCheck("generation settings", "ok", summary)


def _check_ace_step_service(config: AppConfig, probe: ServiceProbe) -> DiagnosticCheck:
    base_url = config.ace_step_http.base_url
    try:
        reachable = probe(base_url)
    except Exception:
        reachable = False
    if reachable:
        return DiagnosticCheck("ace-step service", "ok", f"reachable at {base_url}")
    return DiagnosticCheck(
        "ace-step service",
        "warn",
        f"cannot reach {base_url} — start it on the GPU host with `uv run acestep-api` "
        "(see docs/ace-step.md); the app cannot generate until it answers",
    )


def _probe_http_service(base_url: str) -> bool:
    # The URL comes from the user's own config.toml and deliberately targets a
    # private LAN host (or localhost) running ACE-Step, so private ranges stay
    # allowed; only plain HTTP(S) is accepted and redirects are never followed
    # so a misconfigured URL cannot be bounced elsewhere.
    parsed = urlparse(base_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    response = httpx.get(
        f"{parsed.scheme}://{parsed.netloc}/health", timeout=5.0, follow_redirects=False
    )
    return response.is_success


def _module_available(module: str) -> bool:
    return importlib.util.find_spec(module) is not None
