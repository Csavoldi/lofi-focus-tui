import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from lofi_focus_tui.generation.settings import GenerationSettings

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised only on Python 3.10
    import tomli as tomllib


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8765


class GenerationConfig(BaseModel):
    backend: Literal["mock", "ace-step", "ace-step-http", "runpod"] = "mock"
    output_format: Literal["wav"] = "wav"
    inference_steps: int = Field(default=27, ge=1, le=100)
    guidance_scale: float = Field(default=15.0, ge=0.0, le=30.0)
    batch_size: int = Field(default=1, ge=1, le=8)
    chunk_seconds: int = Field(default=30, ge=10, le=600)
    checkpoint_path: str = ""

    def to_settings(self, seed: int = -1) -> GenerationSettings:
        return GenerationSettings(
            output_format=self.output_format,
            inference_steps=self.inference_steps,
            guidance_scale=self.guidance_scale,
            batch_size=self.batch_size,
            seed=seed,
        )


class PlaybackConfig(BaseModel):
    volume: float = Field(default=0.8, ge=0.0, le=1.0)
    fade_seconds: float = Field(default=1.5, ge=0.0, le=10.0)


class AceStepHttpConfig(BaseModel):
    base_url: str = "http://127.0.0.1:8001"
    api_key: str = ""
    timeout_seconds: float = Field(default=1800.0, gt=0.0)


class RunPodConfig(BaseModel):
    api_key: str = ""
    gpu_type: str = "NVIDIA GeForce RTX 4090"
    template_id: str = ""
    volume_id: str = ""
    auto_destroy: bool = True


class AppConfig(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    playback: PlaybackConfig = Field(default_factory=PlaybackConfig)
    ace_step_http: AceStepHttpConfig = Field(default_factory=AceStepHttpConfig)
    runpod: RunPodConfig = Field(default_factory=RunPodConfig)


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
        data = config.model_dump()
        data["generation"].update(overrides)
        config = AppConfig.model_validate(data)
    return config


def _resolve_config_path(path: Path | None) -> Path | None:
    if path is not None:
        if path.exists():
            return path
    for default_path in DEFAULT_CONFIG_PATHS:
        if default_path.exists():
            return default_path
    return None
