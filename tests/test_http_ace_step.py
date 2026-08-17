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
from lofi_focus_tui.generation.prompt_engine import compose_local_prompt
from lofi_focus_tui.generation.runpod import RunPodAceStepAdapter
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
    blueprint = make_blueprint().model_copy(update={"prompt": "late-night rainy room"})

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "POST" and request.url.path == "/format_input":
            assert request.headers["authorization"] == "Bearer secret"
            assert request.extensions["timeout"] == {
                "connect": 30.0,
                "read": 30.0,
                "write": 30.0,
                "pool": 30.0,
            }
            assert json.loads(request.content) == {
                "prompt": local_prompt,
                "lyrics": "[Instrumental]",
                "temperature": 0.85,
                "param_obj": (
                    f'{{"bpm":{blueprint.tempo_bpm},"duration":10,"key":"minor pentatonic",'
                    '"language":"unknown","time_signature":"4"}'
                ),
            }
            return httpx.Response(
                200,
                json={"data": {"caption": "formatted rainy room"}},
            )
        if request.method == "POST" and request.url.path == "/release_task":
            payload = json.loads(request.content)
            assert set(payload) == {
                "audio_duration",
                "prompt",
                "lyrics",
                "thinking",
                "inference_steps",
                "guidance_scale",
                "audio_format",
                "batch_size",
                "use_random_seed",
                "seed",
            }
            assert payload["audio_duration"] == 10
            assert payload["inference_steps"] == 12
            assert payload["audio_format"] == "wav"
            assert payload["batch_size"] == 1
            assert payload["use_random_seed"] is False
            assert payload["seed"] == 456
            assert payload["prompt"] == "late-night rainy room. formatted rainy room"
            assert payload["lyrics"] == "[Instrumental]"
            assert payload["thinking"] is False
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

    blueprint = blueprint.model_copy(
        update={"continuation_constraints": ["match the previous chunk's loudness"]}
    )
    local_prompt = compose_local_prompt(blueprint)
    result = adapter.generate(blueprint, duration_seconds=10, settings=settings)

    assert result.sample_rate == 22050
    assert result.duration_seconds == 10
    assert result.audio.shape == (3,)
    assert result.metadata["backend"] == "ace-step-http"
    assert result.metadata["task_id"] == "task-1"
    assert result.metadata["path"] == "rendered.wav"
    assert [request.url.path for request in requests] == [
        "/format_input",
        "/release_task",
        "/query_result",
        "/v1/audio",
    ]


def test_http_adapter_omits_seed_only_for_random_seed_payload():
    payloads = {}

    def handler(request: httpx.Request) -> httpx.Response:
        payloads[request.url.path] = json.loads(request.content)
        if request.url.path == "/format_input":
            return httpx.Response(200, json={"data": {"caption": "caption"}})
        return httpx.Response(200, json={"task_id": "task-1"})

    adapter = AceStepHttpAdapter(
        base_url="http://ace.test",
        transport=httpx.MockTransport(handler),
    )
    settings = GenerationSettings(seed=-1)
    blueprint = make_blueprint().model_copy(update={"seed": -1})

    adapter.submit_task(blueprint, duration_seconds=10, settings=settings)

    assert set(payloads["/release_task"]) == {
        "audio_duration",
        "prompt",
        "lyrics",
        "thinking",
        "inference_steps",
        "guidance_scale",
        "audio_format",
        "batch_size",
        "use_random_seed",
    }
    assert payloads["/release_task"]["use_random_seed"] is True


def _generate_with_format_response(format_response, blueprint=None):
    requests = []
    blueprint = blueprint or make_blueprint()
    local_prompt = compose_local_prompt(blueprint)

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/format_input":
            if isinstance(format_response, BaseException):
                raise format_response
            if isinstance(format_response, httpx.Response):
                return format_response
            return httpx.Response(200, json=format_response)
        if request.url.path == "/release_task":
            assert json.loads(request.content)["prompt"] == local_prompt
            return httpx.Response(200, json={"task_id": "task-1"})
        if request.url.path == "/query_result":
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "task_id": "task-1",
                            "status": 1,
                            "result": json.dumps({"audio_path": "rendered.wav"}),
                        }
                    ]
                },
            )
        if request.url.path == "/v1/audio":
            return httpx.Response(200, content=make_wav_bytes())
        return httpx.Response(404)

    adapter = AceStepHttpAdapter(
        base_url="http://ace.test",
        transport=httpx.MockTransport(handler),
        poll_interval_seconds=0.0,
    )
    result = adapter.generate(blueprint, duration_seconds=1)
    return result, requests


@pytest.mark.parametrize(
    "failure",
    [
        httpx.ConnectError("connection refused"),
        httpx.ReadTimeout("timed out"),
        httpx.Response(503),
        httpx.Response(200, content=b"not json"),
        {"data": []},
        {"data": {}},
        {"data": {"caption": None}},
        {"data": {"caption": 123}},
        {"data": {"caption": "  "}},
        {"data": {"caption": "x" * 513}},
    ],
    ids=[
        "connection",
        "timeout",
        "http",
        "invalid-json",
        "non-dictionary-data",
        "missing-caption",
        "missing-caption-value",
        "non-string-caption",
        "blank-caption",
        "overlong-caption",
    ],
)
def test_http_adapter_falls_back_to_local_prompt_for_enrichment_failures(failure):
    result, requests = _generate_with_format_response(failure)

    assert result.sample_rate == 22050
    assert [request.url.path for request in requests].count("/format_input") == 1
    assert [request.url.path for request in requests] == [
        "/format_input",
        "/release_task",
        "/query_result",
        "/v1/audio",
    ]


@pytest.mark.parametrize("lyrics", [123, "  ", "x" * 4097])
def test_http_adapter_ignores_invalid_optional_lyrics(lyrics):
    blueprint = make_blueprint().model_copy(
        update={"prompt": "user wording", "vocal_mode": "vocals"}
    )
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/format_input":
            return httpx.Response(
                200,
                json={"data": {"caption": "generated caption", "lyrics": lyrics}},
            )
        if request.url.path == "/release_task":
            payload = json.loads(request.content)
            assert payload["prompt"] == "user wording. generated caption"
            assert payload["lyrics"] == ""
            assert payload["thinking"] is True
            return httpx.Response(200, json={"task_id": "task-1"})
        if request.url.path == "/query_result":
            return httpx.Response(
                200,
                json={"task_id": "task-1", "status": "done", "result": "rendered.wav"},
            )
        return httpx.Response(200, content=make_wav_bytes())

    adapter = AceStepHttpAdapter(
        base_url="http://ace.test",
        transport=httpx.MockTransport(handler),
        poll_interval_seconds=0.0,
    )
    adapter.generate(blueprint, duration_seconds=1)

    assert [request.url.path for request in requests][:2] == ["/format_input", "/release_task"]


@pytest.mark.parametrize("returned_lyrics", ["[Verse]\nhello", None])
def test_http_adapter_vocal_payload_uses_returned_or_empty_lyrics(returned_lyrics):
    blueprint = make_blueprint().model_copy(update={"vocal_mode": "vocals"})
    response_data = {"caption": "caption"}
    if returned_lyrics is not None:
        response_data["lyrics"] = returned_lyrics
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/format_input":
            assert json.loads(request.content)["lyrics"] == ""
            return httpx.Response(200, json={"data": response_data})
        if request.url.path == "/release_task":
            payload = json.loads(request.content)
            assert payload["lyrics"] == (returned_lyrics or "")
            assert payload["thinking"] is True
            return httpx.Response(200, json={"task_id": "task-1"})
        if request.url.path == "/query_result":
            return httpx.Response(
                200,
                json={"task_id": "task-1", "status": "done", "result": "rendered.wav"},
            )
        return httpx.Response(200, content=make_wav_bytes())

    adapter = AceStepHttpAdapter(
        base_url="http://ace.test",
        transport=httpx.MockTransport(handler),
        poll_interval_seconds=0.0,
    )
    adapter.generate(blueprint, duration_seconds=1)


def test_runpod_adapter_inherits_vocal_http_payload():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/format_input":
            return httpx.Response(200, json={"data": {"caption": "caption", "lyrics": "verse"}})
        if request.url.path == "/release_task":
            payload = json.loads(request.content)
            assert payload["lyrics"] == "verse"
            assert payload["thinking"] is True
            assert request.headers["authorization"] == "Bearer secret"
            return httpx.Response(200, json={"task_id": "task-1"})
        if request.url.path == "/query_result":
            return httpx.Response(
                200,
                json={"task_id": "task-1", "status": "done", "result": "rendered.wav"},
            )
        return httpx.Response(200, content=make_wav_bytes())

    adapter = RunPodAceStepAdapter(
        api_key="secret",
        base_url="http://runpod.test",
        timeout_seconds=60.0,
    )
    adapter.client = httpx.Client(
        base_url="http://runpod.test",
        transport=httpx.MockTransport(handler),
    )
    adapter.generate(
        make_blueprint().model_copy(update={"vocal_mode": "vocals"}),
        duration_seconds=1,
    )

    assert [request.url.path for request in requests] == [
        "/format_input",
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
