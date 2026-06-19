from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceInfo:
    backend: str
    name: str
    available: bool
    recommended_render_seconds: int


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


def choose_device(preference: str) -> DeviceInfo:
    devices = _torch_device_summary()
    if preference != "auto":
        for device in devices:
            if device.backend == preference:
                return device
        return DeviceInfo(preference, f"{preference} unavailable", False, 0)
    return devices[0] if devices else DeviceInfo("cpu", "CPU test mode", True, 30)
