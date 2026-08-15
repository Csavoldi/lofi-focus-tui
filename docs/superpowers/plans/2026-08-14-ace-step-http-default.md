# ACE-Step HTTP Default Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `ace-step-http` the application’s default generation backend while preserving explicit backend overrides and documenting the normal ACE-Step REST setup.

**Architecture:** Change the single Pydantic default in `config.py`; existing environment and TOML loading already provide the required precedence and validation. Add regression tests around defaulting and overrides, then update the configuration and UAT guidance without touching the user’s uncommitted `config.example.toml` edits.

**Tech Stack:** Python 3.11+, Pydantic, pytest, Markdown/TOML documentation.

---

## Chunk 1: Configuration default and regression coverage

**Files:**
- Modify: `tests/test_config.py`
- Modify: `tests/test_backend_api.py`
- Modify: `tests/test_backend_client.py`
- Modify: `src/lofi_focus_tui/config.py`

- [ ] **Step 1: Write the failing tests**

  Update `test_default_config_loads_without_file` to expect `ace-step-http` and
  the default URL `http://127.0.0.1:8001`. Add
  `test_config_without_backend_uses_http_default` with an existing TOML file
  containing only `[server]`, asserting the HTTP backend default. Update
  `test_env_overrides_backend` so TOML selects `ace-step` while
  `LOFI_BACKEND=mock` wins. Add separate tests for an explicitly unset and an
  empty `LOFI_BACKEND`, both asserting that a TOML `ace-step` value is retained.
  Update existing tests that intentionally exercise mock mode so they select
  `mock` explicitly rather than relying on `AppConfig()` defaults.

- [ ] **Step 2: Run the focused tests to verify the default test fails**

  Run: `PYTHONPATH=src pytest -q tests/test_config.py`

  Expected: the no-file default and no-backend TOML backend assertions fail
  because the implementation still defaults to `mock`; the default URL,
  explicit environment override, unset environment, and empty environment
  assertions remain green.

- [ ] **Step 3: Change the minimal implementation**

  Change only `GenerationConfig.backend`’s default literal from `"mock"` to
  `"ace-step-http"`. Keep the existing truthy environment override behavior,
  which already leaves TOML/default values intact for an unset or empty
  `LOFI_BACKEND`.

- [ ] **Step 4: Run the focused tests to verify they pass**

  Run: `PYTHONPATH=src pytest -q tests/test_config.py`

  Expected: all configuration tests pass.

- [ ] **Step 5: Commit the code and tests**

  ```bash
  git add src/lofi_focus_tui/config.py tests/test_config.py
  git commit -m "feat: default to ace-step-http backend"
  ```

## Chunk 2: User-facing setup documentation

**Files:**
- Modify: `docs/configuration.md`
- Modify: `docs/user-acceptance-testing.md`
- Modify: `README.md`
- Modify: `docs/usage.md`
- Modify: `docs/ace-step.md`

- [ ] **Step 1: Update the normal configuration example**

  Set the documented generation backend to `ace-step-http`, state that it is
  the default, and point users to the local REST endpoint at
  `http://127.0.0.1:8001`. Keep `mock` documented as an explicit development
  fallback and align all README and ACE-Step/usage guidance with that default.

- [ ] **Step 2: Clarify the fresh-install UAT path**

  State that the default path requires the ACE-Step REST server and that the
  mock workflow is the explicit offline alternative. Update the mock gate so
  it requires `generation.backend = "mock"` or `LOFI_BACKEND=mock`; do not say
  that removing local config selects mock. Keep the existing real HTTP gates
  and their commands intact.

- [ ] **Step 3: Check documentation consistency**

  Run: `rg -n 'backend = "mock"|backend = "ace-step-http"|127\.0\.0\.1:8001' docs/configuration.md docs/user-acceptance-testing.md README.md docs/usage.md docs/ace-step.md`

  Expected: normal setup/configuration text uses `ace-step-http`; mock appears
  only in explicit developer/mock workflow guidance.

- [ ] **Step 4: Commit the documentation**

  ```bash
  git add docs/configuration.md docs/user-acceptance-testing.md
  git commit -m "docs: document ace-step-http default"
  ```

## Chunk 3: Full verification

**Files:**
- No additional files.

- [ ] **Step 1: Run the full test suite**

  Run: `PYTHONPATH=src pytest -q`

  Expected: all tests pass, with only the repository’s existing skips.

- [ ] **Step 2: Run lint and whitespace checks**

  Run: `ruff check src tests` and `git diff --check`

  Expected: both commands succeed.

- [ ] **Step 3: Confirm user-owned changes remain untouched**

  Run: `git status --short`

  Expected: the pre-existing `config.example.toml` modification and `.superpowers/`
  directory remain present. Run `git diff --name-only de27d35..HEAD` after the
  implementation commits; expected output contains only the intended source,
  test, and documentation files listed in Chunks 1 and 2, and does not contain
  `config.example.toml` or `.superpowers/`.
