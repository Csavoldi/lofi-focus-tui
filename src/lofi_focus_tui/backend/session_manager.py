from concurrent.futures import CancelledError, Future, ThreadPoolExecutor
from threading import Lock
from uuid import uuid4

from lofi_focus_tui.audio.playback import PlaybackManager
from lofi_focus_tui.backend.tasks import GenerationTask
from lofi_focus_tui.composition import create_blueprint
from lofi_focus_tui.devices import choose_device
from lofi_focus_tui.domain import BackendState, BackendStatus, SessionRequest
from lofi_focus_tui.generation.base import ModelAdapter
from lofi_focus_tui.generation.settings import GenerationSettings
from lofi_focus_tui.presets import expand_preset
from lofi_focus_tui.prompt_safety import map_style_tags


class SessionManager:
    def __init__(
        self,
        model: ModelAdapter,
        generation_defaults: GenerationSettings | None = None,
        render_seconds_limit: int | None = None,
    ) -> None:
        self.model = model
        self.generation_defaults = generation_defaults
        self.render_seconds_limit = render_seconds_limit
        self.playback = PlaybackManager()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="lofi-generation")
        self._lock = Lock()
        self._tasks: dict[str, GenerationTask] = {}
        self._active_future: Future[None] | None = None
        self._status = BackendStatus(state=BackendState.IDLE, message="ready", backend=model.name)

    def health(self) -> BackendStatus:
        with self._lock:
            return self._status.model_copy()

    def start_session(self, request: SessionRequest) -> BackendStatus:
        device = choose_device(request.device_preference)
        safe_request = request.model_copy(update={"style_tags": map_style_tags(request.style_tags)})
        plan = expand_preset(safe_request)
        blueprint = create_blueprint(plan)
        duration_limit = self.render_seconds_limit or device.recommended_render_seconds or 30
        if device.recommended_render_seconds:
            duration_limit = min(duration_limit, device.recommended_render_seconds)
        duration_seconds = min(duration_limit, request.duration_minutes * 60)
        settings = request.generation or self.generation_defaults
        task = GenerationTask(task_id=str(uuid4()), session_id=plan.session_id)
        status = BackendStatus(
            state=BackendState.GENERATING,
            message="generating",
            active_session_id=plan.session_id,
            progress=0.0,
            active_task_id=task.task_id,
            backend=self.model.name,
            device=device.backend,
        )
        with self._lock:
            self._tasks[task.task_id] = task
            self._status = status
            self._active_future = self._executor.submit(
                self._run_generation_task,
                task,
                blueprint,
                duration_seconds,
                settings,
                device.backend,
            )
        return status

    def wait_for_active_task(self, timeout: float = 5.0) -> BackendStatus:
        with self._lock:
            future = self._active_future
        if future is not None:
            try:
                future.result(timeout=timeout)
            except CancelledError:
                pass
        return self.health()

    def pause_session(self) -> BackendStatus:
        with self._lock:
            self.playback.pause()
            self._status = self._status.model_copy(
                update={"state": BackendState.PAUSED, "message": "paused"}
            )
            return self._status

    def resume_session(self) -> BackendStatus:
        with self._lock:
            self.playback.resume()
            self._status = self._status.model_copy(
                update={"state": BackendState.PLAYING, "message": "playing"}
            )
            return self._status

    def stop_session(self) -> BackendStatus:
        with self._lock:
            if self._active_future is not None:
                self._active_future.cancel()
            self.playback.stop()
            self._status = BackendStatus(
                state=BackendState.IDLE,
                message="stopped",
                backend=self.model.name,
            )
            return self._status

    def _run_generation_task(
        self,
        task: GenerationTask,
        blueprint,
        duration_seconds: int,
        settings: GenerationSettings | None,
        device_backend: str,
    ) -> None:
        if not self._is_active_task(task):
            return
        try:
            self._update_task_status(
                task,
                state=BackendState.GENERATING,
                message="generating",
                progress=0.5,
                device_backend=device_backend,
            )
            result = self.model.generate(
                blueprint,
                duration_seconds=duration_seconds,
                settings=settings,
            )
            self._complete_task_success(task, result, device_backend)
        except Exception as exc:
            task.error = str(exc)
            self._update_task_status(
                task,
                state=BackendState.ERROR,
                message="generation failed",
                progress=task.progress,
                device_backend=device_backend,
                error=task.error,
            )

    def _update_task_status(
        self,
        task: GenerationTask,
        state: BackendState,
        message: str,
        progress: float,
        device_backend: str,
        output_path: str | None = None,
        error: str | None = None,
    ) -> None:
        task.update(state, message, progress)
        if output_path is not None:
            task.output_path = output_path
        if error is not None:
            task.error = error
        with self._lock:
            if self._status.active_task_id != task.task_id:
                return
            self._status = BackendStatus(
                state=task.state,
                message=task.message,
                active_session_id=task.session_id,
                progress=task.progress,
                active_task_id=task.task_id,
                output_path=task.output_path,
                error=task.error,
                backend=self.model.name,
                device=device_backend,
            )

    def _complete_task_success(self, task: GenerationTask, result, device_backend: str) -> None:
        output_path = self._output_path(result.metadata)
        with self._lock:
            if self._status.active_task_id != task.task_id:
                return
            self.playback.load(result)
            task.output_path = output_path
            task.update(BackendState.PLAYING, "playing", 1.0)
            self._status = BackendStatus(
                state=task.state,
                message=task.message,
                active_session_id=task.session_id,
                progress=task.progress,
                active_task_id=task.task_id,
                output_path=task.output_path,
                error=task.error,
                backend=self.model.name,
                device=device_backend,
            )

    def _is_active_task(self, task: GenerationTask) -> bool:
        with self._lock:
            return self._status.active_task_id == task.task_id

    @staticmethod
    def _output_path(metadata: dict[str, str]) -> str | None:
        return metadata.get("output_path") or metadata.get("path")
