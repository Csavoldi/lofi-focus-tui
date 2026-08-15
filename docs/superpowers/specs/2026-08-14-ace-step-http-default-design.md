# ACE-Step HTTP Default

## Status

Approved direction for implementation on the `dev` branch.

## Goal

Make the configured default generation backend `ace-step-http` so a fresh install
uses the user’s running ACE-Step REST server instead of the placeholder mock tone.

## Behavior

- `GenerationConfig.backend` defaults to `"ace-step-http"`.
- The default REST base URL remains `http://127.0.0.1:8001`.
- Backend selection precedence is `LOFI_BACKEND` > TOML `generation.backend` >
  the application default. An unset or empty `LOFI_BACKEND` does not override
  TOML or the default.
- An explicit TOML `generation.backend` value is preserved, including when an
  existing config file omits the backend field.
- `LOFI_BACKEND` can explicitly select `mock`, `ace-step`, `ace-step-http`, or
  `runpod`.
- Mock mode remains available for offline development; it is no longer the default.
- The local `ace-step` backend remains available when explicitly selected.
- No ACE-Step server API or generation payload changes are needed.
- If the HTTP server is unavailable, existing adapter error behavior is
  unchanged; this change only changes which backend a fresh configuration uses.

## Documentation

Update `docs/configuration.md` and `docs/user-acceptance-testing.md` so the
normal path says to run the ACE-Step REST server and use `ace-step-http`. Keep
the mock-mode section in `README.md` as an explicit developer fallback. Leave
the user’s existing uncommitted `config.example.toml` edits untouched; the
application default and documentation are the source of truth for this change.

## Testing

- A config with no file defaults to `ace-step-http` and
  `http://127.0.0.1:8001`.
- An existing TOML backend remains unchanged; an existing file without a
  backend uses `ace-step-http`.
- `LOFI_BACKEND=mock` still selects mock mode and overrides TOML.
- An unset or empty `LOFI_BACKEND` does not override TOML.
- Invalid backend values still raise validation errors.
- `PYTHONPATH=src pytest -q` passes, including the existing HTTP adapter tests.

## Non-goals

- No changes to the ACE-Step REST adapter.
- No changes to local model installation or checkpoint handling.
- No removal of mock mode.
- No changes to playback, TUI controls, or saved output formats.
