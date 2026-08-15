# ACE-Step HTTP Default

## Status

Approved direction for implementation on the `dev` branch.

## Goal

Make the configured default generation backend `ace-step-http` so a fresh install
uses the user’s running ACE-Step REST server instead of the placeholder mock tone.

## Behavior

- `GenerationConfig.backend` defaults to `"ace-step-http"`.
- The default REST base URL remains `http://127.0.0.1:8001`.
- An explicit TOML `generation.backend` value is preserved.
- `LOFI_BACKEND` continues to override TOML and can explicitly select `mock`,
  `ace-step`, `ace-step-http`, or `runpod`.
- Mock mode remains available for offline development; it is no longer the default.
- The local `ace-step` backend remains available when explicitly selected.
- No ACE-Step server API or generation payload changes are needed.

## Documentation

Update the configuration and setup guidance so the normal path says to run the
ACE-Step REST server and use `ace-step-http`. Keep the mock-mode section as an
explicit developer fallback. Do not overwrite the user’s existing uncommitted
`config.example.toml` edits; the application default and documentation are the
source of truth for this change.

## Testing

- A config with no file defaults to `ace-step-http`.
- An explicit TOML backend remains unchanged.
- `LOFI_BACKEND=mock` still selects mock mode.
- Invalid backend values still raise validation errors.
- Existing HTTP adapter and full test coverage remain green.

## Non-goals

- No changes to the ACE-Step REST adapter.
- No changes to local model installation or checkpoint handling.
- No removal of mock mode.
- No changes to playback, TUI controls, or saved output formats.
