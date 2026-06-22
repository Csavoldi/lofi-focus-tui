import json
import time
from threading import Event
from typing import Any, Callable

import httpx
import numpy as np
from pydantic import BaseModel

from lofi_focus_tui.audio.wav import read_wav_bytes
from lofi_focus_tui.domain import CompositionBlueprint
from lofi_focus_tui.generation.ace_step import _blueprint_to_prompt
from lofi_focus_tui.generation.base import GenerationCancelledError, GenerationResult
from lofi_focus_tui.generation.settings import GenerationSettings

SUCCEEDED_STATUSES = {"succeeded", "success", "completed", "done"}
FAILED_STATUSES = {"failed", "error", "cancelled", "canceled"}


class TaskSubmission(BaseModel):
    task_id: str

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "TaskSubmission":
        data = _unwrap_data(payload)
        task_id = data.get("task_id") or data.get("taskId") or data.get("id")
        if not task_id:
            raise RuntimeError("ACE-Step HTTP response did not include a task id")
        return cls(task_id=str(task_id))


class AudioResult(BaseModel):
    path: str

    @classmethod
    def from_payload(cls, payload: Any) -> "AudioResult":
        data = _decode_jsonish(payload)
        if isinstance(data, str):
            return cls(path=data)
        if not isinstance(data, dict):
            raise RuntimeError("ACE-Step HTTP audio result must be an object or path")
        path = (
            data.get("path")
            or data.get("audio_path")
            or data.get("output_path")
            or data.get("url")
        )
        if not path:
            raise RuntimeError("ACE-Step HTTP result did not include an audio path")
        return cls(path=str(path))


class TaskResult(BaseModel):
    task_id: str | None = None
    status: str
    audio: AudioResult | None = None
    error: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "TaskResult":
        data = _unwrap_data(payload)
        status = str(data.get("status") or data.get("state") or "").lower()
        if not status:
            raise RuntimeError("ACE-Step HTTP result did not include a status")
        result = data.get("result") or data.get("audio") or data.get("output")
        audio = None
        if result is not None and status in SUCCEEDED_STATUSES:
            audio = AudioResult.from_payload(result)
        return cls(
            task_id=data.get("task_id") or data.get("taskId") or data.get("id"),
            status=status,
            audio=audio,
            error=data.get("error") or data.get("message"),
        )


class AceStepHttpAdapter:
    name = "ace-step-http"

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8001",
        api_key: str = "",
        timeout_seconds: float = 1800.0,
        poll_interval_seconds: float = 1.0,
        transport: httpx.BaseTransport | None = None,
        client: httpx.Client | None = None,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.clock = clock or time.monotonic
        self.sleep = sleep or time.sleep
        self.client = client or httpx.Client(
            base_url=self.base_url,
            timeout=timeout_seconds,
            transport=transport,
        )

    def health(self) -> bool:
        try:
            response = self.client.get("/health", headers=self._headers())
            return response.is_success
        except httpx.HTTPError:
            return False

    def submit_task(
        self,
        blueprint: CompositionBlueprint,
        duration_seconds: int,
        settings: GenerationSettings | None = None,
    ) -> TaskSubmission:
        settings = settings or GenerationSettings(seed=blueprint.seed)
        seed = settings.seed if settings.seed >= 0 else blueprint.seed
        payload = {
            "audio_duration": duration_seconds,
            "prompt": _blueprint_to_prompt(blueprint),
            "lyrics": "",
            "infer_step": settings.inference_steps,
            "guidance_scale": settings.guidance_scale,
            "scheduler_type": settings.scheduler_type,
            "cfg_type": settings.cfg_type,
            "omega_scale": settings.omega_scale,
            "manual_seeds": str(seed),
            "output_format": settings.output_format,
            "batch_size": settings.batch_size,
        }
        response = self.client.post("/release_task", json=payload, headers=self._headers())
        response.raise_for_status()
        return TaskSubmission.from_payload(response.json())

    def query_result(self, task_id: str) -> TaskResult:
        response = self.client.post(
            "/query_result",
            json={"task_id": task_id},
            headers=self._headers(),
        )
        response.raise_for_status()
        return TaskResult.from_payload(response.json())

    def download_audio(self, path: str) -> tuple[np.ndarray, int]:
        response = self.client.get(
            "/v1/audio",
            params={"path": path},
            headers=self._headers(),
        )
        response.raise_for_status()
        return read_wav_bytes(response.content)

    def generate(
        self,
        blueprint: CompositionBlueprint,
        duration_seconds: int,
        settings: GenerationSettings | None = None,
        cancel_event: Event | None = None,
    ) -> GenerationResult:
        submission = self.submit_task(blueprint, duration_seconds, settings)
        started_at = self.clock()
        while True:
            self._raise_if_cancelled(cancel_event)
            if self.clock() - started_at > self.timeout_seconds:
                raise TimeoutError(f"ACE-Step HTTP task timed out after {self.timeout_seconds:g}s")
            result = self.query_result(submission.task_id)
            if result.status in SUCCEEDED_STATUSES:
                if result.audio is None:
                    raise RuntimeError("ACE-Step HTTP task succeeded without audio")
                audio, sample_rate = self.download_audio(result.audio.path)
                return GenerationResult(
                    audio=audio,
                    sample_rate=sample_rate,
                    duration_seconds=duration_seconds,
                    metadata={
                        "session_id": blueprint.session_id,
                        "backend": self.name,
                        "task_id": submission.task_id,
                        "path": result.audio.path,
                    },
                )
            if result.status in FAILED_STATUSES:
                raise RuntimeError(result.error or f"ACE-Step HTTP task {result.status}")
            if self.poll_interval_seconds > 0:
                self.sleep(self.poll_interval_seconds)

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        return {"Authorization": f"Bearer {self.api_key}"}

    @staticmethod
    def _raise_if_cancelled(cancel_event: Event | None) -> None:
        if cancel_event is not None and cancel_event.is_set():
            raise GenerationCancelledError("generation cancelled")


def _unwrap_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data", payload)
    if not isinstance(data, dict):
        raise RuntimeError("ACE-Step HTTP response data must be an object")
    return data


def _decode_jsonish(payload: Any) -> Any:
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return payload
    return payload
