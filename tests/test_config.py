import pytest
from pydantic import ValidationError

from lofi_focus_tui.config import AppConfig, GenerationConfig, load_config


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


def test_invalid_backend_in_toml_raises_validation_error(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("[generation]\nbackend = \"acestep\"\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        load_config(path)


def test_invalid_output_format_in_toml_raises_validation_error(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("[generation]\noutput_format = \"mp3\"\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        load_config(path)


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


def test_invalid_env_backend_raises_validation_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LOFI_BACKEND", "acestep")

    with pytest.raises(ValidationError):
        load_config()


def test_env_overrides_ace_step_checkpoint_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ACESTEP_CHECKPOINT_PATH", "/models/ace-step")

    config = load_config()

    assert config.generation.checkpoint_path == "/models/ace-step"


def test_generation_config_to_settings_maps_defaults():
    config = GenerationConfig(
        output_format="wav",
        inference_steps=44,
        guidance_scale=7.5,
        batch_size=2,
    )

    settings = config.to_settings(seed=123)

    assert settings.output_format == "wav"
    assert settings.inference_steps == 44
    assert settings.guidance_scale == 7.5
    assert settings.batch_size == 2
    assert settings.seed == 123
