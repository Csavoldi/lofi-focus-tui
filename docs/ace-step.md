# ACE-Step

ACE-Step support is optional. Mock mode remains the default for development and CI.

## ACE-Step-1.5 HTTP Mode

The required release UAT path is ACE-Step-1.5 running as a local REST API. Keep it in a
separate checkout so model dependencies, Python version, and GPU setup do not leak into
normal `lofi-focus-tui` development.

ACE-Step-1.5 expects Python 3.11-3.12. CUDA is recommended, and the upstream project also
documents MPS, ROCm, Intel XPU, and CPU modes. Models download automatically on first run.

Start the API:

```bash
git clone https://github.com/ace-step/ACE-Step-1.5.git
cd ACE-Step-1.5
uv sync
uv run acestep-api
```

Windows launch-script alternative:

```powershell
.\start_api_server.bat
```

Expected API URL:

```text
http://127.0.0.1:8001
```

Verify directly:

```bash
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8001/v1/models
```

Configure this app:

```toml
[generation]
backend = "ace-step-http"
chunk_seconds = 300
inference_steps = 8
batch_size = 1

[ace_step_http]
base_url = "http://127.0.0.1:8001"
api_key = ""
timeout_seconds = 1800.0
```

Run the opt-in live gate:

```bash
LOFI_UAT_ACE_STEP_BASE_URL=http://127.0.0.1:8001 pytest tests/test_live_ace_step_http.py -v
```

PowerShell:

```powershell
$env:LOFI_UAT_ACE_STEP_BASE_URL = "http://127.0.0.1:8001"
pytest tests/test_live_ace_step_http.py -v
```

The test submits a real ACE-Step-1.5 HTTP task, polls `/query_result`, downloads the
returned `/v1/audio?path=...` WAV, validates that it is non-silent and unclipped, and
writes evidence under `.uat/ace-step-http/`.

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

Embedded mode is not the required ACE-Step-1.5 release gate. Use HTTP mode for UAT unless
the embedded adapter has been separately validated against ACE-Step-1.5.

## Generic HTTP Mode

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
