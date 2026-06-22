# Configuration

`lofi-focus-tui` loads configuration from `config.toml` in the current directory, then from `~/.config/lofi-focus-tui/config.toml`. Missing files use defaults.

See `config.example.toml` for a complete starting point.

## Server

```toml
[server]
host = "127.0.0.1"
port = 8765
```

The backend listens on this host and port. The TUI client uses the same values when created from config.

## Generation

```toml
[generation]
backend = "mock"
output_format = "wav"
inference_steps = 27
guidance_scale = 15.0
batch_size = 1
chunk_seconds = 30
checkpoint_path = ""
```

Backends:

- `mock`: deterministic local test generator.
- `ace-step`: embedded ACE-Step Python pipeline.
- `ace-step-http`: local or remote ACE-Step HTTP server.
- `runpod`: RunPod-style remote adapter over a configured ACE-Step HTTP endpoint.

`chunk_seconds` controls long-session chunk size. Chunks are checked for continuity and stitched with crossfades.
`batch_size` is passed to ACE-Step backends.

## Playback

```toml
[playback]
volume = 0.8
fade_seconds = 1.5
```

Playback uses `sounddevice` when installed and falls back to a null player in unsupported environments.
`fade_seconds` applies a fade to playback audio without changing the saved WAV.

## ACE-Step HTTP

```toml
[ace_step_http]
base_url = "http://127.0.0.1:8001"
api_key = ""
timeout_seconds = 1800.0
```

The HTTP adapter submits `/release_task`, polls `/query_result`, and downloads `/v1/audio?path=...`.
`timeout_seconds` is the total remote task deadline as well as the HTTP client timeout.

## RunPod

```toml
[runpod]
api_key = ""
gpu_type = "NVIDIA GeForce RTX 4090"
template_id = ""
volume_id = ""
auto_destroy = true
```

RunPod support is optional and dependency-light. The current adapter selects a remote ACE-Step endpoint from config; pod lifecycle automation is an extension point.

## Environment Overrides

- `LOFI_BACKEND`: overrides `generation.backend`.
- `ACESTEP_CHECKPOINT_PATH`: overrides `generation.checkpoint_path`.
