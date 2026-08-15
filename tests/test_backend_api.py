import pytest
from httpx import ASGITransport, AsyncClient

from lofi_focus_tui.audio.output import OutputManager
from lofi_focus_tui.audio.player import NullPlayer, SoundDevicePlayer
from lofi_focus_tui.backend.api import _build_model, _build_playback, create_app
from lofi_focus_tui.backend.session_manager import SessionManager
from lofi_focus_tui.config import AppConfig, GenerationConfig, PlaybackConfig
from lofi_focus_tui.generation.ace_step import AceStepAdapter
from lofi_focus_tui.generation.http_ace_step import AceStepHttpAdapter
from lofi_focus_tui.generation.mock import MockModelAdapter
from lofi_focus_tui.generation.runpod import RunPodAceStepAdapter


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
                "focus": "deep_work",
                "preset": "classic_lofi",
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
                "focus": "deep_work",
                "preset": "classic_lofi",
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


@pytest.mark.asyncio
async def test_playback_control_endpoints_update_status():
    manager = SessionManager(model=MockModelAdapter(), render_seconds_limit=1)
    transport = ASGITransport(app=create_app(manager=manager))

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/sessions",
            json={
                "preset": "classic_lofi",
                "duration_minutes": 5,
                "energy": "steady",
            },
        )
        manager.wait_for_active_task()
        volume_response = await client.post("/sessions/volume", json={"delta": 0.1})
        seek_response = await client.post("/sessions/seek", json={"seconds": 10})
        restart_response = await client.post("/sessions/restart")

    assert volume_response.status_code == 200
    assert volume_response.json()["volume"] == 0.9
    assert seek_response.status_code == 200
    assert seek_response.json()["position_seconds"] == 1.0
    assert restart_response.status_code == 200
    assert restart_response.json()["position_seconds"] == 0.0


@pytest.mark.asyncio
async def test_export_endpoint_copies_completed_session_files(tmp_path):
    manager = SessionManager(
        model=MockModelAdapter(),
        render_seconds_limit=1,
        output_manager=OutputManager(tmp_path / "cache"),
    )
    transport = ASGITransport(app=create_app(manager=manager))

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/sessions",
            json={
                "preset": "classic_lofi",
                "duration_minutes": 5,
                "energy": "steady",
            },
        )
        manager.wait_for_active_task()
        response = await client.post(
            "/sessions/export",
            json={"directory": str(tmp_path / "exports")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "session exported"
    assert body["audio_path"].endswith("/audio.wav")
    assert body["metadata_path"].endswith("/metadata.json")


@pytest.mark.asyncio
async def test_export_endpoint_rejects_missing_completed_session():
    transport = ASGITransport(app=create_app(manager=SessionManager(model=MockModelAdapter())))

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/sessions/export",
            json={"directory": "/tmp/lofi-focus-export-test"},
        )

    assert response.status_code == 409


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {
            "focus": "unknown",
            "preset": "classic_lofi",
            "duration_minutes": 30,
            "energy": "steady",
        },
        {
            "focus": "deep_work",
            "preset": "unknown",
            "duration_minutes": 30,
            "energy": "steady",
        },
        {
            "focus": "coding",
            "preset": "reading",
            "duration_minutes": 30,
            "energy": "steady",
        },
    ],
)
async def test_start_session_rejects_invalid_request_at_boundary(payload):
    transport = ASGITransport(app=create_app(manager=SessionManager(model=MockModelAdapter())))

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/sessions", json=payload)

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"preset": [], "duration_minutes": 30, "energy": "steady"},
        {"preset": {}, "duration_minutes": 30, "energy": "steady"},
        {
            "focus": [],
            "preset": "classic_lofi",
            "duration_minutes": 30,
            "energy": "steady",
        },
        {
            "focus": {},
            "preset": "classic_lofi",
            "duration_minutes": 30,
            "energy": "steady",
        },
    ],
)
async def test_start_session_rejects_non_string_option_shapes_at_boundary(payload):
    transport = ASGITransport(app=create_app(manager=SessionManager(model=MockModelAdapter())))

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/sessions", json=payload)

    assert response.status_code == 422


def test_build_playback_uses_null_player_without_sounddevice(monkeypatch):
    monkeypatch.setattr(SoundDevicePlayer, "available", staticmethod(lambda: False))

    playback = _build_playback(PlaybackConfig(volume=0.25, fade_seconds=2.0))

    assert isinstance(playback.player, NullPlayer)
    assert playback.volume == 0.25
    assert playback.fade_seconds == 2.0


def test_build_playback_uses_sounddevice_player_when_available(monkeypatch):
    monkeypatch.setattr(SoundDevicePlayer, "available", staticmethod(lambda: True))

    playback = _build_playback(PlaybackConfig(volume=0.5))

    assert isinstance(playback.player, SoundDevicePlayer)
    assert playback.volume == 0.5


def test_build_model_selects_configured_generation_backend():
    assert isinstance(_build_model(AppConfig()), MockModelAdapter)
    assert isinstance(
        _build_model(AppConfig(generation=GenerationConfig(backend="ace-step"))),
        AceStepAdapter,
    )
    assert isinstance(
        _build_model(AppConfig(generation=GenerationConfig(backend="ace-step-http"))),
        AceStepHttpAdapter,
    )
    assert isinstance(
        _build_model(AppConfig(generation=GenerationConfig(backend="runpod"))),
        RunPodAceStepAdapter,
    )
