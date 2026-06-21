import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised only on Python 3.10
    import tomli as tomllib


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8765


class GenerationConfig(BaseModel):
    backend: str = "mock"
    output_format: str = "wav"
    inference_steps: int = Field(default=27, ge=1, le=100)
    guidance_scale: float = Field(default=15.0, ge=0.0, le=30.0)
    batch_size: int = Field(default=1, ge=1, le=8)
    chunk_seconds: int = Field(default=30, ge=10, le=600)
    checkpoint_path: str = ""


class PlaybackConfig(BaseModel):
    volume: float = Field(default=0.8, ge=0.0, le=1.0)
    fade_seconds: float = Field(default=1.5, ge=0.0, le=10.0)


class AppConfig(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    playback: PlaybackConfig = Field(default_factory=PlaybackConfig)


DEFAULT_CONFIG_PATHS = [
    Path("config.toml"),
    Path.home() / ".config" / "lofi-focus-tui" / "config.toml",
]


def load_config(path: Path | None = None) -> AppConfig:
    config_path = _resolve_config_path(path)
    data: dict[str, Any] = {}
    if config_path is not None:
        with config_path.open("rb") as config_file:
            data = tomllib.load(config_file)

    config = AppConfig.model_validate(data)
    overrides: dict[str, Any] = {}
    if backend := os.environ.get("LOFI_BACKEND"):
        overrides["backend"] = backend
    if checkpoint_path := os.environ.get("ACESTEP_CHECKPOINT_PATH"):
        overrides["checkpoint_path"] = checkpoint_path
    if overrides:
        config = config.model_copy(
            update={
                "generation": config.generation.model_copy(update=overrides),
            }
        )
    return config


def _resolve_config_path(path: Path | None) -> Path | None:
    if path is not None:
        if path.exists():
            return path
    for default_path in DEFAULT_CONFIG_PATHS:
        if default_path.exists():
            return default_path
    return None
