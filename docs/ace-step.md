# ACE-Step

ACE-Step support is optional. Mock mode remains the default for development and CI.

## Embedded Mode

Install the optional embedded dependency on a machine prepared for model inference:

```bash
python -m pip install -e ".[ace-step]"
```

Configure:

```toml
[generation]
backend = "ace-step"
checkpoint_path = "/path/to/checkpoint"
```

The backend loads ACE-Step lazily when generation starts.

## HTTP Mode

Run an ACE-Step-compatible HTTP service, then configure:

```toml
[generation]
backend = "ace-step-http"

[ace_step_http]
base_url = "http://127.0.0.1:8001"
api_key = ""
timeout_seconds = 1800.0
```

The adapter submits `/release_task`, polls `/query_result`, and downloads WAV audio from `/v1/audio`.
Polling stops when the configured timeout is reached or when the session is cancelled.

## RunPod Mode

Install the optional dependency if you are managing RunPod resources from this environment:

```bash
python -m pip install -e ".[runpod]"
```

Configure:

```toml
[generation]
backend = "runpod"

[ace_step_http]
base_url = "https://your-runpod-endpoint"

[runpod]
api_key = ""
gpu_type = "NVIDIA GeForce RTX 4090"
template_id = ""
volume_id = ""
auto_destroy = true
```

The first implementation keeps RunPod optional and exposes a selectable remote adapter. Pod create/destroy lifecycle automation can be layered on top without changing the TUI/backend contract.

## Diagnostics

Run:

```bash
lofi-doctor
```

Use warnings about missing optional packages or unavailable backend ports to decide which extra to install or which service to start.

## Acceptance

Real ACE-Step generation is required before release. Follow
[`docs/user-acceptance-testing.md`](user-acceptance-testing.md) for the short-generation,
chunked-generation, and error UX gates.
