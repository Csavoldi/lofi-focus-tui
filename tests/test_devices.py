from lofi_focus_tui.devices import DeviceInfo, choose_device


def test_choose_device_returns_cpu_when_no_runtime_available(monkeypatch):
    monkeypatch.setattr("lofi_focus_tui.devices._torch_device_summary", lambda: [])

    device = choose_device("auto")

    assert isinstance(device, DeviceInfo)
    assert device.backend == "cpu"
    assert device.available is True
