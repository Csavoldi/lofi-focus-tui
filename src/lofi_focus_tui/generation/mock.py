import numpy as np

from lofi_focus_tui.domain import CompositionBlueprint
from lofi_focus_tui.generation.base import GenerationResult
from lofi_focus_tui.generation.settings import GenerationSettings


class MockModelAdapter:
    name = "mock"

    def generate(
        self,
        blueprint: CompositionBlueprint,
        duration_seconds: int,
        settings: GenerationSettings | None = None,
    ) -> GenerationResult:
        sample_rate = 44100
        t = np.linspace(0, duration_seconds, sample_rate * duration_seconds, endpoint=False)
        seed = settings.seed if settings is not None and settings.seed >= 0 else blueprint.seed
        base_frequency = 220 + (seed % 80)
        audio = 0.05 * np.sin(2 * np.pi * base_frequency * t)
        return GenerationResult(
            audio=audio.astype(np.float32),
            sample_rate=sample_rate,
            duration_seconds=duration_seconds,
            metadata={"session_id": blueprint.session_id, "backend": self.name},
        )
