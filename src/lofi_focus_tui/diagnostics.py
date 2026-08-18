import importlib.util
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from lofi_focus_tui.audio.cache import default_cache_dir, default_output_dir
from lofi_focus_tui.config import load_config
from lofi_focus_tui.devices import choose_device

DiagnosticStatus = Literal["ok", "warn", "fail"]
ImportChecker = Callable[[str], bool]


@dataclass(frozen=True)
class DiagnosticCheck:
    name: str
    status: DiagnosticStatus
    message: str


def run_diagnostics(
    config_path: Path | None = None,
    cache_dir: Path | None = None,
    import_checker: ImportChecker | None = None,
) -> list[DiagnosticCheck]:
    import_checker = import_checker or _module_available
    checks = [_check_python()]

    try:
        load_config(config_path)
        checks.append(DiagnosticCheck("config", "ok", "loaded"))
    except Exception as exc:
        checks.append(DiagnosticCheck("config", "fail", str(exc)))

    checks.append(_check_optional_import("ace-step", "acestep", import_checker))
    checks.append(_check_optional_import("sounddevice", "sounddevice", import_checker))

    root = cache_dir or default_cache_dir()
    checks.append(_check_writable("cache", root))
    output_dir = (cache_dir / "outputs") if cache_dir else default_output_dir()
    checks.append(_check_writable("outputs", output_dir))

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


def _module_available(module: str) -> bool:
    return importlib.util.find_spec(module) is not None
