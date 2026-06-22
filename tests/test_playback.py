import sys

import numpy as np

from lofi_focus_tui.audio.playback import PlaybackManager
from lofi_focus_tui.audio.player import NullPlayer, SoundDevicePlayer
from lofi_focus_tui.generation.base import GenerationResult


def make_result() -> GenerationResult:
    return GenerationResult(
        audio=np.array([0.25, -0.5], dtype=np.float32),
        sample_rate=22050,
        duration_seconds=1,
        metadata={},
    )


class FakePlayer:
    def __init__(self) -> None:
        self.calls = []

    def play(self, audio: np.ndarray, sample_rate: int, volume: float = 1.0) -> None:
        self.calls.append(("play", audio, sample_rate, volume))

    def pause(self) -> None:
        self.calls.append(("pause",))

    def resume(self) -> None:
        self.calls.append(("resume",))

    def stop(self) -> None:
        self.calls.append(("stop",))


class FailingPlayer(FakePlayer):
    def play(self, audio: np.ndarray, sample_rate: int, volume: float = 1.0) -> None:
        raise RuntimeError("no output device")


class CannotResumePlayer(FakePlayer):
    def resume(self) -> bool:
        self.calls.append(("resume",))
        return False


def test_load_stores_current_and_calls_player_play():
    result = make_result()
    player = FakePlayer()
    manager = PlaybackManager(player=player, volume=0.4)
    manager.paused = True

    manager.load(result)

    assert manager.current is result
    assert manager.paused is False
    assert player.calls[0][0] == "play"
    np.testing.assert_array_equal(player.calls[0][1], result.audio)
    assert player.calls[0][2:] == (result.sample_rate, 0.4)


def test_load_applies_configured_playback_fade_without_mutating_result():
    result = GenerationResult(
        audio=np.ones(10, dtype=np.float32),
        sample_rate=10,
        duration_seconds=1,
        metadata={},
    )
    player = FakePlayer()
    manager = PlaybackManager(player=player, fade_seconds=0.2)

    manager.load(result)

    played_audio = player.calls[0][1]
    assert played_audio[0] == 0.0
    assert played_audio[-1] == 0.0
    np.testing.assert_array_equal(result.audio, np.ones(10, dtype=np.float32))


def test_pause_calls_player_pause_and_sets_paused():
    player = FakePlayer()
    manager = PlaybackManager(player=player)
    manager.load(make_result())
    player.calls.clear()

    manager.pause()

    assert manager.paused is True
    assert player.calls == [("pause",)]


def test_pause_without_loaded_audio_returns_false():
    player = FakePlayer()
    manager = PlaybackManager(player=player)

    assert manager.pause() is False
    assert manager.paused is False
    assert player.calls == []


def test_resume_calls_player_resume_and_clears_paused():
    player = FakePlayer()
    manager = PlaybackManager(player=player)
    manager.load(make_result())
    player.calls.clear()
    manager.paused = True

    manager.resume()

    assert manager.paused is False
    assert player.calls == [("resume",)]


def test_resume_without_loaded_audio_returns_false():
    player = FakePlayer()
    manager = PlaybackManager(player=player)
    manager.paused = True

    assert manager.resume() is False
    assert manager.paused is True
    assert player.calls == []


def test_resume_keeps_paused_state_when_player_cannot_resume():
    player = CannotResumePlayer()
    manager = PlaybackManager(player=player)
    manager.load(make_result())
    player.calls.clear()
    manager.paused = True

    assert manager.resume() is False
    assert manager.paused is True
    assert player.calls == [("resume",)]


def test_stop_clears_current_and_paused_then_calls_player_stop():
    player = FakePlayer()
    manager = PlaybackManager(player=player)
    manager.load(make_result())
    manager.paused = True

    manager.stop()

    assert manager.current is None
    assert manager.paused is False
    assert player.calls[-1] == ("stop",)


def test_load_falls_back_to_null_player_when_output_device_fails():
    manager = PlaybackManager(player=FailingPlayer(), volume=0.3)
    result = make_result()

    manager.load(result)

    assert manager.current is result
    assert manager.last_error == "no output device"
    assert isinstance(manager.player, NullPlayer)
    assert manager.player.volume == 0.3
    np.testing.assert_array_equal(manager.player.audio, result.audio)


def test_null_player_records_last_audio_and_state():
    player = NullPlayer()
    audio = np.array([0.1, -0.2], dtype=np.float32)

    player.play(audio, 48000, volume=0.25)

    assert player.state == "playing"
    assert player.sample_rate == 48000
    assert player.volume == 0.25
    np.testing.assert_array_equal(player.audio, audio)

    player.pause()
    assert player.state == "paused"

    player.resume()
    assert player.state == "playing"

    player.stop()
    assert player.state == "stopped"


def test_sounddevice_player_constructs_without_importing_sounddevice(monkeypatch):
    monkeypatch.setitem(sys.modules, "sounddevice", None)

    SoundDevicePlayer()


def test_sounddevice_player_play_uses_stream_with_contiguous_volume(monkeypatch):
    class FakeStream:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs
            self.started = False
            self.stopped = False
            self.closed = False

        def start(self) -> None:
            self.started = True

        def stop(self) -> None:
            self.stopped = True

        def close(self) -> None:
            self.closed = True

    class FakeSoundDevice:
        def __init__(self) -> None:
            self.streams = []
            self.CallbackStop = RuntimeError

        def OutputStream(self, **kwargs):
            stream = FakeStream(**kwargs)
            self.streams.append(stream)
            return stream

    fake_sounddevice = FakeSoundDevice()
    monkeypatch.setitem(sys.modules, "sounddevice", fake_sounddevice)
    source = np.array([[0.5, 0.0], [-1.0, 0.0]], dtype=np.float64)[:, 0]
    player = SoundDevicePlayer()

    player.play(source, 44100, volume=0.5)

    stream = fake_sounddevice.streams[0]
    assert stream.started is True
    assert stream.kwargs["samplerate"] == 44100
    assert stream.kwargs["channels"] == 1
    assert stream.kwargs["dtype"] == "float32"

    outdata = np.empty((2, 1), dtype=np.float32)
    try:
        stream.kwargs["callback"](outdata, 2, None, None)
    except RuntimeError:
        pass

    assert player._audio.dtype == np.float32
    assert player._audio.flags["C_CONTIGUOUS"]
    np.testing.assert_array_equal(outdata, np.array([[0.25], [-0.5]], dtype=np.float32))
    assert player.state == "stopped"


def test_sounddevice_player_pause_resume_continues_from_current_frame(monkeypatch):
    class FakeStream:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs
            self.started = False
            self.stopped = False
            self.closed = False

        def start(self) -> None:
            self.started = True

        def stop(self) -> None:
            self.stopped = True

        def close(self) -> None:
            self.closed = True

    class FakeSoundDevice:
        def __init__(self) -> None:
            self.streams = []
            self.CallbackStop = RuntimeError

        def OutputStream(self, **kwargs):
            stream = FakeStream(**kwargs)
            self.streams.append(stream)
            return stream

    fake_sounddevice = FakeSoundDevice()
    monkeypatch.setitem(sys.modules, "sounddevice", fake_sounddevice)
    player = SoundDevicePlayer()
    player.play(np.array([0.1, 0.2, 0.3], dtype=np.float32), 44100)
    first_stream = fake_sounddevice.streams[0]
    first_chunk = np.empty((1, 1), dtype=np.float32)
    first_stream.kwargs["callback"](first_chunk, 1, None, None)

    player.pause()
    player.resume()

    assert first_stream.stopped is True
    assert first_stream.closed is True
    second_stream = fake_sounddevice.streams[1]
    second_chunk = np.empty((2, 1), dtype=np.float32)
    try:
        second_stream.kwargs["callback"](second_chunk, 2, None, None)
    except RuntimeError:
        pass
    np.testing.assert_array_equal(second_chunk, np.array([[0.2], [0.3]], dtype=np.float32))

    player.stop()

    assert player.state == "stopped"
    assert player._audio is None


def test_sounddevice_player_closes_stream_when_start_fails(monkeypatch):
    class FailingStream:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs
            self.stopped = False
            self.closed = False

        def start(self) -> None:
            raise RuntimeError("stream failed")

        def stop(self) -> None:
            self.stopped = True

        def close(self) -> None:
            self.closed = True

    class FakeSoundDevice:
        def __init__(self) -> None:
            self.streams = []
            self.CallbackStop = RuntimeError

        def OutputStream(self, **kwargs):
            stream = FailingStream(**kwargs)
            self.streams.append(stream)
            return stream

    fake_sounddevice = FakeSoundDevice()
    monkeypatch.setitem(sys.modules, "sounddevice", fake_sounddevice)
    player = SoundDevicePlayer()

    try:
        player.play(np.array([0.1], dtype=np.float32), 44100)
    except RuntimeError:
        pass

    assert fake_sounddevice.streams[0].stopped is True
    assert fake_sounddevice.streams[0].closed is True
    assert player._stream is None
