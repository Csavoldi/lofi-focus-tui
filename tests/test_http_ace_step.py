import io
import json
import wave

import httpx
import numpy as np
import pytest

from lofi_focus_tui.composition import create_blueprint
from lofi_focus_tui.domain import EnergyLevel, SessionRequest
from lofi_focus_tui.generation.http_ace_step import AceStepHttpAdapter, TaskResult
from lofi_focus_tui.generation.settings import GenerationSettings
from lofi_focus_tui.presets import expand_preset


def make_blueprint():
    plan = expand_preset(
        SessionRequest(
            preset="deep_work",
            duration_minutes=30,
            energy=EnergyLevel.STEADY,
            seed=123,
        )
    )
    return create_blueprint(plan)


def make_wav_bytes() -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(22050)
        wav.writeframes(np.array([0, 1200, -1200], dtype=np.int16).tobytes())
    return buffer.getvalue()


def test_http_adapter_health_reports_success_and_failure():
    success = AceStepHttpAdapter(
        base_url="http://ace.test",
        transport=httpx.MockTransport(lambda request: httpx.Response(200)),
    )
    failure = AceStepHttpAdapter(
        base_url="http://ace.test",
        transport=httpx.MockTransport(lambda request: httpx.Response(503)),
    )

    assert success.health() is True
    assert failure.health() is False


def test_task_result_parses_double_encoded_audio_result():
    result = TaskResult.from_payload(
        {
            "data": {
                "task_id": "task-1",
                "status": "succeeded",
                "result": json.dumps({"audio_path": "rendered.wav"}),
            }
        }
    )

    assert result.task_id == "task-1"
    assert result.status == "succeeded"
    assert result.audio.path == "rendered.wav"


def test_http_adapter_generates_audio_from_remote_task():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "POST" and request.url.path == "/release_task":
            payload = json.loads(request.content)
            assert payload["audio_duration"] == 1
            assert payload["infer_step"] == 12
            assert payload["manual_seeds"] == "456"
            assert "instrumental focus music" in payload["prompt"]
            assert request.headers["authorization"] == "Bearer secret"
            return httpx.Response(200, json={"task_id": "task-1"})
        if request.method == "POST" and request.url.path == "/query_result":
            return httpx.Response(
                200,
                json={
                    "task_id": "task-1",
                    "status": "succeeded",
                    "result": json.dumps({"path": "rendered.wav"}),
                },
            )
        if request.method == "GET" and request.url.path == "/v1/audio":
            assert request.url.params["path"] == "rendered.wav"
            return httpx.Response(200, content=make_wav_bytes())
        return httpx.Response(404)

    adapter = AceStepHttpAdapter(
        base_url="http://ace.test",
        api_key="secret",
        transport=httpx.MockTransport(handler),
        poll_interval_seconds=0.0,
    )
    settings = GenerationSettings(inference_steps=12, seed=456)

    result = adapter.generate(make_blueprint(), duration_seconds=1, settings=settings)

    assert result.sample_rate == 22050
    assert result.duration_seconds == 1
    assert result.audio.shape == (3,)
    assert result.metadata["backend"] == "ace-step-http"
    assert result.metadata["task_id"] == "task-1"
    assert result.metadata["path"] == "rendered.wav"
    assert [request.url.path for request in requests] == [
        "/release_task",
        "/query_result",
        "/v1/audio",
    ]


def test_http_adapter_raises_when_remote_task_fails():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/release_task":
            return httpx.Response(200, json={"task_id": "task-1"})
        return httpx.Response(
            200,
            json={"task_id": "task-1", "status": "failed", "error": "out of memory"},
        )

    adapter = AceStepHttpAdapter(
        base_url="http://ace.test",
        transport=httpx.MockTransport(handler),
        poll_interval_seconds=0.0,
    )

    with pytest.raises(RuntimeError, match="out of memory"):
        adapter.generate(make_blueprint(), duration_seconds=1)
