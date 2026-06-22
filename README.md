# Lofi Focus TUI

Session-first terminal UI for local AI-generated focus music.

![TUI preview](docs/tui-preview.svg)

The TUI instructs a local backend. The backend owns planning, ACE-Step integration,
device selection, continuity checks, playback state, and cache.

Initial development uses a deterministic mock generator before enabling ACE-Step.

## Development

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
pytest -v
```

## Quality Checks

```bash
ruff check src tests
pytest -v
```

## Run

Mock mode is the default and does not require ACE-Step.

Start the backend:

```bash
lofi-backend
```

Start the terminal UI in a second terminal:

```bash
lofi
```

With the backend running, press `s` in the TUI to start a mock deep-work session.
The TUI will update from `idle` to `playing` after the backend accepts the session.

Run diagnostics:

```bash
lofi-doctor
```

Saved sessions are written under `~/.cache/lofi-focus-tui/outputs`, with history at
`~/.cache/lofi-focus-tui/history.jsonl`.

More detail:

- [Usage](docs/usage.md)
- [Configuration](docs/configuration.md)
- [ACE-Step modes](docs/ace-step.md)
- [User acceptance testing](docs/user-acceptance-testing.md)

## ACE-Step-1.5 HTTP Smoke Test

ACE-Step is optional during normal development. For release UAT, run the ACE-Step-1.5
REST API locally and point this app at it over HTTP.

```bash
git clone https://github.com/ace-step/ACE-Step-1.5.git
cd ACE-Step-1.5
uv sync
uv run acestep-api
```

The API should listen on `http://127.0.0.1:8001`.

In this repository, run the live UAT gate from a second terminal:

```bash
LOFI_UAT_ACE_STEP_BASE_URL=http://127.0.0.1:8001 pytest tests/test_live_ace_step_http.py -v
```

PowerShell:

```powershell
$env:LOFI_UAT_ACE_STEP_BASE_URL = "http://127.0.0.1:8001"
pytest tests/test_live_ace_step_http.py -v
```

Use the fake-pipeline tests for normal development. Run real ACE-Step generation only on a
prepared model-inference machine. Real ACE-Step-1.5 HTTP generation must pass before release.
