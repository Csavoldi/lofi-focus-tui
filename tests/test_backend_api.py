import pytest
from httpx import ASGITransport, AsyncClient

from lofi_focus_tui.backend.api import create_app
from lofi_focus_tui.backend.session_manager import SessionManager
from lofi_focus_tui.generation.mock import MockModelAdapter


@pytest.mark.asyncio
async def test_health_endpoint_reports_ready():
    transport = ASGITransport(app=create_app())

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["state"] == "idle"


@pytest.mark.asyncio
async def test_start_session_endpoint_returns_generating():
    manager = SessionManager(model=MockModelAdapter())
    transport = ASGITransport(app=create_app(manager=manager))

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/sessions",
            json={
                "preset": "deep_work",
                "duration_minutes": 30,
                "energy": "steady",
                "style_tags": ["lofi"],
                "avoid_tags": ["vocals"],
            },
        )

    assert response.status_code == 200
    assert response.json()["state"] == "generating"
    assert response.json()["active_task_id"] is not None

    manager.wait_for_active_task()


@pytest.mark.asyncio
async def test_status_endpoint_reports_playing_after_task_completes():
    manager = SessionManager(model=MockModelAdapter())
    transport = ASGITransport(app=create_app(manager=manager))

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        start_response = await client.post(
            "/sessions",
            json={
                "preset": "deep_work",
                "duration_minutes": 30,
                "energy": "steady",
                "style_tags": ["lofi"],
                "avoid_tags": ["vocals"],
            },
        )
        manager.wait_for_active_task()
        status_response = await client.get("/status")

    assert start_response.status_code == 200
    assert status_response.status_code == 200
    assert status_response.json()["state"] == "playing"
    assert status_response.json()["progress"] == 1.0
