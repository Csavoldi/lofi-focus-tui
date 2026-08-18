from lofi_focus_tui import cli
from lofi_focus_tui.audio.output import OutputManager
from lofi_focus_tui.audio.player import NullPlayer, SoundDevicePlayer
from lofi_focus_tui.config import (
    AceStepHttpConfig,
    AppConfig,
    GenerationConfig,
    PlaybackConfig,
    RunPodConfig,
)
from lofi_focus_tui.generation.ace_step import AceStepAdapter
from lofi_focus_tui.generation.http_ace_step import AceStepHttpAdapter
from lofi_focus_tui.generation.mock import MockModelAdapter
from lofi_focus_tui.generation.runpod import RunPodAceStepAdapter
from lofi_focus_tui.history import HistoryStore
from lofi_focus_tui.runtime import build_model, build_playback, build_session_manager


def test_cli_main_reuses_one_config_for_manager_and_app(monkeypatch):
    config = AppConfig(theme="vhs")
    manager = object()
    seen = {}

    class FakeApp:
        def __init__(self, *, session_manager, config):
            seen["app_manager"] = session_manager
            seen["app_config"] = config

        def run(self):
            seen["ran"] = True

    def fake_build_session_manager(passed_config):
        seen["manager_config"] = passed_config
        return manager

    monkeypatch.setattr(cli, "load_config", lambda: config)
    monkeypatch.setattr(cli, "build_session_manager", fake_build_session_manager)
    monkeypatch.setattr(cli, "LofiFocusApp", FakeApp)

    cli.main()

    assert seen == {
        "manager_config": config,
        "app_manager": manager,
        "app_config": config,
        "ran": True,
    }


def test_build_session_manager_wires_configured_runtime(monkeypatch, tmp_path):
    output_dir = tmp_path / "outputs"
    history_path = tmp_path / "history.jsonl"
    monkeypatch.setattr(
        "lofi_focus_tui.runtime.default_output_dir", lambda: output_dir
    )
    monkeypatch.setattr(
        "lofi_focus_tui.runtime.default_history_path", lambda: history_path
    )
    monkeypatch.setattr(SoundDevicePlayer, "available", staticmethod(lambda: False))
    config = AppConfig(
        generation=GenerationConfig(
            backend="mock",
            inference_steps=12,
            guidance_scale=8.5,
            batch_size=2,
            chunk_seconds=240,
        ),
        playback=PlaybackConfig(volume=0.35, fade_seconds=2.5),
    )

    manager = build_session_manager(config)

    assert isinstance(manager.model, MockModelAdapter)
    assert manager.generation_defaults.model_dump() == {
        "output_format": "wav",
        "inference_steps": 12,
        "guidance_scale": 8.5,
        "batch_size": 2,
        "seed": -1,
        "scheduler_type": "euler",
        "cfg_type": "apg",
        "omega_scale": 10.0,
    }
    assert manager.chunk_seconds == 240
    assert isinstance(manager.playback.player, NullPlayer)
    assert manager.playback.volume == 0.35
    assert manager.playback.fade_seconds == 2.5
    assert isinstance(manager.output_manager, OutputManager)
    assert manager.output_manager.base_dir == output_dir
    assert isinstance(manager.history_store, HistoryStore)
    assert manager.history_store.path == history_path


def test_build_playback_uses_null_player_without_sounddevice(monkeypatch):
    monkeypatch.setattr(SoundDevicePlayer, "available", staticmethod(lambda: False))

    playback = build_playback(PlaybackConfig(volume=0.25, fade_seconds=2.0))

    assert isinstance(playback.player, NullPlayer)
    assert playback.volume == 0.25
    assert playback.fade_seconds == 2.0


def test_build_playback_uses_sounddevice_player_when_available(monkeypatch):
    monkeypatch.setattr(SoundDevicePlayer, "available", staticmethod(lambda: True))

    playback = build_playback(PlaybackConfig(volume=0.5))

    assert isinstance(playback.player, SoundDevicePlayer)
    assert playback.volume == 0.5


def test_build_model_preserves_http_configuration():
    config = AppConfig(
        generation=GenerationConfig(backend="ace-step-http"),
        ace_step_http=AceStepHttpConfig(
            base_url="https://ace.example/",
            api_key="secret",
            timeout_seconds=42.5,
        ),
    )

    model = build_model(config)

    assert isinstance(model, AceStepHttpAdapter)
    assert model.base_url == "https://ace.example"
    assert model.api_key == "secret"
    assert model.timeout_seconds == 42.5


def test_build_model_preserves_embedded_checkpoint_configuration():
    model = build_model(
        AppConfig(
            generation=GenerationConfig(
                backend="ace-step", checkpoint_path="/models/ace-step"
            )
        )
    )

    assert isinstance(model, AceStepAdapter)
    assert model.checkpoint_path == "/models/ace-step"


def test_build_model_preserves_runpod_configuration():
    config = AppConfig(
        generation=GenerationConfig(backend="runpod"),
        ace_step_http=AceStepHttpConfig(
            base_url="https://ace.example",
            timeout_seconds=99.0,
        ),
        runpod=RunPodConfig(
            api_key="runpod-secret",
            gpu_type="NVIDIA A10G",
            template_id="template-123",
            volume_id="volume-456",
            auto_destroy=False,
        ),
    )

    model = build_model(config)

    assert isinstance(model, RunPodAceStepAdapter)
    assert model.api_key == "runpod-secret"
    assert model.gpu_type == "NVIDIA A10G"
    assert model.template_id == "template-123"
    assert model.volume_id == "volume-456"
    assert model.auto_destroy is False
    assert model.base_url == "https://ace.example"
    assert model.timeout_seconds == 99.0
