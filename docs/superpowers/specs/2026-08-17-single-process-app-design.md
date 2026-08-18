# Single-Process Lofi App Design

## Goal

Run `lofi-focus-tui` as one user-facing application process. The TUI should call the
session manager directly instead of requiring a separately launched Lofi HTTP backend.

## Current problem

The application currently has two Lofi processes:

```text
lofi TUI -> HTTP localhost:8765 -> lofi-backend -> SessionManager -> generator
```

This makes a local app feel like a distributed system. Users must start and keep two
commands running, and an unavailable local port is reported as a backend failure even
when the application itself could own the session manager.

## Approved architecture

`lofi` will construct the configured model adapter, playback manager, output manager,
history store, and `SessionManager`, then inject that manager into `LofiFocusApp`:

```text
lofi process
├── Textual TUI
├── SessionManager
├── background generation worker
├── playback, history, and export
└── configured model adapter
```

`SessionManager` retains its existing single-worker executor. Generation remains
asynchronous from the TUI's perspective; removing HTTP does not move model inference
onto the UI event loop.

The existing `backend/session_manager.py` and task machinery remain internal
implementation modules. They are not separate user-facing entities.

ACE-Step HTTP remains an optional external model service when `generation.backend` is
`ace-step-http`. This change removes the Lofi TUI/backend split; embedding ACE-Step
itself is a separate concern and is not part of this work.

## Runtime flow

1. `lofi_focus_tui.cli.main()` loads the application config exactly once.
2. A runtime builder creates the configured model adapter and `SessionManager` from that
   config.
3. `LofiFocusApp(session_manager=manager, config=config)` starts the Textual application.
   The TUI reuses this config for theme and display settings instead of loading a second
   copy from disk.
4. On mount and on its existing refresh interval, the TUI reads `manager.health()`.
5. Start, pause, resume, stop, volume, seek, restart, and export actions call the
   corresponding manager methods directly.
6. `SessionManager.start_session()` submits generation to its existing worker and
   immediately returns a generating status.
7. Existing status, playback, output, history, prompt, and vocal-mode behavior remains
   unchanged.

When the app unmounts or quits, it calls an idempotent manager shutdown method. Shutdown
marks the manager closed so new sessions are rejected, requests cooperative cancellation
through the existing task mechanism and stops playback. It waits for the active future for
a fixed short timeout, then cancels pending futures. If an adapter does not honor
cooperative cancellation, the app may remain alive until that current generation returns;
Python cannot safely hard-kill a model thread inside the single process. The manager must
not close a model adapter while its worker is still using it. Cleanup runs after worker
termination, then closes the adapter and executor. Repeated shutdown calls are no-ops, and
new sessions and controls raise `RuntimeError("session manager is closed")`. `health()`
returns an idle status with message `closed`, and export raises the same runtime error.
`shutdown()` returns after the fixed two-second wait even if a worker is still running;
the worker's finalization path performs delayed cleanup. Every post-close completion is
discarded before it can update status, save a completed session, or restart playback.
Repeated shutdown calls are no-ops. A quit-during-generation test must verify the closed
state, cancellation request, playback stop, safe delayed cleanup, discarded late results,
and post-close rejection. The ACE-Step HTTP adapter's `close()` closes its owned HTTPX
client; adapters without resources may use a no-op cleanup path.

## Code changes

### TUI integration

Replace the HTTP `BackendClient` dependency in `LofiFocusApp` with `SessionManager`.
The TUI keeps its current async action methods, but their bodies call fast synchronous
manager methods directly. The manager's worker thread continues to handle generation.

The export screen will preserve its current user-facing error behavior by catching
manager export errors rather than HTTP errors. Because `export_current()` copies files
synchronously, the TUI will invoke it with `asyncio.to_thread` so export I/O does not block
the Textual event loop. `SessionManager.export_current()` will capture the completed output
path while holding its locks, release those locks, and perform file copying afterward. A
test will use a deliberately slow export manager and verify both that the handler yields
while the copy is in progress and that a concurrent manager operation can acquire the
released lock.

### Runtime construction

Move model, playback, and session-manager construction into a small application runtime
builder that can be used by the CLI and tests without importing FastAPI or starting a
server. The builder will preserve the current backend selection and configuration
behavior for mock, embedded ACE-Step, ACE-Step HTTP, and RunPod adapters.

`AppConfig` is the single startup configuration object. It is passed to both the runtime
builder and `LofiFocusApp`; neither layer reloads the config file.

### Remove the Lofi HTTP boundary

Remove the Lofi FastAPI application and HTTP client path from the normal package:

- remove the `lofi-backend` console script;
- remove `backend/api.py` once its construction helpers are moved;
- remove `tui/backend_client.py`;
- remove FastAPI and Uvicorn runtime dependencies;
- retain HTTPX because the ACE-Step HTTP adapter still uses it for the external model
  service;
- remove API/client tests and replace them with direct manager/TUI integration coverage.

The `backend` package name may remain for the internal session manager to avoid an
unrelated package-wide rename.

### Configuration and diagnostics

Remove the Lofi `[server]` host/port configuration from the active model. Existing TOML
files containing those keys should remain loadable because unknown legacy keys are
ignored by the current Pydantic configuration model.

`lofi-doctor` will stop probing port `8765`. It will continue checking Python, config,
optional model/playback modules, writable cache/output directories, and playback device
availability. ACE-Step's own endpoint remains configured under `[ace_step_http]` and is
not treated as the Lofi app server.

### Documentation and commands

Update README, usage, configuration, ACE-Step, and user-acceptance instructions so the
normal local workflow is:

```bash
LOFI_BACKEND=mock lofi
```

For real HTTP generation, users still start the separate ACE-Step-1.5 service, then run
only `lofi` for the Lofi application. The installed commands are `lofi` and
`lofi-doctor`; `lofi-backend` is removed.

Update `config.example.toml` so it no longer documents the removed Lofi `[server]` section.
Legacy TOML files that still contain `[server]` must remain loadable, but the active config
model must not use those values.

## Error behavior

- Model construction errors continue to fail during application startup with the
  existing configuration/model error.
- Generation failures continue to be represented by `BackendStatus` error state from
  `SessionManager`.
- TUI actions receive manager status values directly; there is no synthetic
  "backend unavailable" status for a stopped local process.
- Export errors continue to be displayed in the export dialog.
- Long-running generation remains cancellable through the existing manager controls.

## Testing

Add or update tests to prove:

- the runtime builder selects the same model adapters and settings as before;
- one shared `AppConfig` reaches runtime construction and TUI theme/display setup;
- `LofiFocusApp` calls a supplied manager directly for status and controls;
- generation remains asynchronous through the manager's worker;
- quitting during generation shuts down the manager and playback cleanly;
- prompt and vocal-mode fields reach the manager unchanged;
- export success and failure behavior remains intact;
- export file I/O runs off the TUI event loop;
- the package exposes `lofi` and `lofi-doctor`, but no `lofi-backend` command;
- diagnostics no longer depends on port `8765`;
- a legacy TOML file containing `[server]` still loads while no active server config is used;
- `httpx` remains installed for ACE-Step HTTP mode;
- the full existing suite and Ruff checks pass.

The primary manual smoke test becomes one process in mock mode:

```bash
LOFI_BACKEND=mock lofi
```

## Non-goals

- Do not embed or rewrite ACE-Step-1.5 as part of this change.
- Do not redesign `SessionManager` generation, playback, chunking, or prompt logic.
- Do not preserve a hidden localhost Lofi server; direct manager calls are the chosen
  architecture.
- Do not add a new public service API.
