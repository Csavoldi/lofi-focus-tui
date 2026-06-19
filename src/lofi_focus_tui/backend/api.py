import uvicorn
from fastapi import FastAPI

from lofi_focus_tui.backend.session_manager import SessionManager
from lofi_focus_tui.domain import BackendStatus, SessionRequest
from lofi_focus_tui.generation.mock import MockModelAdapter


def create_app(manager: SessionManager | None = None) -> FastAPI:
    app = FastAPI(title="Lofi Focus Backend")
    session_manager = manager or SessionManager(model=MockModelAdapter())

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
    uvicorn.run(create_app(), host="127.0.0.1", port=8765)
