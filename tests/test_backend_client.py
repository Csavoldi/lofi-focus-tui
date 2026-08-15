import pytest
from httpx import ASGITransport

from lofi_focus_tui.audio.output import OutputManager
from lofi_focus_tui.backend.api import create_app
from lofi_focus_tui.backend.session_manager import SessionManager
from lofi_focus_tui.config import ServerConfig
from lofi_focus_tui.domain import EnergyLevel, SessionRequest
from lofi_focus_tui.generation.mock import MockModelAdapter
from lofi_focus_tui.tui.backend_client import BackendClient


@pytest.mark.asyncio
async def test_backend_client_gets_status_from_api():
    client = BackendClient(
        transport=ASGITransport(
            app=create_app(manager=SessionManager(model=MockModelAdapter()))
        )
    )

    status = await client.get_status()

    assert status.state == "idle"
    assert status.backend == "mock"


@pytest.mark.asyncio
async def test_backend_client_starts_session_through_api():
    manager = SessionManager(model=MockModelAdapter())
    client = BackendClient(transport=ASGITransport(app=create_app(manager=manager)))
    request = SessionRequest(
        focus="deep_work",
        preset="classic_lofi",
        duration_minutes=30,
        energy=EnergyLevel.STEADY,
        style_tags=["lofi"],
        avoid_tags=["vocals"],
    )

    status = await client.start_session(request)

    assert status.state == "generating"
    assert status.active_session_id is not None
    assert status.active_task_id is not None

    manager.wait_for_active_task()
    final_status = await client.get_status()

    assert final_status.state == "playing"


@pytest.mark.asyncio
async def test_backend_client_controls_session_through_api():
    manager = SessionManager(model=MockModelAdapter())
    client = BackendClient(transport=ASGITransport(app=create_app(manager=manager)))
    request = SessionRequest(
        focus="deep_work",
        preset="classic_lofi",
        duration_minutes=30,
        energy=EnergyLevel.STEADY,
        style_tags=["lofi"],
        avoid_tags=["vocals"],
    )

    await client.start_session(request)
    manager.wait_for_active_task()

    paused = await client.pause_session()
    resumed = await client.resume_session()
    louder = await client.adjust_volume(0.1)
    forward = await client.seek(10.0)
    restarted = await client.restart()
    stopped = await client.stop_session()

    assert paused.state == "paused"
    assert resumed.state == "playing"
    assert louder.volume == 0.9
    assert forward.position_seconds >= 0.0
    assert restarted.position_seconds == 0.0
    assert stopped.state == "idle"


@pytest.mark.asyncio
async def test_backend_client_exports_session_through_api(tmp_path):
    manager = SessionManager(
        model=MockModelAdapter(),
        render_seconds_limit=1,
        output_manager=OutputManager(tmp_path / "cache"),
    )
    client = BackendClient(transport=ASGITransport(app=create_app(manager=manager)))
    request = SessionRequest(
        preset="classic_lofi",
        duration_minutes=5,
        energy=EnergyLevel.STEADY,
    )

    await client.start_session(request)
    manager.wait_for_active_task()
    response = await client.export_session(str(tmp_path / "exports"))

    assert response.message == "session exported"
    assert response.audio_path.endswith("/audio.wav")


def test_backend_client_uses_server_config_base_url():
    client = BackendClient.from_config(ServerConfig(host="0.0.0.0", port=9999))

    assert client.base_url == "http://0.0.0.0:9999"
