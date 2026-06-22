import subprocess

from lofi_focus_tui.devices import (
    DeviceInfo,
    choose_device,
    estimate_vram_gb,
    nvidia_smi_summary,
    vram_warning,
)


def test_choose_device_returns_cpu_when_no_runtime_available(monkeypatch):
    monkeypatch.setattr("lofi_focus_tui.devices._torch_device_summary", lambda: [])

    device = choose_device("auto")

    assert isinstance(device, DeviceInfo)
    assert device.backend == "cpu"
    assert device.available is True


def test_nvidia_smi_summary_returns_empty_when_command_is_missing():
    def missing_runner(*args, **kwargs):
        raise FileNotFoundError

    assert nvidia_smi_summary(run=missing_runner) == []


def test_nvidia_smi_summary_parses_gpu_memory():
    def fake_runner(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="NVIDIA GeForce RTX 4090, 24564\n",
            stderr="",
        )

    devices = nvidia_smi_summary(run=fake_runner)

    assert devices == [
        DeviceInfo(
            backend="cuda",
            name="NVIDIA GeForce RTX 4090",
            available=True,
            recommended_render_seconds=240,
            memory_total_mb=24564,
        )
    ]


def test_vram_estimate_warns_without_failing_when_request_is_large():
    assert estimate_vram_gb(duration_seconds=120, batch_size=2) > estimate_vram_gb(
        duration_seconds=30,
        batch_size=1,
    )
    assert vram_warning(available_vram_gb=4.0, duration_seconds=600, batch_size=8) is not None
    assert vram_warning(available_vram_gb=24.0, duration_seconds=30, batch_size=1) is None
