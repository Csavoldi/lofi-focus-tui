try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


def test_ace_step_optional_dependency_name_matches_upstream_distribution():
    with open("pyproject.toml", "rb") as project_file:
        project = tomllib.load(project_file)

    ace_step_deps = project["project"]["optional-dependencies"]["ace-step"]

    assert ace_step_deps == ["ace-step @ git+https://github.com/ace-step/ACE-Step.git"]
