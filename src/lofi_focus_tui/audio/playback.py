from lofi_focus_tui.generation.base import GenerationResult


class PlaybackManager:
    def __init__(self) -> None:
        self.current: GenerationResult | None = None
        self.paused = False

    def load(self, result: GenerationResult) -> None:
        self.current = result
        self.paused = False

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False

    def stop(self) -> None:
        self.current = None
        self.paused = False
