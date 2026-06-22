# Usage

## Install

```bash
python -m pip install -e ".[dev]"
```

Install optional playback support when you want local audio output through `sounddevice`:

```bash
python -m pip install -e ".[playback]"
```

## Start Mock Mode

Start the backend:

```bash
lofi-backend
```

Start the TUI in a second terminal:

```bash
lofi
```

Press `s` to start a session. Use `space` to pause or resume, `x` to stop, and `r` to refresh.
The duration selector includes a 5-minute option for real-generation smoke tests.

## Session Controls

The TUI starts with a deep-work session. Cycle presets, duration, energy, and style fields from the keyboard, then press `s`.

The status panel shows backend state, device, playback mode, generation progress, chunk progress for long sessions, and recent saved sessions.
If no audio device is available, generated audio is saved and status reports playback as disabled.

## Outputs

Generated sessions are saved under:

```text
~/.cache/lofi-focus-tui/outputs
```

History is stored as JSON lines at:

```text
~/.cache/lofi-focus-tui/history.jsonl
```

Each saved session includes `audio.wav` and `metadata.json` with request, plan, blueprint, settings, device, seed, and generation metadata.
For chunked sessions, metadata includes both requested and actual stitched duration because crossfades shorten the final WAV slightly.

## Diagnostics

Run:

```bash
lofi-doctor
```

Warnings for optional packages are expected unless you installed ACE-Step, RunPod, or playback extras.
