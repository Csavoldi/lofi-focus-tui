import subprocess
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceInfo:
    backend: str
    name: str
    available: bool
    recommended_render_seconds: int
    memory_total_mb: int | None = None


RunCommand = Callable[..., subprocess.CompletedProcess]


def _torch_device_summary() -> list[DeviceInfo]:
    try:
        import torch
    except Exception:
        return []

    devices: list[DeviceInfo] = []
    if torch.cuda.is_available():
        is_rocm = bool(getattr(torch.version, "hip", None))
        backend = "rocm" if is_rocm else "cuda"
        devices.append(DeviceInfo(backend, torch.cuda.get_device_name(0), True, 240))
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        devices.append(DeviceInfo("mps", "Apple Silicon MPS", True, 120))
    if hasattr(torch, "xpu") and torch.xpu.is_available():
        devices.append(DeviceInfo("xpu", "Intel XPU", True, 120))
    return devices


def nvidia_smi_summary(run: RunCommand = subprocess.run) -> list[DeviceInfo]:
    try:
        result = run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return []
    if result.returncode != 0:
        return []

    devices = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        name, memory = _parse_nvidia_smi_line(line)
        devices.append(
            DeviceInfo(
                backend="cuda",
                name=name,
                available=True,
                recommended_render_seconds=240,
                memory_total_mb=memory,
            )
        )
    return devices


def estimate_vram_gb(duration_seconds: int, batch_size: int) -> float:
    duration_factor = max(1.0, duration_seconds / 30.0)
    batch_factor = max(1, batch_size)
    return 2.0 + (duration_factor * batch_factor * 0.6)


def vram_warning(
    available_vram_gb: float,
    duration_seconds: int,
    batch_size: int,
) -> str | None:
    estimated = estimate_vram_gb(duration_seconds, batch_size)
    if estimated <= available_vram_gb:
        return None
    return (
        f"estimated VRAM {estimated:.1f} GB may exceed available "
        f"{available_vram_gb:.1f} GB"
    )


def choose_device(preference: str) -> DeviceInfo:
    devices = _torch_device_summary()
    if preference != "auto":
        for device in devices:
            if device.backend == preference:
                return device
        return DeviceInfo(preference, f"{preference} unavailable", False, 0)
    return devices[0] if devices else DeviceInfo("cpu", "CPU test mode", True, 30)


def _parse_nvidia_smi_line(line: str) -> tuple[str, int]:
    name, memory = line.rsplit(",", maxsplit=1)
    return name.strip(), int(memory.strip())
