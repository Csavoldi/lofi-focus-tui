from lofi_focus_tui.diagnostics import DiagnosticCheck, format_diagnostics, run_diagnostics


def test_run_diagnostics_reports_core_checks(tmp_path):
    checks = run_diagnostics(
        config_path=tmp_path / "missing.toml",
        cache_dir=tmp_path / "cache",
        port_probe=lambda host, port: True,
        import_checker=lambda module: module == "sys",
    )

    by_name = {check.name: check for check in checks}

    assert by_name["python"].status == "ok"
    assert by_name["config"].status == "ok"
    assert by_name["backend"].status == "ok"
    assert by_name["cache"].status == "ok"
    assert by_name["outputs"].status == "ok"
    assert by_name["device"].status == "ok"
    assert by_name["ace-step"].status == "warn"
    assert by_name["sounddevice"].status == "warn"


def test_run_diagnostics_reports_failed_config(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text("[generation]\nbackend = \"bad\"\n", encoding="utf-8")

    checks = run_diagnostics(
        config_path=config_path,
        cache_dir=tmp_path / "cache",
        port_probe=lambda host, port: False,
        import_checker=lambda module: False,
    )

    by_name = {check.name: check for check in checks}

    assert by_name["config"].status == "fail"
    assert by_name["backend"].status == "warn"


def test_format_diagnostics_outputs_status_lines():
    output = format_diagnostics(
        [
            DiagnosticCheck(name="python", status="ok", message="3.13"),
            DiagnosticCheck(name="ace-step", status="warn", message="not installed"),
        ]
    )

    assert "[ok] python: 3.13" in output
    assert "[warn] ace-step: not installed" in output
