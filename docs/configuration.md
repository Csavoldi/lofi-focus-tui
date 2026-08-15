# Configuration

`lofi-focus-tui` loads configuration from `config.toml` in the current directory, then from `~/.config/lofi-focus-tui/config.toml`. Missing files use defaults.

See `config.example.toml` for a complete starting point.

focus and music preset are separate API fields.
API requests carry separate focus and music preset fields: `focus` and `preset`.
omitted focus and null focus follow the same normalization path.
legacy focus-valued presets map to matching focus plus classic_lofi.
This migration applies only when focus is omitted or null.
valid music preset values default the separate focus field to deep_work.
This defaulting applies only when focus is omitted or null.
An explicit valid focus is preserved with a valid music preset.
An explicit non-null focus plus a legacy focus-valued preset is rejected.
no TOML keys change.

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
chunk_seconds = 600
checkpoint_path = ""
```

Backends:

- `mock`: deterministic local test generator.
- `ace-step`: embedded ACE-Step Python pipeline.
- `ace-step-http`: local or remote ACE-Step HTTP server.
- `runpod`: RunPod-style remote adapter over a configured ACE-Step HTTP endpoint.

`chunk_seconds` is the maximum chunk size and defaults to 600 seconds (10 minutes). The
session policy uses one 300-second chunk for a 5-minute request and chunks up to 600 seconds
for longer requests; the final chunk can be shorter. Set a lower value between 10 and 600
seconds to cap chunk size for a constrained machine.

Each generated chunk is checked for loudness, clipping, silence, boundary clicks, and
spectral changes. Ordinary warnings become continuation notes for the following chunk.
Severe boundaries retry once with corrective prompt constraints. Accepted chunks are joined
with the existing fixed crossfade.
`batch_size` is passed to ACE-Step backends.

## Playback

```toml
[playback]
volume = 0.8
fade_seconds = 1.5
```

Playback uses `sounddevice` when installed and falls back to a null player in unsupported environments.
`fade_seconds` applies a fade to playback audio without changing the saved WAV.

## ACE-Step-1.5 HTTP

```toml
[ace_step_http]
base_url = "http://127.0.0.1:8001"
api_key = ""
timeout_seconds = 1800.0
```

The HTTP adapter targets the ACE-Step-1.5 REST API shape: submit `/release_task`,
poll `/query_result` with `task_id_list`, and download the returned `/v1/audio?path=...`
WAV URL.
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
