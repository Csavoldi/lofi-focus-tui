from lofi_focus_tui.audio.cache import default_history_path, default_output_dir
from lofi_focus_tui.audio.output import OutputManager
from lofi_focus_tui.audio.playback import PlaybackManager
from lofi_focus_tui.audio.player import NullPlayer, SoundDevicePlayer
from lofi_focus_tui.backend.session_manager import SessionManager
from lofi_focus_tui.config import (
    AceStepHttpConfig,
    AppConfig,
    GenerationConfig,
    PlaybackConfig,
    RunPodConfig,
)
from lofi_focus_tui.generation.ace_step import AceStepAdapter
from lofi_focus_tui.generation.base import ModelAdapter
from lofi_focus_tui.generation.http_ace_step import AceStepHttpAdapter
from lofi_focus_tui.generation.mock import MockModelAdapter
from lofi_focus_tui.generation.runpod import RunPodAceStepAdapter
from lofi_focus_tui.history import HistoryStore


def build_model(config: AppConfig | GenerationConfig) -> ModelAdapter:
    generation = config.generation if isinstance(config, AppConfig) else config
    http_config = config.ace_step_http if isinstance(config, AppConfig) else AceStepHttpConfig()
    runpod_config = config.runpod if isinstance(config, AppConfig) else RunPodConfig()

    if generation.backend == "mock":
        return MockModelAdapter()
    if generation.backend == "ace-step":
        return AceStepAdapter(checkpoint_path=generation.checkpoint_path)
    if generation.backend == "ace-step-http":
        return AceStepHttpAdapter(
            base_url=http_config.base_url,
            api_key=http_config.api_key,
            timeout_seconds=http_config.timeout_seconds,
        )
    if generation.backend == "runpod":
        return RunPodAceStepAdapter(
            api_key=runpod_config.api_key,
            gpu_type=runpod_config.gpu_type,
            template_id=runpod_config.template_id,
            volume_id=runpod_config.volume_id,
            auto_destroy=runpod_config.auto_destroy,
            base_url=http_config.base_url,
            timeout_seconds=http_config.timeout_seconds,
        )
    raise ValueError(f"Unsupported generation backend: {generation.backend}")


def build_playback(config: PlaybackConfig) -> PlaybackManager:
    player = SoundDevicePlayer() if SoundDevicePlayer.available() else NullPlayer()
    return PlaybackManager(player=player, volume=config.volume, fade_seconds=config.fade_seconds)


def build_session_manager(config: AppConfig) -> SessionManager:
    return SessionManager(
        model=build_model(config),
        generation_defaults=config.generation.to_settings(),
        chunk_seconds=config.generation.chunk_seconds,
        playback=build_playback(config.playback),
        output_manager=OutputManager(default_output_dir()),
        history_store=HistoryStore(default_history_path()),
    )
