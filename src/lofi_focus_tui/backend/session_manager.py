from lofi_focus_tui.audio.playback import PlaybackManager
from lofi_focus_tui.composition import create_blueprint
from lofi_focus_tui.devices import choose_device
from lofi_focus_tui.domain import BackendStatus, SessionRequest
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
        self._status = BackendStatus(state="idle", message="ready", backend=model.name)

    def health(self) -> BackendStatus:
        return self._status

    def start_session(self, request: SessionRequest) -> BackendStatus:
        device = choose_device(request.device_preference)
        safe_request = request.model_copy(update={"style_tags": map_style_tags(request.style_tags)})
        plan = expand_preset(safe_request)
        blueprint = create_blueprint(plan)
        duration_limit = self.render_seconds_limit or device.recommended_render_seconds or 30
        if device.recommended_render_seconds:
            duration_limit = min(duration_limit, device.recommended_render_seconds)
        duration_seconds = min(duration_limit, request.duration_minutes * 60)
        result = self.model.generate(
            blueprint,
            duration_seconds=duration_seconds,
            settings=request.generation or self.generation_defaults,
        )
        self.playback.load(result)
        self._status = BackendStatus(
            state="playing",
            message="playing",
            active_session_id=plan.session_id,
            backend=self.model.name,
            device=device.backend,
        )
        return self._status

    def pause_session(self) -> BackendStatus:
        self.playback.pause()
        self._status = self._status.model_copy(update={"state": "paused", "message": "paused"})
        return self._status

    def resume_session(self) -> BackendStatus:
        self.playback.resume()
        self._status = self._status.model_copy(update={"state": "playing", "message": "playing"})
        return self._status

    def stop_session(self) -> BackendStatus:
        self._status = BackendStatus(state="idle", message="stopped", backend=self.model.name)
        return self._status
