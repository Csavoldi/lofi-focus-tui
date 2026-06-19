import pytest
from httpx import ASGITransport, AsyncClient

from lofi_focus_tui.backend.api import create_app


@pytest.mark.asyncio
async def test_health_endpoint_reports_ready():
    transport = ASGITransport(app=create_app())

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["state"] == "idle"


@pytest.mark.asyncio
async def test_start_session_endpoint_returns_playing():
    transport = ASGITransport(app=create_app())

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
    assert response.json()["state"] == "playing"
