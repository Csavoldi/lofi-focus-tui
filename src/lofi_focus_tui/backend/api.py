import uvicorn
from fastapi import FastAPI

from lofi_focus_tui.audio.cache import default_history_path, default_output_dir
from lofi_focus_tui.audio.output import OutputManager
from lofi_focus_tui.audio.playback import PlaybackManager
from lofi_focus_tui.audio.player import NullPlayer, SoundDevicePlayer
from lofi_focus_tui.backend.session_manager import SessionManager
from lofi_focus_tui.config import (
    AceStepHttpConfig,
    AppConfig,
    GenerationConfig,
    PlaybackConfig,
    RunPodConfig,
    load_config,
)
from lofi_focus_tui.domain import BackendStatus, SessionRequest
from lofi_focus_tui.generation.ace_step import AceStepAdapter
from lofi_focus_tui.generation.base import ModelAdapter
from lofi_focus_tui.generation.http_ace_step import AceStepHttpAdapter
from lofi_focus_tui.generation.mock import MockModelAdapter
from lofi_focus_tui.generation.runpod import RunPodAceStepAdapter
from lofi_focus_tui.history import HistoryStore


def create_app(manager: SessionManager | None = None) -> FastAPI:
    app = FastAPI(title="Lofi Focus Backend")
    session_manager = manager or _build_manager(load_config())

    @app.get("/health", response_model=BackendStatus)
    async def health() -> BackendStatus:
        return session_manager.health()

    @app.get("/status", response_model=BackendStatus)
    async def status() -> BackendStatus:
        return session_manager.health()

    @app.post("/sessions", response_model=BackendStatus)
    async def start_session(request: SessionRequest) -> BackendStatus:
        return session_manager.start_session(request)

    @app.post("/sessions/pause", response_model=BackendStatus)
    async def pause_session() -> BackendStatus:
        return session_manager.pause_session()

    @app.post("/sessions/resume", response_model=BackendStatus)
    async def resume_session() -> BackendStatus:
        return session_manager.resume_session()

    @app.post("/sessions/stop", response_model=BackendStatus)
    async def stop_session() -> BackendStatus:
        return session_manager.stop_session()

    return app


def main() -> None:
    config = load_config()
    uvicorn.run(
        create_app(manager=_build_manager(config)),
        host=config.server.host,
        port=config.server.port,
    )


def _build_model(config: AppConfig | GenerationConfig) -> ModelAdapter:
    generation = config.generation if isinstance(config, AppConfig) else config
    http_config = config.ace_step_http if isinstance(config, AppConfig) else AceStepHttpConfig()
    runpod_config = config.runpod if isinstance(config, AppConfig) else RunPodConfig()

    if generation.backend == "mock":
        return MockModelAdapter()
    if generation.backend == "ace-step":
        return AceStepAdapter(checkpoint_path=generation.checkpoint_path)
    if generation.backend == "ace-step-http":
        return AceStepHttpAdapter(
            base_url=http_config.base_url,
            api_key=http_config.api_key,
            timeout_seconds=http_config.timeout_seconds,
        )
    if generation.backend == "runpod":
        return RunPodAceStepAdapter(
            api_key=runpod_config.api_key,
            gpu_type=runpod_config.gpu_type,
            template_id=runpod_config.template_id,
            volume_id=runpod_config.volume_id,
            auto_destroy=runpod_config.auto_destroy,
            base_url=http_config.base_url,
            timeout_seconds=http_config.timeout_seconds,
        )
    raise ValueError(f"Unsupported generation backend: {generation.backend}")


def _build_playback(config: PlaybackConfig) -> PlaybackManager:
    player = SoundDevicePlayer() if SoundDevicePlayer.available() else NullPlayer()
    return PlaybackManager(player=player, volume=config.volume, fade_seconds=config.fade_seconds)


def _build_manager(config: AppConfig) -> SessionManager:
    return SessionManager(
        model=_build_model(config),
        generation_defaults=config.generation.to_settings(),
        chunk_seconds=config.generation.chunk_seconds,
        playback=_build_playback(config.playback),
        output_manager=OutputManager(default_output_dir()),
        history_store=HistoryStore(default_history_path()),
    )
