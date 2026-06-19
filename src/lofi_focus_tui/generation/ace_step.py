import importlib.util
import os
import wave
from pathlib import Path

import numpy as np

from lofi_focus_tui.domain import CompositionBlueprint
from lofi_focus_tui.generation.base import GenerationResult


class AceStepUnavailableError(RuntimeError):
    pass


class AceStepAdapter:
    name = "ace-step"

    def __init__(
        self,
        pipeline: object | None = None,
        output_dir: Path | None = None,
        checkpoint_path: str = "",
        bf16: bool = True,
        torch_compile: bool = False,
        cpu_offload: bool = True,
        overlapped_decode: bool = True,
    ) -> None:
        self._pipeline = pipeline
        self.output_dir = output_dir or _default_output_dir()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path = checkpoint_path
        self.bf16 = bf16
        self.torch_compile = torch_compile
        self.cpu_offload = cpu_offload
        self.overlapped_decode = overlapped_decode

    @property
    def available(self) -> bool:
        return importlib.util.find_spec("acestep") is not None

    def _load_pipeline(self) -> object:
        if self._pipeline is not None:
            return self._pipeline
        if not self.available:
            raise AceStepUnavailableError(
                "ACE-Step is not installed. Install with: python -m pip install -e '.[ace-step]'"
            )
        from acestep.pipeline_ace_step import ACEStepPipeline

        self._pipeline = ACEStepPipeline(
            checkpoint_dir=self.checkpoint_path,
            dtype="bfloat16" if self.bf16 else "float32",
            torch_compile=self.torch_compile,
            cpu_offload=self.cpu_offload,
            overlapped_decode=self.overlapped_decode,
        )
        return self._pipeline

    def generate(self, blueprint: CompositionBlueprint, duration_seconds: int) -> GenerationResult:
        pipeline = self._load_pipeline()
        save_path = self.output_dir / f"{blueprint.session_id}.wav"
        prompt = _blueprint_to_prompt(blueprint)

        pipeline(
            audio_duration=duration_seconds,
            prompt=prompt,
            lyrics="",
            infer_step=27,
            guidance_scale=15.0,
            scheduler_type="euler",
            cfg_type="apg",
            omega_scale=10.0,
            manual_seeds=str(blueprint.seed),
            guidance_interval=0.5,
            guidance_interval_decay=0.0,
            min_guidance_scale=3.0,
            use_erg_tag=True,
            use_erg_lyric=False,
            use_erg_diffusion=True,
            oss_steps="",
            guidance_scale_text=0.0,
            guidance_scale_lyric=0.0,
            save_path=str(save_path),
        )

        audio, sample_rate = _read_wav(save_path)
        return GenerationResult(
            audio=audio,
            sample_rate=sample_rate,
            duration_seconds=duration_seconds,
            metadata={"session_id": blueprint.session_id, "backend": self.name, "path": str(save_path)},
        )


def _blueprint_to_prompt(blueprint: CompositionBlueprint) -> str:
    parts = [
        "instrumental focus music",
        f"{blueprint.tempo_bpm} bpm",
        blueprint.key_center,
        blueprint.motif,
        blueprint.drum_feel,
        blueprint.bass_behavior,
        ", ".join(blueprint.texture_layers),
        "continuous coherent arrangement",
        "no vocals",
    ]
    return ", ".join(part for part in parts if part)


def _default_output_dir() -> Path:
    cache_root = os.environ.get("XDG_CACHE_HOME")
    if cache_root:
        return Path(cache_root) / "lofi-focus-tui" / "ace-step"
    return Path.cwd() / ".cache" / "lofi-focus-tui" / "ace-step"


def _read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sample_rate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    return audio, sample_rate
