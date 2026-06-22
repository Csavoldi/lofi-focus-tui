import io
import json
import wave
from threading import Event

import httpx
import numpy as np
import pytest

from lofi_focus_tui.composition import create_blueprint
from lofi_focus_tui.domain import EnergyLevel, SessionRequest
from lofi_focus_tui.generation.base import GenerationCancelledError
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


def test_task_result_parses_ace_step_15_batch_audio_result():
    result = TaskResult.from_payload(
        {
            "data": [
                {
                    "task_id": "task-1",
                    "status": 1,
                    "result": json.dumps(
                        [
                            {
                                "file": "/v1/audio?path=%2Ftmp%2Fapi_audio%2Frendered.wav",
                                "lm_model": "acestep-5Hz-lm-0.6B",
                                "dit_model": "acestep-v15-turbo",
                            }
                        ]
                    ),
                }
            ]
        }
    )

    assert result.task_id == "task-1"
    assert result.status == "succeeded"
    assert result.audio.path == "/tmp/api_audio/rendered.wav"


def test_task_result_parses_ace_step_15_running_status():
    result = TaskResult.from_payload({"data": [{"task_id": "task-1", "status": 0}]})

    assert result.task_id == "task-1"
    assert result.status == "running"
    assert result.audio is None


def test_http_adapter_generates_audio_from_remote_task():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "POST" and request.url.path == "/release_task":
            payload = json.loads(request.content)
            assert payload["audio_duration"] == 10
            assert payload["inference_steps"] == 12
            assert payload["audio_format"] == "wav"
            assert payload["batch_size"] == 1
            assert payload["use_random_seed"] is False
            assert payload["seed"] == 456
            assert "instrumental focus music" in payload["prompt"]
            assert request.headers["authorization"] == "Bearer secret"
            return httpx.Response(200, json={"task_id": "task-1"})
        if request.method == "POST" and request.url.path == "/query_result":
            payload = json.loads(request.content)
            assert payload == {"task_id_list": ["task-1"]}
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "task_id": "task-1",
                            "status": 1,
                            "result": json.dumps(
                                [
                                    {
                                        "file": "/v1/audio?path=rendered.wav",
                                        "lm_model": "acestep-5Hz-lm-0.6B",
                                        "dit_model": "acestep-v15-turbo",
                                    }
                                ]
                            ),
                        }
                    ]
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

    result = adapter.generate(make_blueprint(), duration_seconds=10, settings=settings)

    assert result.sample_rate == 22050
    assert result.duration_seconds == 10
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
            json={"data": [{"task_id": "task-1", "status": 2, "error": "out of memory"}]},
        )

    adapter = AceStepHttpAdapter(
        base_url="http://ace.test",
        transport=httpx.MockTransport(handler),
        poll_interval_seconds=0.0,
    )

    with pytest.raises(RuntimeError, match="out of memory"):
        adapter.generate(make_blueprint(), duration_seconds=1)


def test_http_adapter_times_out_when_remote_task_never_finishes():
    now = [100.0]

    def clock() -> float:
        now[0] += 2.0
        return now[0]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/release_task":
            return httpx.Response(200, json={"task_id": "task-1"})
        return httpx.Response(200, json={"task_id": "task-1", "status": "running"})

    adapter = AceStepHttpAdapter(
        base_url="http://ace.test",
        transport=httpx.MockTransport(handler),
        timeout_seconds=1.0,
        poll_interval_seconds=0.0,
        clock=clock,
    )

    with pytest.raises(TimeoutError, match="timed out"):
        adapter.generate(make_blueprint(), duration_seconds=1)


def test_http_adapter_stops_polling_when_generation_is_cancelled():
    cancel_event = Event()
    query_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal query_count
        if request.url.path == "/release_task":
            return httpx.Response(200, json={"task_id": "task-1"})
        query_count += 1
        cancel_event.set()
        return httpx.Response(200, json={"task_id": "task-1", "status": "running"})

    adapter = AceStepHttpAdapter(
        base_url="http://ace.test",
        transport=httpx.MockTransport(handler),
        poll_interval_seconds=0.0,
    )

    with pytest.raises(GenerationCancelledError):
        adapter.generate(make_blueprint(), duration_seconds=1, cancel_event=cancel_event)

    assert query_count == 1
