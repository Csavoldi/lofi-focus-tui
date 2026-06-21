from lofi_focus_tui.audio.player import NullPlayer, Player
from lofi_focus_tui.generation.base import GenerationResult


class PlaybackManager:
    def __init__(self, player: Player | None = None, volume: float = 0.8) -> None:
        self.player = player or NullPlayer()
        self.volume = volume
        self.current: GenerationResult | None = None
        self.paused = False
        self.last_error: str | None = None

    def load(self, result: GenerationResult) -> None:
        try:
            self.player.play(result.audio, result.sample_rate, self.volume)
            self.last_error = None
        except Exception as exc:
            self.last_error = str(exc)
            try:
                self.player.stop()
            except Exception:
                pass
            self.player = NullPlayer()
            self.player.play(result.audio, result.sample_rate, self.volume)
        self.current = result
        self.paused = False

    def pause(self) -> bool:
        if self.current is None:
            return False
        self.paused = True
        if self.player.pause() is False:
            self.paused = False
            return False
        return True

    def resume(self) -> bool:
        if self.current is None:
            return False
        if self.player.resume() is False:
            return False
        self.paused = False
        return True

    def stop(self) -> None:
        self.current = None
        self.paused = False
        self.player.stop()
