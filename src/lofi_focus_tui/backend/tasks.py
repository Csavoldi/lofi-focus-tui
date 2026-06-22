from dataclasses import dataclass, field
from threading import Event
from time import monotonic

from lofi_focus_tui.domain import BackendState


@dataclass
class GenerationTask:
    task_id: str
    session_id: str
    state: BackendState = BackendState.PLANNING
    progress: float = 0.0
    message: str = "planning"
    error: str | None = None
    output_path: str | None = None
    cancel_event: Event = field(default_factory=Event)
    started_at: float = field(default_factory=monotonic)
    updated_at: float = field(default_factory=monotonic)

    def update(self, state: BackendState, message: str, progress: float) -> None:
        self.state = state
        self.message = message
        self.progress = max(0.0, min(1.0, progress))
        self.updated_at = monotonic()
