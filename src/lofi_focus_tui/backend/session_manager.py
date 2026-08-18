from concurrent.futures import CancelledError, Future, ThreadPoolExecutor, TimeoutError
from datetime import UTC, datetime
from inspect import signature
from math import ceil
from pathlib import Path
from threading import Lock
from uuid import uuid4

from lofi_focus_tui.audio.continuity import (
    analyze_boundary,
    analyze_chunk,
    continuation_notes,
)
from lofi_focus_tui.audio.normalization import crossfade
from lofi_focus_tui.audio.output import OutputManager
from lofi_focus_tui.audio.playback import PlaybackManager
from lofi_focus_tui.backend.tasks import GenerationTask
from lofi_focus_tui.composition import create_blueprint, create_chunk_blueprint
from lofi_focus_tui.devices import choose_device
from lofi_focus_tui.domain import (
    BackendState,
    BackendStatus,
    ExportResponse,
    SessionRequest,
)
from lofi_focus_tui.generation.base import GenerationCancelledError, GenerationResult, ModelAdapter
from lofi_focus_tui.generation.settings import GenerationSettings
from lofi_focus_tui.history import HistoryStore, SessionRecord
from lofi_focus_tui.presets import expand_preset
from lofi_focus_tui.prompt_safety import map_style_tags


class SessionManager:
    _SHUTDOWN_TIMEOUT_SECONDS = 2.0

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
        self._resource_lock = Lock()
        self._tasks: dict[str, GenerationTask] = {}
        self._futures: set[Future[None]] = set()
        self._active_future: Future[None] | None = None
        self._running_tasks = 0
        self._closed = False
        self._resources_closed = False
        self._status = BackendStatus(
            state=BackendState.IDLE,
            message="ready",
            backend=model.name,
            playback=self._playback_mode(),
            recent_sessions=self._recent_session_labels(),
        )

    def health(self) -> BackendStatus:
        with self._lock:
            status = self._status.model_copy()
        return status.model_copy(update=self._playback_status_fields())

    def start_session(self, request: SessionRequest) -> BackendStatus:
        self._ensure_open()
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
            playback=self._playback_mode(),
            recent_sessions=self._recent_session_labels(),
            chunk_index=0,
            chunk_count=len(chunk_durations),
        )
        with self._playback_lock:
            with self._lock:
                self._ensure_open_locked()
                self.playback.stop()
                self._cancel_active_task_locked()
                self._tasks[task.task_id] = task
                self._status = status
                future = self._executor.submit(
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
                self._futures.add(future)
                self._active_future = future
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
            with self._lock:
                self._ensure_open_locked()
                paused = self.playback.pause()
                if paused:
                    self._status = self._status.model_copy(
                        update={"state": BackendState.PAUSED, "message": "paused"}
                    )
                return self._status.model_copy(update=self._playback_status_fields())

    def resume_session(self) -> BackendStatus:
        with self._playback_lock:
            with self._lock:
                self._ensure_open_locked()
                resumed = self.playback.resume()
                if resumed:
                    self._status = self._status.model_copy(
                        update={"state": BackendState.PLAYING, "message": "playing"}
                    )
                return self._status.model_copy(update=self._playback_status_fields())

    def adjust_volume(self, delta: float) -> BackendStatus:
        with self._playback_lock:
            with self._lock:
                self._ensure_open_locked()
                self.playback.adjust_volume(delta)
                return self._status.model_copy(update=self._playback_status_fields())

    def seek_playback(self, seconds: float) -> BackendStatus:
        with self._playback_lock:
            with self._lock:
                self._ensure_open_locked()
                self.playback.seek(seconds)
                return self._status.model_copy(update=self._playback_status_fields())

    def restart_playback(self) -> BackendStatus:
        with self._playback_lock:
            with self._lock:
                self._ensure_open_locked()
                self.playback.restart()
                return self._status.model_copy(update=self._playback_status_fields())

    def export_current(self, directory: str) -> ExportResponse:
        with self._playback_lock:
            with self._lock:
                self._ensure_open_locked()
                output_manager = self.output_manager
                if output_manager is None:
                    raise RuntimeError("no completed audio session to export")
                output_path = self._status.output_path
                if output_path is None:
                    raise RuntimeError("no completed audio session to export")
        audio_path, metadata_path = output_manager.export_session(
            Path(output_path), Path(directory)
        )
        return ExportResponse(
            message="session exported",
            audio_path=str(audio_path),
            metadata_path=str(metadata_path),
        )

    def stop_session(self) -> BackendStatus:
        with self._playback_lock:
            with self._lock:
                self._ensure_open_locked()
                self._cancel_active_task_locked()
                if self._active_future is not None:
                    self._active_future.cancel()
                self.playback.stop()
                self._status = BackendStatus(
                    state=BackendState.IDLE,
                    message="stopped",
                    backend=self.model.name,
                    playback=self._playback_mode(),
                    recent_sessions=self._recent_session_labels(),
                )
                return self._status.model_copy(update=self._playback_status_fields())

    def shutdown(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            active_future = self._active_future
            if self._status.active_task_id is not None:
                active_task = self._tasks.get(self._status.active_task_id)
                if active_task is not None:
                    active_task.cancel_event.set()
            self._status = BackendStatus(
                state=BackendState.IDLE,
                message="closed",
                backend=self.model.name,
                playback=self._playback_mode(),
                recent_sessions=self._recent_session_labels(),
            )

        with self._playback_lock:
            self.playback.stop()

        if active_future is not None:
            try:
                active_future.result(timeout=self._SHUTDOWN_TIMEOUT_SECONDS)
            except (CancelledError, TimeoutError):
                pass

        with self._lock:
            futures = tuple(self._futures)
        for future in futures:
            if not future.running() and not future.done():
                future.cancel()
        with self._lock:
            should_finalize = all(future.done() for future in self._futures)
        if should_finalize:
            self._finalize_resources()

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
        with self._lock:
            self._running_tasks += 1
        try:
            if self._is_active_task(task):
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
            if isinstance(exc, GenerationCancelledError):
                self._update_task_status(
                    task,
                    state=BackendState.IDLE,
                    message="stopped",
                    progress=task.progress,
                    device_backend=device_backend,
                    chunk_count=len(chunk_durations),
                )
            else:
                self._update_task_status(
                    task,
                    state=BackendState.ERROR,
                    message="generation failed",
                    progress=task.progress,
                    device_backend=device_backend,
                    error=str(exc),
                    chunk_count=len(chunk_durations),
                )
        finally:
            with self._lock:
                self._running_tasks -= 1
                should_finalize = self._closed and self._running_tasks == 0
            if should_finalize:
                self._finalize_resources()

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
        with self._lock:
            if not self._is_active_task_locked(task):
                return
            task.update(state, message, progress)
            if output_path is not None:
                task.output_path = output_path
            if error is not None:
                task.error = error
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
                playback=self._playback_mode(),
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
        chunk_results = []
        chunk_metadata = []
        chunk_count = len(chunk_durations)
        handoff: list[str] = []
        for chunk_index, chunk_duration in enumerate(chunk_durations):
            self._raise_if_cancelled(task)
            chunk_blueprint = (
                blueprint
                if chunk_count == 1
                else create_chunk_blueprint(
                    plan,
                    chunk_index,
                    chunk_count,
                    continuation_constraints=handoff,
                    base_blueprint=blueprint,
                )
            )
            result = self._generate_chunk(
                task,
                chunk_blueprint,
                duration_seconds=chunk_duration,
                settings=settings,
            )
            self._raise_if_cancelled(task)
            retry_count = 0
            boundary_report = None
            if chunk_results:
                boundary_report = analyze_boundary(
                    chunk_results[-1].audio,
                    result.audio,
                    sample_rate=result.sample_rate,
                )
                if boundary_report.severe:
                    result = self._retry_chunk_if_needed(
                        task=task,
                        previous=chunk_results[-1],
                        result=result,
                        report=boundary_report,
                        chunk_blueprint=chunk_blueprint,
                        chunk_index=chunk_index,
                        chunk_duration=chunk_duration,
                        settings=settings,
                    )
                    retry_count = 1
                    boundary_report = analyze_boundary(
                        chunk_results[-1].audio,
                        result.audio,
                        sample_rate=result.sample_rate,
                    )
                handoff = continuation_notes(boundary_report)
            else:
                handoff = []
            chunk_results.append(result)
            chunk_metadata.append(
                {
                    "index": chunk_index,
                    "duration_seconds": chunk_duration,
                    "profile": analyze_chunk(result.audio, result.sample_rate).to_dict(),
                    "boundary": (
                        boundary_report.to_dict() if boundary_report is not None else None
                    ),
                    "handoff": list(handoff),
                    "retry_count": retry_count,
                }
            )
            self._update_task_status(
                task,
                state=BackendState.GENERATING,
                message=f"generated chunk {chunk_index + 1}/{chunk_count}",
                progress=0.5 + ((chunk_index + 1) / chunk_count * 0.45),
                device_backend=device_backend,
                chunk_index=chunk_index + 1,
                chunk_count=chunk_count,
            )
        return self._stitch_chunk_results(plan.session_id, chunk_results, chunk_metadata)

    def _generate_chunk(
        self,
        task: GenerationTask,
        blueprint,
        duration_seconds: int,
        settings: GenerationSettings | None,
    ) -> GenerationResult:
        generate = self.model.generate
        parameters = signature(generate).parameters
        if "cancel_event" in parameters:
            return generate(
                blueprint,
                duration_seconds=duration_seconds,
                settings=settings,
                cancel_event=task.cancel_event,
            )
        return generate(blueprint, duration_seconds=duration_seconds, settings=settings)

    @staticmethod
    def _raise_if_cancelled(task: GenerationTask) -> None:
        if task.cancel_event.is_set():
            raise GenerationCancelledError("generation cancelled")

    def _retry_chunk_if_needed(
        self,
        task: GenerationTask,
        previous: GenerationResult,
        result: GenerationResult,
        report,
        chunk_blueprint,
        chunk_index: int,
        chunk_duration: int,
        settings: GenerationSettings | None,
    ) -> GenerationResult:
        if not report.severe:
            return result

        retry_seed = chunk_blueprint.seed + chunk_index + 1
        retry_blueprint = chunk_blueprint.model_copy(
            update={
                "seed": retry_seed,
                "continuation_constraints": continuation_notes(report),
            }
        )
        retry_settings = settings
        if settings is not None and settings.seed >= 0:
            retry_settings = settings.model_copy(update={"seed": retry_seed})
        retry_result = self._generate_chunk(
            task,
            retry_blueprint,
            duration_seconds=chunk_duration,
            settings=retry_settings,
        )
        retry_report = analyze_boundary(
            previous.audio,
            retry_result.audio,
            sample_rate=retry_result.sample_rate,
        )
        if not retry_report.accepted:
            warnings = ", ".join(retry_report.warnings)
            raise RuntimeError(f"chunk continuity failed: {warnings}")
        return retry_result

    def _stitch_chunk_results(
        self,
        session_id: str,
        chunk_results: list[GenerationResult],
        chunk_metadata: list[dict],
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
                "requested_duration_seconds": str(
                    sum(result.duration_seconds for result in chunk_results)
                ),
                "actual_duration_seconds": f"{len(audio) / sample_rate:.6f}",
                "chunks": chunk_metadata,
            }
        )
        return GenerationResult(
            audio=audio,
            sample_rate=sample_rate,
            duration_seconds=len(audio) / sample_rate,
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
        with self._playback_lock:
            with self._lock:
                if not self._is_active_task_locked(task):
                    return
                output_path = self._output_path(result.metadata)
                record = None
                if self.output_manager is not None:
                    output_path, _metadata_path, record = self._prepare_output_record(
                        request=request,
                        plan=plan,
                        blueprint=blueprint,
                        result=result,
                        duration_seconds=duration_seconds,
                        settings=settings,
                        device_backend=device_backend,
                    )
                if not self._is_active_task_locked(task):
                    return
                self.playback.load(result)
                if not self._is_active_task_locked(task):
                    self.playback.stop()
                    return
                if record is not None and self.history_store is not None:
                    self.history_store.append(record)
                if not self._is_active_task_locked(task):
                    self.playback.stop()
                    return
                task.output_path = output_path
                playback_mode = self._playback_mode()
                if playback_mode == "disabled":
                    message = "generated; playback disabled"
                elif getattr(self.playback, "last_error", None):
                    message = "generated; playback fallback"
                else:
                    message = "playing"
                if not self._is_active_task_locked(task):
                    self.playback.stop()
                    return
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
                    playback=playback_mode,
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
            "actual_duration_seconds": result.duration_seconds,
            "generation": result.metadata,
        }
        metadata_path = self.output_manager.save_metadata(metadata, directory)
        record = SessionRecord(
            session_id=plan.session_id,
            preset=plan.preset,
            focus=plan.focus,
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
            return self._is_active_task_locked(task)

    def _is_active_task_locked(self, task: GenerationTask) -> bool:
        return not self._closed and self._status.active_task_id == task.task_id

    def _ensure_open(self) -> None:
        with self._lock:
            self._ensure_open_locked()

    def _ensure_open_locked(self) -> None:
        if self._closed:
            raise RuntimeError("session manager is closed")

    def _finalize_resources(self) -> None:
        with self._resource_lock:
            if self._resources_closed:
                return
            self._resources_closed = True
            try:
                close = getattr(self.model, "close", None)
                if callable(close):
                    close()
            finally:
                self._executor.shutdown(wait=False, cancel_futures=True)

    def _recent_session_labels(self) -> list[str]:
        if self.history_store is None:
            return []
        labels = []
        for record in self.history_store.list(limit=5):
            favorite = " *" if record.favorite else ""
            labels.append(f"{record.session_id[:8]} {record.preset}{favorite}")
        return labels

    def _cancel_active_task_locked(self) -> None:
        if self._active_future is not None:
            self._active_future.cancel()
        if self._status.active_task_id is None:
            return
        active_task = self._tasks.get(self._status.active_task_id)
        if active_task is not None:
            active_task.cancel_event.set()

    def _playback_mode(self) -> str:
        return str(getattr(self.playback, "mode", "custom"))

    def _playback_status_fields(self) -> dict[str, float]:
        return {
            "volume": float(getattr(self.playback, "volume", 0.8)),
            "position_seconds": float(getattr(self.playback, "position_seconds", 0.0)),
            "duration_seconds": float(getattr(self.playback, "duration_seconds", 0.0)),
        }

    @staticmethod
    def _output_path(metadata: dict[str, str]) -> str | None:
        return metadata.get("output_path") or metadata.get("path")
