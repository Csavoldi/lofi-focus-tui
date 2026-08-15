# Playback Controls and Session Export

## Status

Approved design for the second user-facing feature plan on the `dev` branch. Audio chunk
orchestration is already implemented separately. This feature adds playback control and
manual export without changing generation behavior.

## Goal

Let a user control the currently loaded session from the TUI and export that session's audio
and metadata to a directory of their choice.

## Current behavior

The backend owns a `PlaybackManager` with pause, resume, and stop. `SoundDevicePlayer` tracks
its current frame internally, but the manager and REST API expose no seek, restart, volume, or
position controls. The TUI can call only pause, resume, and stop.

Generated sessions are automatically written by `OutputManager` under the cache output
directory. There is no user-triggered export path. The TUI has no modal input for a directory.

## User-facing controls

The existing controls remain unchanged. Add:

```text
[ / ]   volume down/up
, / .   rewind/forward 10 seconds
0       restart current audio
e       export audio and metadata
```

Volume changes use a fixed step of `0.10` and clamp to `0.0–1.0`. Seek changes use exactly
10 seconds and clamp to the loaded audio bounds. Restart seeks to frame zero without
regenerating audio.

The main status display adds current volume and playback position/duration when available.
Controls remain safe when audio is not loaded; the backend returns a clear status message and
the TUI displays it.

## Architecture

The backend remains the sole owner of playback state:

```text
TUI key action
      |
      v
BackendClient REST call
      |
      v
FastAPI session endpoint
      |
      v
SessionManager -> PlaybackManager -> Player
```

The TUI stays a thin client. It does not open audio devices, hold audio buffers, or duplicate
playback position. No new playback service or audio dependency is introduced.

## Playback interface

Extend the existing `Player` protocol with the smallest operations needed by the controls:

- `set_volume(volume: float) -> bool`;
- `seek(seconds: float) -> bool`;
- `restart() -> bool`;
- `position_seconds() -> float`;
- `duration_seconds() -> float`.

`PlaybackManager` exposes matching operations, clamps volume and position, and returns a
boolean for operations that require loaded audio. Existing `pause`, `resume`, `stop`, and
fallback behavior remain unchanged.

`SoundDevicePlayer` retains the prepared audio, sample rate, current frame, and current
volume. Volume is applied in the output callback so it can change without rebuilding the
audio buffer. Seek clamps the frame, stops/restarts the stream only when necessary, and keeps
the player state (`playing`, `paused`, or `stopped`) consistent. Restart is seek-to-zero.

`NullPlayer` implements the same operations without requiring a sound device. It stores enough
state for deterministic tests and reports position zero when no real clock is available.

## Backend API

Add validated request models at the FastAPI boundary:

```python
class VolumeAdjustment(BaseModel):
    delta: float = Field(ge=-1.0, le=1.0)


class SeekAdjustment(BaseModel):
    seconds: float = Field(ge=-86400.0, le=86400.0)


class ExportRequest(BaseModel):
    directory: str = Field(min_length=1)
```

Add endpoints:

```text
POST /sessions/volume   {"delta": 0.10}
POST /sessions/seek     {"seconds": 10}
POST /sessions/restart
POST /sessions/export  {"directory": "~/Music/lofi-focus-tui"}
```

The first three return the existing `BackendStatus` response with updated playback fields.
Export returns a dedicated response containing the exported audio path, metadata path, and a
short message. Invalid bodies receive normal FastAPI validation errors. Playback failures
return a clear backend error rather than raising an uncaught exception through the API.

`BackendStatus` gains defaulted fields so existing clients remain compatible:

```text
volume: float = 0.8
position_seconds: float = 0.0
duration_seconds: float = 0.0
```

The status-building path reads these values from `PlaybackManager` so normal `/status`
refreshes reflect the controls.

## TUI export flow

Pressing `e` opens a small modal screen with one text input:

```text
Export directory:
~/Music/lofi-focus-tui
Enter export   Escape cancel
```

The input defaults to `~/Music/lofi-focus-tui`. On Enter, the TUI sends the expanded string
to the backend. Escape cancels without a request. While the modal is open, unrelated session
selection actions are suppressed; `q` remains a global quit action.

On success, the TUI reports the exported directory. On failure, it keeps the modal open and
shows the backend error so the user can correct the path.

## Export behavior

`SessionManager.export_current(directory)` exports only a completed session with a saved
source audio path. If no completed session is loaded, it returns a clear error and does not
create files.

`OutputManager` adds an export helper using `pathlib` and `shutil.copy2`:

1. Expand the destination directory and create it if needed.
2. Create a unique child directory using the existing source session directory name.
3. Copy `audio.wav` and its sibling `metadata.json` into that child directory.
4. Return both resulting paths.

The export preserves the generated WAV and the complete metadata, including request, plan,
blueprint, generation settings, chunk profiles, handoffs, and retry information. It does not
move or delete the automatic cache copy. Re-exporting the same session replaces files only in
that session's chosen export directory; it never modifies the cache source.

## Error handling and concurrency

- Volume and seek values are clamped before reaching the player.
- Controls with no current result return `False` and a user-readable status message.
- A seek beyond the audio bounds lands exactly at the beginning or end.
- Sound-device errors retain the existing fallback to `NullPlayer`.
- Export validates the directory input and reports filesystem errors through the API.
- Export runs only after generation has completed, so it copies an immutable saved session.
- No generation task is cancelled by a playback adjustment or export request.

## Testing

Tests should cover the smallest existing seams:

- `SoundDevicePlayer` and `NullPlayer` clamp volume, seek, and restart correctly;
- `PlaybackManager` forwards controls, preserves pause state, and reports position/duration;
- status responses include default and updated playback fields;
- each REST endpoint accepts valid input and rejects invalid shapes/ranges;
- `BackendClient` calls every new endpoint and handles HTTP failures consistently;
- TUI bindings invoke the correct client methods for `[`, `]`, `,`, `.`, `0`, and `e`;
- the export modal submits on Enter and cancels on Escape;
- export copies both `audio.wav` and `metadata.json` into a unique destination child;
- export rejects missing current audio and invalid filesystem paths without partial output;
- existing pause/resume/stop, generation, API, and TUI tests remain green.

Use fake players, HTTP transports, and temporary directories. Do not require a sound device or
the ACE-Step server for unit tests.

## Non-goals

- No native GUI file picker.
- No playlist or multi-session queue.
- No playback controls while audio is still generating.
- No streaming generation changes.
- No new audio format conversion.
- No change to automatic cache output behavior.
