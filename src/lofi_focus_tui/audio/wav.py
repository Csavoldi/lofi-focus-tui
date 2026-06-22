import io
import wave
from pathlib import Path
from typing import BinaryIO

import numpy as np


def read_wav_file(path: Path) -> tuple[np.ndarray, int]:
    try:
        with path.open("rb") as wav_file:
            return _read_pcm_wav(wav_file)
    except wave.Error as exc:
        return _read_with_soundfile(path, exc)


def read_wav_bytes(content: bytes) -> tuple[np.ndarray, int]:
    buffer = io.BytesIO(content)
    try:
        return _read_pcm_wav(buffer)
    except wave.Error as exc:
        buffer.seek(0)
        return _read_with_soundfile(buffer, exc)


def _read_pcm_wav(source: BinaryIO) -> tuple[np.ndarray, int]:
    with wave.open(source, "rb") as wav:
        channels = wav.getnchannels()
        sample_rate = wav.getframerate()
        sample_width = wav.getsampwidth()
        frames = wav.readframes(wav.getnframes())
    audio = _decode_pcm_frames(frames, sample_width)
    if channels > 1 and audio.size:
        audio = audio.reshape(-1, channels).mean(axis=1)
    return audio.astype(np.float32, copy=False), sample_rate


def _decode_pcm_frames(frames: bytes, sample_width: int) -> np.ndarray:
    if not frames:
        return np.array([], dtype=np.float32)
    if sample_width == 1:
        samples = np.frombuffer(frames, dtype=np.uint8).astype(np.float32)
        return (samples - 128.0) / 128.0
    if sample_width == 2:
        return np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    if sample_width == 3:
        raw = np.frombuffer(frames, dtype=np.uint8).reshape(-1, 3)
        samples = (
            raw[:, 0].astype(np.int32)
            | (raw[:, 1].astype(np.int32) << 8)
            | (raw[:, 2].astype(np.int32) << 16)
        )
        samples = np.where(samples & 0x800000, samples - 0x1000000, samples)
        return samples.astype(np.float32) / float(1 << 23)
    if sample_width == 4:
        return np.frombuffer(frames, dtype="<i4").astype(np.float32) / float(1 << 31)
    raise wave.Error(f"unsupported PCM sample width: {sample_width}")


def _read_with_soundfile(
    source: Path | BinaryIO,
    original_error: Exception,
) -> tuple[np.ndarray, int]:
    try:
        import soundfile as sf
    except ImportError as exc:
        raise RuntimeError(
            "Unsupported WAV encoding. Install soundfile to read non-PCM WAV output."
        ) from original_error or exc
    audio, sample_rate = sf.read(source, dtype="float32", always_2d=False)
    samples = np.asarray(audio, dtype=np.float32)
    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    return samples, int(sample_rate)
