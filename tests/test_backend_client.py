import pytest
from httpx import ASGITransport

from lofi_focus_tui.backend.api import create_app
from lofi_focus_tui.domain import EnergyLevel, SessionRequest
from lofi_focus_tui.tui.backend_client import BackendClient


@pytest.mark.asyncio
async def test_backend_client_gets_status_from_api():
    client = BackendClient(transport=ASGITransport(app=create_app()))

    status = await client.get_status()

    assert status.state == "idle"
    assert status.backend == "mock"


@pytest.mark.asyncio
async def test_backend_client_starts_session_through_api():
    client = BackendClient(transport=ASGITransport(app=create_app()))
    request = SessionRequest(
        preset="deep_work",
        duration_minutes=30,
        energy=EnergyLevel.STEADY,
        style_tags=["lofi"],
        avoid_tags=["vocals"],
    )

    status = await client.start_session(request)

    assert status.state == "playing"
    assert status.active_session_id is not None
