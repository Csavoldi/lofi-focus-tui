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

The TUI starts with a deep-work session. Choose focus, music preset, duration, energy, and style fields from the keyboard, then press `s`.

```text
1       change focus
p       change music preset
2       change duration
3       change energy
4       change style
h       open option guide
Escape  close option guide
q       quit
```

Press `h` to open the option guide. Press `Escape` or `h` to close it; selection and session actions are suppressed while it is open, and `q` remains the global quit key.

## Option Meanings

### Focus

```text
deep_work: sustained concentration and low distraction
reading: spacious, calm, gentle pulse
coding: forward momentum and a steady groove
wind_down: soft, slow decompression
```

### Music presets

```text
classic_lofi: dusty keys, swung drums, round bass
neo_soul: warm chords, pocketed rhythm, mellow bass
ambient_tape: sparse pulse, wide pads, tape haze
jazz_vinyl: brushed drums, jazz harmony, vinyl texture
```

### Energy

```text
low: soft movement and a restrained pulse
steady: balanced movement for ordinary focus work
high: more rhythmic momentum while remaining non-distracting
```

### Style

```text
lofi, neo_soul: warm, dusty, chord-forward texture
ambient, tape: spacious, hazy, slowly moving texture
rainy, mellow: soft atmosphere and subdued detail
jazz, vinyl: brushed, tactile, lightly swinging texture
```

The status panel shows backend state, device, playback mode, generation progress, chunk progress for long sessions, and recent saved sessions.
If no audio device is available, generated audio is saved and status reports playback as disabled.

Long sessions are generated in quality-oriented chunks: a 5-minute request uses one 5-minute
chunk, while longer requests use chunks up to 10 minutes with a shorter final remainder. The
generator analyzes each boundary and carries only targeted continuation guidance into the
next prompt. Severe continuity failures are retried once; the final chunks are joined with a
fixed crossfade.

## Outputs

Generated sessions are saved under:

```text
~/.cache/lofi-focus-tui/outputs
```

History is stored as JSON lines at:

```text
~/.cache/lofi-focus-tui/history.jsonl
```

Each saved session includes `audio.wav` and `metadata.json` with request, plan, blueprint, settings, device, seed, and generation metadata. Chunked metadata includes per-chunk profiles, boundary warnings, continuation handoffs, and retry counts.
For chunked sessions, metadata includes both requested and actual stitched duration because crossfades shorten the final WAV slightly.

## Diagnostics

Run:

```bash
lofi-doctor
```

Warnings for optional packages are expected unless you installed ACE-Step, RunPod, or playback extras.
