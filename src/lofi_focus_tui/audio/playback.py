from lofi_focus_tui.audio.normalization import apply_fade
from lofi_focus_tui.audio.player import NullPlayer, Player
from lofi_focus_tui.generation.base import GenerationResult


class PlaybackManager:
    def __init__(
        self,
        player: Player | None = None,
        volume: float = 0.8,
        fade_seconds: float = 0.0,
    ) -> None:
        self.player = player or NullPlayer()
        self.volume = volume
        self.fade_seconds = fade_seconds
        self.current: GenerationResult | None = None
        self.paused = False
        self.last_error: str | None = None

    def load(self, result: GenerationResult) -> None:
        playback_audio = apply_fade(result.audio, result.sample_rate, self.fade_seconds)
        try:
            self.player.play(playback_audio, result.sample_rate, self.volume)
            self.last_error = None
        except Exception as exc:
            self.last_error = str(exc)
            try:
                self.player.stop()
            except Exception:
                pass
            self.player = NullPlayer()
            self.player.play(playback_audio, result.sample_rate, self.volume)
        self.current = result
        self.paused = False

    @property
    def mode(self) -> str:
        if isinstance(self.player, NullPlayer):
            return "disabled"
        return self.player.__class__.__name__.removesuffix("Player").lower()

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
