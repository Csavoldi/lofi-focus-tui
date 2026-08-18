# Single-Process Lofi App Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the Lofi TUI-to-backend HTTP boundary so `lofi` constructs and owns the session manager in one process.

**Architecture:** Keep `SessionManager` and its existing background generation worker as the internal application runtime. Move dependency construction into a small runtime module, inject one `AppConfig` and one manager into `LofiFocusApp`, call manager methods directly, and delete the Lofi FastAPI/client process path. ACE-Step HTTP remains an external model service when that adapter is selected.

**Tech Stack:** Python 3.10+, Textual, Pydantic, HTTPX for ACE-Step HTTP, pytest/pytest-asyncio, Ruff.

---

## File map

- Create `src/lofi_focus_tui/runtime.py` for model, playback, and `SessionManager` construction.
- Modify `src/lofi_focus_tui/cli.py` to load config once, build the manager, and launch the TUI.
- Modify `src/lofi_focus_tui/tui/app.py` to use direct manager calls, shared config, nonblocking export, and shutdown cleanup.
- Modify `src/lofi_focus_tui/backend/session_manager.py` for lifecycle ownership, late-result guards, and lock-free file copying.
- Modify `src/lofi_focus_tui/generation/http_ace_step.py` to close its owned HTTPX client.
- Modify `src/lofi_focus_tui/config.py` and `config.example.toml` to remove active Lofi server configuration while accepting legacy `[server]` TOML.
- Modify `src/lofi_focus_tui/diagnostics.py` to remove port probing.
- Modify `pyproject.toml` to remove FastAPI/Uvicorn and the `lofi-backend` entry point while retaining HTTPX.
- Delete `src/lofi_focus_tui/backend/api.py` and `src/lofi_focus_tui/tui/backend_client.py`.
- Replace or delete `tests/test_backend_api.py` and `tests/test_backend_client.py` with direct runtime/TUI coverage.
- Modify `tests/test_session_manager.py`, `tests/test_http_ace_step.py`, `tests/test_tui_app.py`, `tests/test_config.py`, and `tests/test_diagnostics.py`.
- Add `tests/test_runtime.py`.
- Update `README.md`, `docs/usage.md`, `docs/configuration.md`, `docs/ace-step.md`, and `docs/user-acceptance-testing.md`.

## Chunk 1: Runtime construction and direct TUI seam

### Task 1: Add a tested runtime builder

**Files:**
- Create: `tests/test_runtime.py`
- Create: `src/lofi_focus_tui/runtime.py`
- Modify: `src/lofi_focus_tui/cli.py`
- Test: `tests/test_backend_api.py` construction assertions to migrate into `tests/test_runtime.py`

- [ ] **Step 1: Write the failing runtime-builder tests.**

  Test that a mock `AppConfig` produces a `SessionManager` with the configured model,
  generation defaults, chunk cap, playback settings, output manager, and history store.
  Test that HTTP, embedded, and RunPod backend selection still returns the same adapter
  classes and configured values as the current `_build_model` path.

- [ ] **Step 2: Run the focused tests and confirm the expected failure.**

  Run: `PYTHONPATH=src pytest tests/test_runtime.py -q`

  Expected: collection or import failure because `lofi_focus_tui.runtime` does not yet
  exist.

- [ ] **Step 3: Move construction helpers into `runtime.py`.**

  Implement `build_model(config)`, `build_playback(config)`, and
  `build_session_manager(config)` by moving the existing construction behavior from
  `backend/api.py`. Keep `httpx`-backed ACE-Step construction unchanged.

- [ ] **Step 4: Make the CLI own one config and one manager.**

  Update `cli.main()` to call `load_config()` once, build the manager, instantiate
  `LofiFocusApp(session_manager=manager, config=config)`, and run it. Do not reload config
  inside the app. Keep shutdown cleanup in the app lifecycle task for the next task.

- [ ] **Step 5: Run the focused tests and confirm they pass.**

  Run: `PYTHONPATH=src pytest tests/test_runtime.py tests/test_backend_api.py -q`

  Expected: runtime tests pass; remaining API tests may still fail until the HTTP boundary
  is removed in Chunk 4.

- [ ] **Step 6: Commit the runtime seam.**

  ```bash
  git add src/lofi_focus_tui/runtime.py src/lofi_focus_tui/cli.py tests/test_runtime.py
  git commit -m "refactor: build the app runtime in process"
  ```

### Task 2: Replace the TUI client with direct manager calls

**Files:**
- Modify: `src/lofi_focus_tui/tui/app.py`
- Modify: `tests/test_tui_app.py`

- [ ] **Step 1: Write failing direct-manager TUI tests.**

  Replace the fake HTTP client with a synchronous fake manager exposing `health`,
  `start_session`, pause/resume/stop, volume, seek, restart, and export methods. Test that
  mount reads manager status, session requests preserve prompt/vocal mode, controls call
  the manager directly, and the configured theme comes from the same `AppConfig` passed to
  the app.

- [ ] **Step 2: Run the focused tests and confirm they fail for the old seam.**

  Run: `PYTHONPATH=src pytest tests/test_tui_app.py -q`

  Expected: failures because the app still expects `BackendClient` and awaits HTTP-client
  methods.

- [ ] **Step 3: Inject `SessionManager` and shared `AppConfig`.**

  Change the constructor to accept the manager and config. Replace every
  `backend_client` call with its direct manager equivalent, keeping the existing async
  action methods for Textual compatibility. Remove `load_config()` from the app.

- [ ] **Step 4: Move export copying off the event loop.**

  In `ExportScreen.on_input_submitted`, call `await asyncio.to_thread(
  self.app.session_manager.export_current, event.value)`. Preserve the current error text
  and success notification behavior. The manager implementation will release its locks
  before copying in Task 3.

- [ ] **Step 5: Run the TUI tests and commit.**

  Run: `PYTHONPATH=src pytest tests/test_tui_app.py -q`

  Expected: all TUI tests pass, including prompt focus, vocal mode, theme selection, and
  direct manager call assertions.

  ```bash
  git add src/lofi_focus_tui/tui/app.py tests/test_tui_app.py
  git commit -m "refactor: connect the TUI to the local session manager"
  ```

## Chunk 2: Manager lifecycle and safe in-process shutdown

### Task 3: Add cooperative manager shutdown and late-result guards

**Files:**
- Modify: `src/lofi_focus_tui/backend/session_manager.py`
- Modify: `src/lofi_focus_tui/generation/http_ace_step.py`
- Modify: `tests/test_session_manager.py`
- Modify: `tests/test_http_ace_step.py`

- [ ] **Step 1: Write failing lifecycle tests.**

  Add tests for:

  - `shutdown()` marks the manager closed, cancels the active task, stops playback, and
    returns after a fixed two-second wait at most;
  - repeated shutdown calls are no-ops;
  - new sessions and controls raise `RuntimeError("session manager is closed")`;
  - `health()` returns idle/`closed` after shutdown;
  - a blocked worker that completes after shutdown cannot write audio/metadata, update
    status, append history, or restart playback;
  - cleanup occurs only after the worker stops;
  - `AceStepHttpAdapter.close()` closes its owned HTTPX client exactly once.

- [ ] **Step 2: Run the focused tests and confirm they fail.**

  Run: `PYTHONPATH=src pytest tests/test_session_manager.py tests/test_http_ace_step.py -q`

  Expected: missing `shutdown`/`close` behavior and late-result artifact failures.

- [ ] **Step 3: Implement the closed state and cooperative shutdown.**

  Add a lock-protected closed flag, a two-second active-future wait, cancellation of the
  active `GenerationTask` and pending futures, and idempotent cleanup. Reject new manager
  operations after close with the exact runtime error. Keep a running model alive until
  its worker exits; never close an adapter while that worker can still use it. Close the
  adapter and executor in the worker finalization path when delayed cleanup is required.

- [ ] **Step 4: Guard every post-close generation commit.**

  Check the closed/active state before `OutputManager` writes audio or metadata and again
  before history, playback, task output, and status updates. A late result must be dropped
  without creating output artifacts.

- [ ] **Step 5: Make the HTTP adapter own and close its client.**

  Add an idempotent `close()` method to `AceStepHttpAdapter` that closes its owned client.
  Preserve injected test-client ownership by not closing externally supplied clients unless
  the adapter owns them. `RunPodAceStepAdapter` inherits the behavior.

- [ ] **Step 6: Run focused lifecycle tests and commit.**

  Run: `PYTHONPATH=src pytest tests/test_session_manager.py tests/test_http_ace_step.py -q`

  Expected: all focused tests pass.

  ```bash
  git add src/lofi_focus_tui/backend/session_manager.py src/lofi_focus_tui/generation/http_ace_step.py tests/test_session_manager.py tests/test_http_ace_step.py
  git commit -m "feat: add safe in-process session shutdown"
  ```

### Task 4: Release manager locks before export I/O

**Files:**
- Modify: `src/lofi_focus_tui/backend/session_manager.py`
- Modify: `tests/test_session_manager.py`

- [ ] **Step 1: Write a failing lock-release test.**

  Use a slow output manager whose copy blocks on an event. Start `export_current()` in a
  worker thread, then assert a concurrent `health()` or playback operation acquires the
  manager locks before releasing the copy event.

- [ ] **Step 2: Run the focused test and confirm it fails.**

  Run: `PYTHONPATH=src pytest tests/test_session_manager.py -k export -q`

  Expected: the concurrent operation remains blocked because the current implementation
  holds `_playback_lock` during file copying.

- [ ] **Step 3: Capture state under lock and copy outside it.**

  Read the completed output path while holding the necessary locks, release all locks, and
  call `OutputManager.export_session()` afterward.

- [ ] **Step 4: Run focused export tests and commit.**

  Run: `PYTHONPATH=src pytest tests/test_session_manager.py -k export -q`

  Expected: export success, missing-session errors, and lock-release tests pass.

  ```bash
  git add src/lofi_focus_tui/backend/session_manager.py tests/test_session_manager.py
  git commit -m "fix: keep export I/O outside manager locks"
  ```

## Chunk 3: Configuration and diagnostics migration

### Task 5: Remove active Lofi server configuration

**Files:**
- Modify: `src/lofi_focus_tui/config.py`
- Modify: `config.example.toml`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Write failing config migration tests.**

  Assert the default `AppConfig` has no active `server` field, a TOML file containing a
  legacy `[server]` section still loads, and generation/ACE-Step/theme settings remain
  intact. Assert `httpx` remains a declared runtime dependency in `pyproject.toml`.

- [ ] **Step 2: Run the focused tests and confirm they fail.**

  Run: `PYTHONPATH=src pytest tests/test_config.py -q`

  Expected: current tests still expose `config.server` and the migration assertion fails.

- [ ] **Step 3: Remove `ServerConfig` and the `AppConfig.server` field.**

  Keep Pydantic’s default ignored-extra behavior so old `[server]` sections are accepted
  but not used. Update default assertions and add the explicit legacy migration test.

- [ ] **Step 4: Remove the `[server]` block from the example config.**

  Keep `[generation]`, `[playback]`, `[ace_step_http]`, and `[runpod]` unchanged.

- [ ] **Step 5: Run config tests and commit.**

  Run: `PYTHONPATH=src pytest tests/test_config.py -q`

  Expected: all config tests pass.

  ```bash
  git add src/lofi_focus_tui/config.py config.example.toml tests/test_config.py
  git commit -m "refactor: remove local server configuration"
  ```

### Task 6: Simplify diagnostics

**Files:**
- Modify: `src/lofi_focus_tui/diagnostics.py`
- Modify: `tests/test_diagnostics.py`

- [ ] **Step 1: Write failing diagnostics tests.**

  Remove the port-probe fixture and assert diagnostics reports Python, config, model
  optional dependency, sounddevice, cache, outputs, and device checks without a `backend`
  port check.

- [ ] **Step 2: Run the focused tests and confirm they fail.**

  Run: `PYTHONPATH=src pytest tests/test_diagnostics.py -q`

  Expected: current tests still require the removed backend check.

- [ ] **Step 3: Remove socket probing and update diagnostics output.**

  Delete `PortProbe`, `_probe_port`, socket imports, and the port status block. Keep
  configuration loading and all local filesystem/device checks.

- [ ] **Step 4: Run diagnostics tests and commit.**

  Run: `PYTHONPATH=src pytest tests/test_diagnostics.py -q`

  Expected: all diagnostics tests pass.

  ```bash
  git add src/lofi_focus_tui/diagnostics.py tests/test_diagnostics.py
  git commit -m "refactor: make diagnostics process-local"
  ```

## Chunk 4: Remove the HTTP boundary and update public workflow

### Task 7: Delete the Lofi API/client and update packaging

**Files:**
- Delete: `src/lofi_focus_tui/backend/api.py`
- Delete: `src/lofi_focus_tui/tui/backend_client.py`
- Delete or replace: `tests/test_backend_api.py`
- Delete or replace: `tests/test_backend_client.py`
- Modify: `pyproject.toml`
- Modify: `src/lofi_focus_tui/cli.py`

- [ ] **Step 1: Migrate any remaining construction tests to `tests/test_runtime.py`.**

  Preserve model-selection, playback-selection, and manager-construction coverage without
  importing FastAPI, ASGI transports, or the removed client.

- [ ] **Step 2: Remove obsolete package entry points and dependencies.**

  Delete the `lofi-backend` script and remove `fastapi` and `uvicorn` from dependencies.
  Keep `httpx` for `AceStepHttpAdapter` and keep all other runtime dependencies.

- [ ] **Step 3: Delete the API and client modules and clean imports.**

  Use `rg -n 'create_app|BackendClient|lofi-backend|fastapi|uvicorn|ServerConfig' src tests`
  and remove every remaining Lofi HTTP-boundary import or reference. Do not remove the
  ACE-Step HTTP adapter or its HTTPX calls.

- [ ] **Step 4: Run the package/import tests and commit.**

  Run: `PYTHONPATH=src pytest tests/test_runtime.py tests/test_tui_app.py tests/test_config.py tests/test_diagnostics.py -q`

  Expected: all direct-runtime tests pass and no removed entry point/import remains.

  ```bash
  git add pyproject.toml src tests
  git commit -m "refactor: remove the local Lofi HTTP boundary"
  ```

### Task 8: Update user-facing documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/usage.md`
- Modify: `docs/configuration.md`
- Modify: `docs/ace-step.md`
- Modify: `docs/user-acceptance-testing.md`

- [ ] **Step 1: Write documentation assertions/search checks.**

  Use repository searches to identify every current instruction that starts `lofi-backend`
  or describes port `8765`. The updated current-user docs must show `LOFI_BACKEND=mock lofi`
  for mock mode and only `lofi` after starting the separate ACE-Step service.

- [ ] **Step 2: Update the one-process instructions.**

  Remove the second Lofi terminal from setup, replace backend startup commands, remove
  `[server]` configuration examples, and clarify that port `8001` belongs only to an
  optional ACE-Step HTTP service.

- [ ] **Step 3: Verify documentation scope.**

  Run:

  ```bash
  rg -n 'lofi-backend|port `?8765|\[server\]' README.md docs/usage.md docs/configuration.md docs/ace-step.md docs/user-acceptance-testing.md
  ```

  Expected: no obsolete Lofi backend instructions remain; ACE-Step port `8001` references
  remain where relevant.

- [ ] **Step 4: Commit the documentation migration.**

  ```bash
  git add README.md docs/usage.md docs/configuration.md docs/ace-step.md docs/user-acceptance-testing.md
  git commit -m "docs: document the single-process app workflow"
  ```

## Chunk 5: Full verification and handoff

### Task 9: Run regression checks

**Files:**
- Verify all changed files; no new production changes are expected in this task.

- [ ] **Step 1: Run the full test suite.**

  Run: `PYTHONPATH=src pytest -q`

  Expected: all tests pass, including direct TUI/runtime, prompt engine, generation,
  lifecycle, export, config migration, and diagnostics coverage.

- [ ] **Step 2: Run lint and whitespace checks.**

  Run: `ruff check src tests`

  Expected: `All checks passed!`

  Run: `git diff --check origin/dev..HEAD`

  Expected: no output and exit code 0.

- [ ] **Step 3: Verify the removed boundary and command surface.**

  Run: `rg -n 'lofi-backend|create_app|BackendClient|ServerConfig|127\.0\.0\.1:8765' src tests README.md docs pyproject.toml`

  Expected: no active Lofi HTTP-boundary references. ACE-Step HTTP references and
  `httpx` remain.

- [ ] **Step 4: Run the manual smoke test.**

  In a clean environment, run only:

  ```bash
  LOFI_BACKEND=mock lofi
  ```

  Confirm the TUI starts without a second process, `i` focuses the prompt editor, `v`
  toggles vocal mode, `s` starts generation, pause/resume/stop work, export remains
  usable, and quitting during generation follows the documented cooperative-shutdown
  behavior.

- [ ] **Step 5: Inspect final scope and hand off.**

  Run:

  ```bash
  git status --short
  git diff --name-only origin/dev..HEAD
  ```

  Expected: the worktree is clean and only the planned runtime, manager, adapter, config,
  diagnostics, packaging, tests, and documentation files changed.
