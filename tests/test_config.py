from lofi_focus_tui.config import AppConfig, load_config


def test_default_config_loads_without_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    config = load_config()

    assert isinstance(config, AppConfig)
    assert config.server.host == "127.0.0.1"
    assert config.server.port == 8765
    assert config.generation.backend == "mock"
    assert config.generation.checkpoint_path == ""


def test_config_loads_from_explicit_toml(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        "[generation]\nbackend = \"ace-step\"\nchunk_seconds = 60\n",
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.generation.backend == "ace-step"
    assert config.generation.chunk_seconds == 60


def test_missing_explicit_config_path_falls_back_to_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    default_path = tmp_path / "config.toml"
    default_path.write_text(
        "[generation]\nbackend = \"ace-step\"\nchunk_seconds = 60\n",
        encoding="utf-8",
    )

    config = load_config(tmp_path / "missing.toml")

    assert config.generation.backend == "ace-step"
    assert config.generation.chunk_seconds == 60


def test_env_overrides_backend(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LOFI_BACKEND", "ace-step")

    config = load_config()

    assert config.generation.backend == "ace-step"


def test_env_overrides_ace_step_checkpoint_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ACESTEP_CHECKPOINT_PATH", "/models/ace-step")

    config = load_config()

    assert config.generation.checkpoint_path == "/models/ace-step"
