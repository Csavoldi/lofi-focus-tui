try:
    from enum import StrEnum
except ImportError:  # pragma: no cover - compatibility for Python 3.10
    from enum import Enum

    class StrEnum(str, Enum):
        pass

from typing import Literal
from unicodedata import normalize

from pydantic import BaseModel, Field, field_validator, model_validator

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
    focus: str = "deep_work"
    preset: str
    duration_minutes: int = Field(ge=5, le=240)
    energy: EnergyLevel
    style_tags: list[str] = Field(default_factory=list)
    avoid_tags: list[str] = Field(default_factory=list)
    device_preference: str = "auto"
    generation: GenerationSettings | None = None
    seed: int | None = Field(default=None, ge=0)
    prompt: str = ""
    vocal_mode: Literal["instrumental", "vocals"] = "instrumental"

    @model_validator(mode="before")
    @classmethod
    def normalize_focus(cls, values):
        if not isinstance(values, dict):
            return values

        values = dict(values)
        if values.get("focus") is None:
            from lofi_focus_tui.options import LEGACY_FOCUS_VALUES, FocusValue, MusicPresetValue

            preset = values.get("preset")
            if isinstance(preset, str) and preset in LEGACY_FOCUS_VALUES:
                values["focus"] = preset
                values["preset"] = MusicPresetValue.CLASSIC_LOFI.value
            else:
                values["focus"] = FocusValue.DEEP_WORK.value
        return values

    @field_validator("focus")
    @classmethod
    def validate_focus(cls, value: str) -> str:
        from lofi_focus_tui.options import FOCUS_OPTIONS

        if value not in FOCUS_OPTIONS:
            raise ValueError(f"Unknown focus: {value}")
        return value

    @field_validator("preset")
    @classmethod
    def validate_preset(cls, value: str) -> str:
        from lofi_focus_tui.options import PRESET_OPTIONS

        if value not in PRESET_OPTIONS:
            raise ValueError(f"Unknown music preset: {value}")
        return value

    @field_validator("prompt", mode="before")
    @classmethod
    def normalize_prompt(cls, value):
        if not isinstance(value, str):
            return value
        value = value.strip()
        if len(normalize("NFC", value)) > 512:
            raise ValueError("Prompt must be 512 characters or fewer")
        return value

    @field_validator("vocal_mode", mode="before")
    @classmethod
    def normalize_vocal_mode(cls, value):
        if not isinstance(value, str):
            return value
        return value.strip().lower()


class VolumeAdjustment(BaseModel):
    delta: float = Field(ge=-1.0, le=1.0)


class SeekAdjustment(BaseModel):
    seconds: float = Field(ge=-86400.0, le=86400.0)


class ExportRequest(BaseModel):
    directory: str = Field(min_length=1)


class ExportResponse(BaseModel):
    message: str
    audio_path: str
    metadata_path: str


class SessionPlan(BaseModel):
    session_id: str
    focus: str
    seed: int
    preset: str
    duration_minutes: int
    energy: EnergyLevel
    phases: list[SessionPhase]
    tempo_range: tuple[int, int]
    key_center: str
    style_traits: list[str]
    avoid_traits: list[str]
    focus_constraints: list[str]
    continuity_requirements: list[str]
    prompt: str = ""
    vocal_mode: Literal["instrumental", "vocals"] = "instrumental"

    @field_validator("vocal_mode", mode="before")
    @classmethod
    def normalize_vocal_mode(cls, value):
        if not isinstance(value, str):
            return value
        return value.strip().lower()


class CompositionBlueprint(BaseModel):
    session_id: str
    seed: int
    focus: str
    focus_constraints: list[str]
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
    continuation_constraints: list[str] = Field(default_factory=list)
    prompt: str = ""
    vocal_mode: Literal["instrumental", "vocals"] = "instrumental"
    energy: EnergyLevel = EnergyLevel.STEADY

    @field_validator("vocal_mode", mode="before")
    @classmethod
    def normalize_vocal_mode(cls, value):
        if not isinstance(value, str):
            return value
        return value.strip().lower()


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
    playback: str = "unknown"
    volume: float = Field(default=0.8, ge=0.0, le=1.0)
    position_seconds: float = Field(default=0.0, ge=0.0)
    duration_seconds: float = Field(default=0.0, ge=0.0)
