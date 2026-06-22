from __future__ import annotations

import importlib
import importlib.util
from typing import Protocol

import numpy as np


class Player(Protocol):
    def play(self, audio: np.ndarray, sample_rate: int, volume: float = 1.0) -> None:
        ...

    def pause(self) -> bool:
        ...

    def resume(self) -> bool:
        ...

    def stop(self) -> None:
        ...


class NullPlayer:
    def __init__(self) -> None:
        self.audio: np.ndarray | None = None
        self.sample_rate: int | None = None
        self.volume = 1.0
        self.state = "stopped"

    def play(self, audio: np.ndarray, sample_rate: int, volume: float = 1.0) -> None:
        self.audio = np.array(audio, copy=True)
        self.sample_rate = sample_rate
        self.volume = volume
        self.state = "playing"

    def pause(self) -> bool:
        self.state = "paused"
        return True

    def resume(self) -> bool:
        self.state = "playing"
        return True

    def stop(self) -> None:
        self.state = "stopped"


class SoundDevicePlayer:
    def __init__(self) -> None:
        self._audio: np.ndarray | None = None
        self._sample_rate: int | None = None
        self._frame = 0
        self._stream = None
        self.state = "stopped"

    def play(self, audio: np.ndarray, sample_rate: int, volume: float = 1.0) -> None:
        self.stop()
        output = self._prepare_audio(audio)
        if volume != 1.0:
            output = np.ascontiguousarray(output * np.float32(volume), dtype=np.float32)
        self._audio = output
        self._sample_rate = sample_rate
        self._frame = 0
        self._start_stream()

    def pause(self) -> bool:
        self._close_stream()
        self.state = "paused"
        return True

    def resume(self) -> bool:
        if self._audio is None or self._sample_rate is None:
            return False
        if self._frame >= len(self._audio):
            return False
        self._start_stream()
        return True

    def stop(self) -> None:
        self._close_stream()
        self._audio = None
        self._sample_rate = None
        self._frame = 0
        self.state = "stopped"

    @staticmethod
    def available() -> bool:
        try:
            return importlib.util.find_spec("sounddevice") is not None
        except (ImportError, ValueError):
            return False

    def _sounddevice(self):
        return importlib.import_module("sounddevice")

    @staticmethod
    def _prepare_audio(audio: np.ndarray) -> np.ndarray:
        output = np.asarray(audio, dtype=np.float32)
        if output.ndim == 1:
            output = output.reshape(-1, 1)
        return np.ascontiguousarray(output, dtype=np.float32)

    def _start_stream(self) -> None:
        if self._audio is None or self._sample_rate is None:
            return
        self._close_stream()
        sounddevice = self._sounddevice()
        self._stream = sounddevice.OutputStream(
            samplerate=self._sample_rate,
            channels=self._audio.shape[1],
            dtype="float32",
            callback=self._write_audio,
        )
        try:
            self._stream.start()
        except Exception:
            self._close_stream()
            raise
        self.state = "playing"

    def _write_audio(self, outdata, frames: int, time, status) -> None:
        del time, status
        if self._audio is None:
            outdata[:] = 0
            raise self._sounddevice().CallbackStop()
        start = self._frame
        stop = min(start + frames, len(self._audio))
        chunk = self._audio[start:stop]
        outdata[: len(chunk)] = chunk
        if len(chunk) < frames:
            outdata[len(chunk) :] = 0
        self._frame = stop
        if stop >= len(self._audio):
            self.state = "stopped"
            raise self._sounddevice().CallbackStop()

    def _close_stream(self) -> None:
        if self._stream is None:
            return
        self._stream.stop()
        self._stream.close()
        self._stream = None
