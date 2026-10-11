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

Start the app:

```bash
LOFI_BACKEND=mock lofi
```

Press `s` to start a session. Use `space` to pause or resume, `x` to stop, and `r` to refresh.
The duration selector includes a 5-minute option for real-generation smoke tests.

## Start ACE-Step HTTP Mode

Start the separate ACE-Step HTTP service as described in [`docs/ace-step.md`](ace-step.md),
then run the Lofi app from this repository:

```bash
lofi
```

Port `8001` belongs only to the external ACE-Step service; the Lofi app runs in one process
and does not need a separate service terminal.

## Session Controls

The TUI starts with a deep-work session. Choose focus, music preset, duration, energy, and style fields from the keyboard, then press `s`.

```text
1       change focus
p       change music preset
2       change duration
3       change energy
4       change style
[       lower volume by 10%
]       raise volume by 10%
,       rewind 10 seconds
.       forward 10 seconds
0       restart the current audio without regenerating
e       open the export dialog
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
lofi_house: washed chord stabs, four-on-the-floor, tape hiss
synthwave: analog arps, gated drums, neon nostalgia
city_pop: funky bass, bright keys, 80s sheen
boom_bap: gritty breaks, sampled chops, vinyl grit
peaceful_piano: felt piano, dreamy pads, near-weightless
```

Each preset carries its own tempo range; energy picks the soft, natural, or livelier
end of it (for example lofi_house sits at 110-125 BPM while neo_soul sits at 65-85).
Each preset also holds ten prompt variations (different lead sounds, drum feels, and
basslines); the session seed picks one, so the same seed reproduces the same variation
and every chunk of a session shares it.

### Energy

```text
low: slow and spacious, resting at the soft end of the preset's tempo range
steady: the preset's natural tempo, balanced for ordinary focus work
high: livelier end of the preset's tempo range, still non-distracting
```

### Style

```text
lofi, neo_soul: warm, dusty, chord-forward texture
ambient, tape: spacious, hazy, slowly moving texture
rainy, mellow: rainy-day atmosphere, soft and subdued
jazz, vinyl: brushed, tactile, lightly swinging texture
vinyl, dust: crackly, gritty beattape texture
neon, retro: bright 80s sheen, nostalgic glow
```

The status panel shows backend state, device, playback mode, volume, playback position and duration,
generation progress, chunk progress for long sessions, and recent saved sessions.
If no audio device is available, generated audio is saved and status reports playback as disabled.

Playback keys work on the completed session currently loaded by the backend. They do not trigger
new generation. Volume is clamped between 0% and 100%, and seeking is clamped to the audio bounds.

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

To export a completed session, press `e`, enter a directory, and press Enter. The app creates a
subdirectory named after the saved session and copies both `audio.wav` and `metadata.json` into it.
The default directory is `~/Music/lofi-focus-tui`. Export never changes or deletes the cached source.
Press `Escape` to cancel; an invalid directory leaves the dialog open with the error shown.

## Diagnostics

Run:

```bash
lofi-doctor
```

Warnings for optional packages are expected unless you installed ACE-Step, RunPod, or playback extras.
