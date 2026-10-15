from lofi_focus_tui.diagnostics import DiagnosticCheck, format_diagnostics, run_diagnostics


def test_run_diagnostics_reports_core_checks(tmp_path):
    checks = run_diagnostics(
        config_path=tmp_path / "missing.toml",
        cache_dir=tmp_path / "cache",
        import_checker=lambda module: module == "sys",
        service_probe=lambda base_url: False,
    )

    by_name = {check.name: check for check in checks}

    assert set(by_name) == {
        "python",
        "config",
        "ace-step",
        "sounddevice",
        "generation settings",
        "cache",
        "outputs",
        "ace-step service",
        "device",
    }
    assert by_name["python"].status == "ok"
    assert by_name["config"].status == "ok"
    assert by_name["cache"].status == "ok"
    assert by_name["outputs"].status == "ok"
    assert by_name["device"].status == "ok"
    assert by_name["ace-step"].status == "warn"
    assert by_name["sounddevice"].status == "warn"
    assert by_name["generation settings"].status == "ok"
    service = by_name["ace-step service"]
    assert service.status == "warn"
    assert "uv run acestep-api" in service.message


def test_run_diagnostics_reports_failed_config(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text("[generation]\nbackend = \"bad\"\n", encoding="utf-8")

    checks = run_diagnostics(
        config_path=config_path,
        cache_dir=tmp_path / "cache",
        import_checker=lambda module: False,
    )

    by_name = {check.name: check for check in checks}

    assert by_name["config"].status == "fail"


def test_format_diagnostics_outputs_status_lines():
    output = format_diagnostics(
        [
            DiagnosticCheck(name="python", status="ok", message="3.13"),
            DiagnosticCheck(name="ace-step", status="warn", message="not installed"),
        ]
    )

    assert "[ok] python: 3.13" in output
    assert "[warn] ace-step: not installed" in output


def test_run_diagnostics_warns_on_drifted_generation_settings(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "[generation]\nbackend = \"ace-step-http\"\ninference_steps = 27\n"
        "guidance_scale = 15.0\n",
        encoding="utf-8",
    )

    checks = run_diagnostics(
        config_path=config_path,
        cache_dir=tmp_path / "cache",
        import_checker=lambda module: False,
        service_probe=lambda base_url: True,
    )

    by_name = {check.name: check for check in checks}
    settings = by_name["generation settings"]
    assert settings.status == "warn"
    assert "inference_steps=27" in settings.message
    assert "docs/ace-step.md" in settings.message
    assert by_name["ace-step service"].status == "ok"


def test_run_diagnostics_reports_reachable_service(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "[generation]\nbackend = \"ace-step-http\"\n",
        encoding="utf-8",
    )
    probed = []

    checks = run_diagnostics(
        config_path=config_path,
        cache_dir=tmp_path / "cache",
        import_checker=lambda module: False,
        service_probe=lambda base_url: probed.append(base_url) or True,
    )

    by_name = {check.name: check for check in checks}
    assert by_name["ace-step service"].status == "ok"
    assert probed == ["http://127.0.0.1:8001"]
