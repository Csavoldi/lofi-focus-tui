import pytest
from httpx import ASGITransport

from lofi_focus_tui.backend.api import create_app
from lofi_focus_tui.backend.session_manager import SessionManager
from lofi_focus_tui.config import ServerConfig
from lofi_focus_tui.domain import EnergyLevel, SessionRequest
from lofi_focus_tui.generation.mock import MockModelAdapter
from lofi_focus_tui.tui.backend_client import BackendClient


@pytest.mark.asyncio
async def test_backend_client_gets_status_from_api():
    client = BackendClient(transport=ASGITransport(app=create_app()))

    status = await client.get_status()

    assert status.state == "idle"
    assert status.backend == "mock"


@pytest.mark.asyncio
async def test_backend_client_starts_session_through_api():
    manager = SessionManager(model=MockModelAdapter())
    client = BackendClient(transport=ASGITransport(app=create_app(manager=manager)))
    request = SessionRequest(
        preset="deep_work",
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


def test_backend_client_uses_server_config_base_url():
    client = BackendClient.from_config(ServerConfig(host="0.0.0.0", port=9999))

    assert client.base_url == "http://0.0.0.0:9999"
