import math
import wave
from pathlib import Path

from lofi_focus_tui.composition import create_blueprint
from lofi_focus_tui.domain import EnergyLevel, SessionRequest
from lofi_focus_tui.generation.ace_step import AceStepAdapter
from lofi_focus_tui.generation.settings import GenerationSettings
from lofi_focus_tui.presets import expand_preset


class FakePipeline:
    def __init__(self):
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        save_path = Path(kwargs["save_path"])
        sample_rate = 44100
        duration = int(kwargs["audio_duration"])
        frames = []
        for index in range(sample_rate * duration):
            value = int(12000 * math.sin(2 * math.pi * 220 * (index / sample_rate)))
            frames.append(value.to_bytes(2, byteorder="little", signed=True))
        with wave.open(str(save_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(b"".join(frames))


def test_ace_step_adapter_reports_dependency_status():
    adapter = AceStepAdapter()

    assert adapter.name == "ace-step"
    assert isinstance(adapter.available, bool)


def test_ace_step_adapter_calls_pipeline_with_blueprint_prompt(tmp_path):
    fake_pipeline = FakePipeline()
    adapter = AceStepAdapter(pipeline=fake_pipeline, output_dir=tmp_path)
    plan = expand_preset(
        SessionRequest(
            preset="deep_work",
            duration_minutes=30,
            energy=EnergyLevel.STEADY,
            style_tags=["lofi"],
            avoid_tags=["vocals"],
        )
    )
    blueprint = create_blueprint(plan)

    result = adapter.generate(blueprint, duration_seconds=2)

    assert result.sample_rate == 44100
    assert result.duration_seconds == 2
    assert result.audio.shape[0] == 88200
    assert fake_pipeline.calls[0]["audio_duration"] == 2
    assert str(blueprint.tempo_bpm) in fake_pipeline.calls[0]["prompt"]


def test_ace_step_adapter_passes_generation_settings_to_pipeline(tmp_path):
    fake_pipeline = FakePipeline()
    adapter = AceStepAdapter(pipeline=fake_pipeline, output_dir=tmp_path)
    plan = expand_preset(
        SessionRequest(
            preset="deep_work",
            duration_minutes=30,
            energy=EnergyLevel.STEADY,
            seed=123,
        )
    )
    blueprint = create_blueprint(plan)
    settings = GenerationSettings(
        output_format="wav",
        inference_steps=44,
        guidance_scale=7.5,
        seed=456,
        scheduler_type="ddim",
        cfg_type="cfg",
        omega_scale=2.5,
    )

    result = adapter.generate(blueprint, duration_seconds=1, settings=settings)

    call = fake_pipeline.calls[0]
    assert call["infer_step"] == 44
    assert call["guidance_scale"] == 7.5
    assert call["scheduler_type"] == "ddim"
    assert call["cfg_type"] == "cfg"
    assert call["omega_scale"] == 2.5
    assert call["manual_seeds"] == "456"
    assert call["save_path"].endswith(".wav")
    assert result.metadata["output_path"].endswith(".wav")
    assert result.metadata["path"].endswith(".wav")
