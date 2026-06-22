from dataclasses import dataclass
from typing import Protocol

import numpy as np

from lofi_focus_tui.domain import CompositionBlueprint
from lofi_focus_tui.generation.settings import GenerationSettings


class GenerationCancelledError(RuntimeError):
    pass


@dataclass(frozen=True)
class GenerationResult:
    audio: np.ndarray
    sample_rate: int
    duration_seconds: float
    metadata: dict[str, str]


class ModelAdapter(Protocol):
    name: str

    def generate(
        self,
        blueprint: CompositionBlueprint,
        duration_seconds: int,
        settings: GenerationSettings | None = None,
    ) -> GenerationResult:
        ...
