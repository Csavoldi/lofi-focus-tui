import uvicorn
from fastapi import FastAPI, HTTPException

from lofi_focus_tui.backend.session_manager import SessionManager
from lofi_focus_tui.config import load_config
from lofi_focus_tui.domain import (
    BackendStatus,
    ExportRequest,
    ExportResponse,
    SeekAdjustment,
    SessionRequest,
    VolumeAdjustment,
)
from lofi_focus_tui.runtime import (
    build_model,
    build_playback,
    build_session_manager,
)

_build_model = build_model
_build_playback = build_playback
_build_manager = build_session_manager


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

    @app.post("/sessions/volume", response_model=BackendStatus)
    async def adjust_volume(request: VolumeAdjustment) -> BackendStatus:
        session_manager.adjust_volume(request.delta)
        return session_manager.health()

    @app.post("/sessions/seek", response_model=BackendStatus)
    async def seek_session(request: SeekAdjustment) -> BackendStatus:
        session_manager.seek_playback(request.seconds)
        return session_manager.health()

    @app.post("/sessions/restart", response_model=BackendStatus)
    async def restart_session() -> BackendStatus:
        session_manager.restart_playback()
        return session_manager.health()

    @app.post("/sessions/export", response_model=ExportResponse)
    async def export_session(request: ExportRequest) -> ExportResponse:
        try:
            return session_manager.export_current(request.directory)
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except OSError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


def main() -> None:
    config = load_config()
    uvicorn.run(
        create_app(manager=_build_manager(config)),
        host=config.server.host,
        port=config.server.port,
    )
