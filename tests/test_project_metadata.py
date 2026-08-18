from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


PROJECT_ROOT = Path(__file__).parents[1]


def test_ace_step_optional_dependency_name_matches_upstream_distribution():
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as project_file:
        project = tomllib.load(project_file)

    ace_step_deps = project["project"]["optional-dependencies"]["ace-step"]

    assert ace_step_deps == ["ace-step @ git+https://github.com/ace-step/ACE-Step.git"]


def test_console_scripts_expose_only_process_local_commands():
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as project_file:
        project = tomllib.load(project_file)

    assert project["project"]["scripts"] == {
        "lofi": "lofi_focus_tui.cli:main",
        "lofi-doctor": "lofi_focus_tui.diagnostics:main",
    }


def test_dependencies_keep_httpx_without_local_http_server_packages():
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as project_file:
        project = tomllib.load(project_file)

    dependencies = project["project"]["dependencies"]

    assert any(dependency.startswith("httpx") for dependency in dependencies)
    removed_dependencies = ("fast" + "api", "uvic" + "orn")
    assert not any(
        dependency.startswith(name)
        for dependency in dependencies
        for name in removed_dependencies
    )


def test_obsolete_local_http_boundary_files_are_absent():
    assert not (PROJECT_ROOT / "src/lofi_focus_tui/backend/api.py").exists()
    assert not (PROJECT_ROOT / "src/lofi_focus_tui/tui/backend_client.py").exists()
