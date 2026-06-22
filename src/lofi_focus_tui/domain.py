try:
    from enum import StrEnum
except ImportError:  # pragma: no cover - compatibility for Python 3.10
    from enum import Enum

    class StrEnum(str, Enum):
        pass

from typing import Literal

from pydantic import BaseModel, Field

from lofi_focus_tui.generation.settings import GenerationSettings


class EnergyLevel(StrEnum):
    LOW = "low"
    STEADY = "steady"
    HIGH = "high"


class SessionPhase(StrEnum):
    WARMUP = "warmup"
    STEADY_WORK = "steady_work"
    COOLDOWN = "cooldown"


class BackendState(StrEnum):
    IDLE = "idle"
    PLANNING = "planning"
    GENERATING = "generating"
    READY = "ready"
    PLAYING = "playing"
    PAUSED = "paused"
    ERROR = "error"


class SessionRequest(BaseModel):
    preset: str
    duration_minutes: int = Field(ge=5, le=240)
    energy: EnergyLevel
    style_tags: list[str] = Field(default_factory=list)
    avoid_tags: list[str] = Field(default_factory=list)
    device_preference: str = "auto"
    generation: GenerationSettings | None = None
    seed: int | None = Field(default=None, ge=0)


class SessionPlan(BaseModel):
    session_id: str
    seed: int
    preset: str
    duration_minutes: int
    energy: EnergyLevel
    phases: list[SessionPhase]
    tempo_range: tuple[int, int]
    key_center: str
    style_traits: list[str]
    avoid_traits: list[str]
    continuity_requirements: list[str]


class CompositionBlueprint(BaseModel):
    session_id: str
    seed: int
    tempo_bpm: int
    meter: Literal["4/4", "3/4", "6/8"] = "4/4"
    key_center: str
    harmonic_palette: list[str]
    motif: str
    drum_feel: str
    bass_behavior: str
    texture_layers: list[str]
    arrangement_sections: list[str]
    boundary_constraints: list[str]


class BackendStatus(BaseModel):
    state: BackendState
    message: str
    active_session_id: str | None = None
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    active_task_id: str | None = None
    output_path: str | None = None
    error: str | None = None
    recent_sessions: list[str] = Field(default_factory=list)
    chunk_index: int = Field(default=0, ge=0)
    chunk_count: int = Field(default=0, ge=0)
    backend: str = "mock"
    device: str = "cpu"
