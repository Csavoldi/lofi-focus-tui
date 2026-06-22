from concurrent.futures import CancelledError, Future, ThreadPoolExecutor
from datetime import UTC, datetime
from math import ceil
from threading import Lock
from uuid import uuid4

from lofi_focus_tui.audio.continuity import analyze_boundary
from lofi_focus_tui.audio.normalization import crossfade
from lofi_focus_tui.audio.output import OutputManager
from lofi_focus_tui.audio.playback import PlaybackManager
from lofi_focus_tui.backend.tasks import GenerationTask
from lofi_focus_tui.composition import create_blueprint, create_chunk_blueprint
from lofi_focus_tui.devices import choose_device
from lofi_focus_tui.domain import BackendState, BackendStatus, SessionRequest
from lofi_focus_tui.generation.base import GenerationResult, ModelAdapter
from lofi_focus_tui.generation.settings import GenerationSettings
from lofi_focus_tui.history import HistoryStore, SessionRecord
from lofi_focus_tui.presets import expand_preset
from lofi_focus_tui.prompt_safety import map_style_tags


class SessionManager:
    def __init__(
        self,
        model: ModelAdapter,
        generation_defaults: GenerationSettings | None = None,
        render_seconds_limit: int | None = None,
        chunk_seconds: int | None = None,
        crossfade_seconds: float = 1.0,
        playback: PlaybackManager | None = None,
        output_manager: OutputManager | None = None,
        history_store: HistoryStore | None = None,
    ) -> None:
        self.model = model
        self.generation_defaults = generation_defaults
        self.render_seconds_limit = render_seconds_limit
        self.chunk_seconds = chunk_seconds
        self.crossfade_seconds = crossfade_seconds
        self.playback = playback or PlaybackManager()
        self.output_manager = output_manager
        self.history_store = history_store
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="lofi-generation")
        self._lock = Lock()
        self._playback_lock = Lock()
        self._tasks: dict[str, GenerationTask] = {}
        self._active_future: Future[None] | None = None
        self._status = BackendStatus(
            state=BackendState.IDLE,
            message="ready",
            backend=model.name,
            recent_sessions=self._recent_session_labels(),
        )

    def health(self) -> BackendStatus:
        with self._lock:
            return self._status.model_copy()

    def start_session(self, request: SessionRequest) -> BackendStatus:
        device = choose_device(request.device_preference)
        safe_request = request.model_copy(update={"style_tags": map_style_tags(request.style_tags)})
        plan = expand_preset(safe_request)
        blueprint = create_blueprint(plan)
        duration_seconds, chunk_durations = self._resolve_timing(request, device)
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
            recent_sessions=self._recent_session_labels(),
            chunk_index=0,
            chunk_count=len(chunk_durations),
        )
        with self._playback_lock:
            self.playback.stop()
        with self._lock:
            self._tasks[task.task_id] = task
            self._status = status
            self._active_future = self._executor.submit(
                self._run_generation_task,
                task,
                safe_request,
                plan,
                blueprint,
                duration_seconds,
                chunk_durations,
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
        with self._playback_lock:
            paused = self.playback.pause()
        with self._lock:
            if paused:
                self._status = self._status.model_copy(
                    update={"state": BackendState.PAUSED, "message": "paused"}
                )
            return self._status.model_copy()

    def resume_session(self) -> BackendStatus:
        with self._playback_lock:
            resumed = self.playback.resume()
        with self._lock:
            if resumed:
                self._status = self._status.model_copy(
                    update={"state": BackendState.PLAYING, "message": "playing"}
                )
            return self._status.model_copy()

    def stop_session(self) -> BackendStatus:
        with self._lock:
            if self._active_future is not None:
                self._active_future.cancel()
            self._status = BackendStatus(
                state=BackendState.IDLE,
                message="stopped",
                backend=self.model.name,
                recent_sessions=self._recent_session_labels(),
            )
            status = self._status.model_copy()
        with self._playback_lock:
            self.playback.stop()
        return status

    def _run_generation_task(
        self,
        task: GenerationTask,
        request: SessionRequest,
        plan,
        blueprint,
        duration_seconds: int,
        chunk_durations: list[int],
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
                chunk_index=0,
                chunk_count=len(chunk_durations),
            )
            result = self._generate_session_result(
                task=task,
                plan=plan,
                blueprint=blueprint,
                chunk_durations=chunk_durations,
                settings=settings,
                device_backend=device_backend,
            )
            self._complete_task_success(
                task,
                request,
                plan,
                blueprint,
                result,
                duration_seconds,
                len(chunk_durations),
                settings,
                device_backend,
            )
        except Exception as exc:
            task.error = str(exc)
            self._update_task_status(
                task,
                state=BackendState.ERROR,
                message="generation failed",
                progress=task.progress,
                device_backend=device_backend,
                error=task.error,
                chunk_count=len(chunk_durations),
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
        chunk_index: int = 0,
        chunk_count: int = 0,
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
                recent_sessions=self._recent_session_labels(),
                chunk_index=chunk_index,
                chunk_count=chunk_count,
                backend=self.model.name,
                device=device_backend,
            )

    def _resolve_timing(self, request: SessionRequest, device) -> tuple[int, list[int]]:
        requested_seconds = request.duration_minutes * 60
        if self.chunk_seconds is None:
            duration_limit = self.render_seconds_limit or device.recommended_render_seconds or 30
            if device.recommended_render_seconds:
                duration_limit = min(duration_limit, device.recommended_render_seconds)
            duration_seconds = min(duration_limit, requested_seconds)
            return duration_seconds, [duration_seconds]

        duration_seconds = requested_seconds
        if self.render_seconds_limit is not None:
            duration_seconds = min(duration_seconds, self.render_seconds_limit)
        chunk_seconds = self.chunk_seconds
        chunk_seconds = max(1, chunk_seconds)
        chunk_count = max(1, ceil(duration_seconds / chunk_seconds))
        chunk_durations = [
            min(chunk_seconds, duration_seconds - (chunk_index * chunk_seconds))
            for chunk_index in range(chunk_count)
        ]
        return duration_seconds, chunk_durations

    def _generate_session_result(
        self,
        task: GenerationTask,
        plan,
        blueprint,
        chunk_durations: list[int],
        settings: GenerationSettings | None,
        device_backend: str,
    ) -> GenerationResult:
        if len(chunk_durations) == 1:
            return self.model.generate(
                blueprint,
                duration_seconds=chunk_durations[0],
                settings=settings,
            )

        chunk_results = []
        chunk_count = len(chunk_durations)
        for chunk_index, chunk_duration in enumerate(chunk_durations):
            chunk_blueprint = create_chunk_blueprint(plan, chunk_index, chunk_count)
            result = self.model.generate(
                chunk_blueprint,
                duration_seconds=chunk_duration,
                settings=settings,
            )
            if chunk_results:
                result = self._retry_chunk_if_needed(
                    previous=chunk_results[-1],
                    result=result,
                    chunk_blueprint=chunk_blueprint,
                    chunk_index=chunk_index,
                    chunk_duration=chunk_duration,
                    settings=settings,
                )
            chunk_results.append(result)
            self._update_task_status(
                task,
                state=BackendState.GENERATING,
                message=f"generated chunk {chunk_index + 1}/{chunk_count}",
                progress=0.5 + ((chunk_index + 1) / chunk_count * 0.45),
                device_backend=device_backend,
                chunk_index=chunk_index + 1,
                chunk_count=chunk_count,
            )
        return self._stitch_chunk_results(plan.session_id, chunk_results)

    def _retry_chunk_if_needed(
        self,
        previous: GenerationResult,
        result: GenerationResult,
        chunk_blueprint,
        chunk_index: int,
        chunk_duration: int,
        settings: GenerationSettings | None,
    ) -> GenerationResult:
        report = analyze_boundary(previous.audio, result.audio)
        if report.accepted:
            return result

        retry_seed = chunk_blueprint.seed + chunk_index + 1
        retry_blueprint = chunk_blueprint.model_copy(update={"seed": retry_seed})
        retry_settings = settings
        if settings is not None and settings.seed >= 0:
            retry_settings = settings.model_copy(update={"seed": retry_seed})
        retry_result = self.model.generate(
            retry_blueprint,
            duration_seconds=chunk_duration,
            settings=retry_settings,
        )
        retry_report = analyze_boundary(previous.audio, retry_result.audio)
        if not retry_report.accepted:
            warnings = ", ".join(retry_report.warnings)
            raise RuntimeError(f"chunk continuity failed: {warnings}")
        return retry_result

    def _stitch_chunk_results(
        self,
        session_id: str,
        chunk_results: list[GenerationResult],
    ) -> GenerationResult:
        first = chunk_results[0]
        audio = first.audio
        sample_rate = first.sample_rate
        for result in chunk_results[1:]:
            if result.sample_rate != sample_rate:
                raise RuntimeError("chunk sample rates differ")
            audio = crossfade(audio, result.audio, sample_rate, self.crossfade_seconds)
        metadata = dict(chunk_results[-1].metadata)
        metadata.update(
            {
                "session_id": session_id,
                "chunk_count": str(len(chunk_results)),
            }
        )
        return GenerationResult(
            audio=audio,
            sample_rate=sample_rate,
            duration_seconds=sum(result.duration_seconds for result in chunk_results),
            metadata=metadata,
        )

    def _complete_task_success(
        self,
        task: GenerationTask,
        request: SessionRequest,
        plan,
        blueprint,
        result,
        duration_seconds: int,
        chunk_count: int,
        settings: GenerationSettings | None,
        device_backend: str,
    ) -> None:
        output_path = self._output_path(result.metadata)
        record = None
        if self.output_manager is not None and self._is_active_task(task):
            output_path, _metadata_path, record = self._prepare_output_record(
                request=request,
                plan=plan,
                blueprint=blueprint,
                result=result,
                duration_seconds=duration_seconds,
                settings=settings,
                device_backend=device_backend,
            )
        with self._playback_lock:
            with self._lock:
                if self._status.active_task_id != task.task_id:
                    return
            self.playback.load(result)
            with self._lock:
                if self._status.active_task_id != task.task_id:
                    self.playback.stop()
                    return
                if record is not None and self.history_store is not None:
                    self.history_store.append(record)
                task.output_path = output_path
                message = "playing"
                if getattr(self.playback, "last_error", None):
                    message = "playing with fallback playback"
                task.update(BackendState.PLAYING, message, 1.0)
                self._status = BackendStatus(
                    state=task.state,
                    message=task.message,
                    active_session_id=task.session_id,
                    progress=task.progress,
                    active_task_id=task.task_id,
                    output_path=task.output_path,
                    error=task.error,
                    recent_sessions=self._recent_session_labels(),
                    chunk_index=chunk_count,
                    chunk_count=chunk_count,
                    backend=self.model.name,
                    device=device_backend,
                )

    def _prepare_output_record(
        self,
        request: SessionRequest,
        plan,
        blueprint,
        result,
        duration_seconds: int,
        settings: GenerationSettings | None,
        device_backend: str,
    ) -> tuple[str, str, SessionRecord]:
        directory = self.output_manager.create_session_dir(plan.session_id, plan.preset)
        audio_path = self.output_manager.save_wav(result, directory)
        metadata = {
            "seed": plan.seed,
            "request": request.model_dump(mode="json"),
            "plan": plan.model_dump(mode="json"),
            "blueprint": blueprint.model_dump(mode="json"),
            "settings": settings.model_dump(mode="json") if settings is not None else None,
            "device": device_backend,
            "duration_seconds": duration_seconds,
            "generation": result.metadata,
        }
        metadata_path = self.output_manager.save_metadata(metadata, directory)
        record = SessionRecord(
            session_id=plan.session_id,
            preset=plan.preset,
            created_at=datetime.now(UTC).isoformat(),
            duration_seconds=duration_seconds,
            audio_path=str(audio_path),
            metadata_path=str(metadata_path),
            seed=plan.seed,
            tags=list(request.style_tags),
        )
        return str(audio_path), str(metadata_path), record

    def _is_active_task(self, task: GenerationTask) -> bool:
        with self._lock:
            return self._status.active_task_id == task.task_id

    def _recent_session_labels(self) -> list[str]:
        if self.history_store is None:
            return []
        labels = []
        for record in self.history_store.list(limit=5):
            favorite = " *" if record.favorite else ""
            labels.append(f"{record.session_id[:8]} {record.preset}{favorite}")
        return labels

    @staticmethod
    def _output_path(metadata: dict[str, str]) -> str | None:
        return metadata.get("output_path") or metadata.get("path")
