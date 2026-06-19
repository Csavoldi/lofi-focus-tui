from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class EnergyLevel(StrEnum):
    LOW = "low"
    STEADY = "steady"
    HIGH = "high"


class SessionPhase(StrEnum):
    WARMUP = "warmup"
    STEADY_WORK = "steady_work"
    COOLDOWN = "cooldown"


class SessionRequest(BaseModel):
    preset: str
    duration_minutes: int = Field(ge=5, le=240)
    energy: EnergyLevel
    style_tags: list[str] = Field(default_factory=list)
    avoid_tags: list[str] = Field(default_factory=list)
    device_preference: str = "auto"


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
    state: Literal["idle", "planning", "generating", "playing", "paused", "error"]
    message: str
    active_session_id: str | None = None
    backend: str = "mock"
    device: str = "cpu"
