import json
import re
import shutil
import wave
from pathlib import Path

import numpy as np

from lofi_focus_tui.generation.base import GenerationResult


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return (slug or "session")[:40]


class OutputManager:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_session_dir(self, session_id: str, preset: str) -> Path:
        directory = self.base_dir / f"{session_id}_{slugify(preset)}"
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def save_wav(
        self,
        result: GenerationResult,
        directory: Path,
        filename: str = "audio.wav",
    ) -> Path:
        path = directory / filename
        audio = np.asarray(result.audio, dtype=np.float32)
        channels = 1
        if audio.ndim == 2:
            channels = audio.shape[1]
        pcm = np.clip(audio, -1.0, 1.0)
        pcm = (pcm * np.iinfo(np.int16).max).astype(np.int16)
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(channels)
            wav.setsampwidth(2)
            wav.setframerate(result.sample_rate)
            wav.writeframes(pcm.tobytes())
        return path

    def save_metadata(self, metadata: dict, directory: Path) -> Path:
        path = directory / "metadata.json"
        path.write_text(
            json.dumps(metadata, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return path

    def export_session(self, audio_path: Path, directory: Path) -> tuple[Path, Path]:
        audio_path = Path(audio_path).expanduser()
        if not audio_path.is_file():
            raise FileNotFoundError(f"audio file not found: {audio_path}")
        metadata_path = audio_path.parent / "metadata.json"
        if not metadata_path.is_file():
            raise FileNotFoundError(f"metadata file not found: {metadata_path}")

        export_dir = Path(directory).expanduser()
        session_dir = export_dir / audio_path.parent.name
        session_dir.mkdir(parents=True, exist_ok=True)
        exported_audio = session_dir / "audio.wav"
        exported_metadata = session_dir / "metadata.json"
        shutil.copy2(audio_path, exported_audio)
        shutil.copy2(metadata_path, exported_metadata)
        return exported_audio, exported_metadata
