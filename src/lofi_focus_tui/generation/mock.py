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
        root_frequency = 110 + (seed % 20)
        pad = (
            0.024 * np.sin(2 * np.pi * root_frequency * t)
            + 0.016 * np.sin(2 * np.pi * (root_frequency + 28) * t + 0.4)
            + 0.010 * np.sin(2 * np.pi * (root_frequency + 55) * t + 1.1)
        )
        audio = pad * (0.8 + 0.2 * np.sin(2 * np.pi * 0.35 * t))
        return GenerationResult(
            audio=audio.astype(np.float32),
            sample_rate=sample_rate,
            duration_seconds=duration_seconds,
            metadata={"session_id": blueprint.session_id, "backend": self.name},
        )
