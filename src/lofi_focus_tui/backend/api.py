import uvicorn
from fastapi import FastAPI

from lofi_focus_tui.audio.cache import default_history_path, default_output_dir
from lofi_focus_tui.audio.output import OutputManager
from lofi_focus_tui.audio.playback import PlaybackManager
from lofi_focus_tui.audio.player import NullPlayer, SoundDevicePlayer
from lofi_focus_tui.backend.session_manager import SessionManager
from lofi_focus_tui.config import AppConfig, GenerationConfig, PlaybackConfig, load_config
from lofi_focus_tui.domain import BackendStatus, SessionRequest
from lofi_focus_tui.generation.ace_step import AceStepAdapter
from lofi_focus_tui.generation.base import ModelAdapter
from lofi_focus_tui.generation.mock import MockModelAdapter
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


def _build_model(config: GenerationConfig) -> ModelAdapter:
    if config.backend == "mock":
        return MockModelAdapter()
    if config.backend == "ace-step":
        return AceStepAdapter(checkpoint_path=config.checkpoint_path)
    raise ValueError(f"Unsupported generation backend: {config.backend}")


def _build_playback(config: PlaybackConfig) -> PlaybackManager:
    player = SoundDevicePlayer() if SoundDevicePlayer.available() else NullPlayer()
    return PlaybackManager(player=player, volume=config.volume)


def _build_manager(config: AppConfig) -> SessionManager:
    return SessionManager(
        model=_build_model(config.generation),
        generation_defaults=config.generation.to_settings(),
        render_seconds_limit=config.generation.chunk_seconds,
        playback=_build_playback(config.playback),
        output_manager=OutputManager(default_output_dir()),
        history_store=HistoryStore(default_history_path()),
    )
