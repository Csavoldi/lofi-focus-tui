# Audio Chunk Orchestration

## Status

Approved design for the first audio-orchestration plan on the `dev` branch.
Implementation planning is intentionally separate from this document. Playback controls
and user-selected export are deferred to Plan 2.

## Goal

Improve long-session generation quality by using larger, quality-oriented chunks and a
small deterministic feedback loop between chunks. The loop should preserve the session's
focus, music preset, energy, and style while reducing abrupt transitions, loudness jumps,
clicks, silence gaps, clipping, and texture changes.

## Current behavior

`GenerationConfig.chunk_seconds` defaults to 30 seconds and is passed to
`SessionManager`. The session manager splits a requested duration into chunks, calls the
configured model adapter for each chunk, checks boundaries with `analyze_boundary`, retries
one failed boundary, and stitches accepted chunks with a fixed crossfade.

The existing continuity report checks RMS difference, a boundary sample delta, silence,
and clipping. The ACE-Step adapters build each chunk prompt from the same composition
blueprint, so later chunks do not receive audio-derived continuation guidance.

## Chunk sizing

The requested session duration determines the target chunk size:

| Requested duration | Target chunk size | Example chunk durations |
|---|---:|---|
| 5 minutes | 300 seconds | `[300]` |
| More than 5 minutes | 600 seconds | 11 minutes → `[600, 60]` |

The final chunk may be shorter than the target. A session of 6 minutes therefore remains
one 360-second chunk rather than being split into an unnecessary 300/60 pair. The existing
240-minute request limit remains unchanged.

`generation.chunk_seconds` remains as a compatibility and safety cap, but its default
changes from 30 to 600. The policy selects 300 seconds for a 5-minute request and 600
seconds for longer requests, then applies any explicitly configured lower cap. Values over
600 remain invalid. This preserves an operator's ability to lower chunk size without
allowing the old 30-second default to govern normal generation.

Chunk sizing belongs in the existing timing resolution path. No new duration selector or
ACE-Step server API is required.

## Orchestration flow

The existing `SessionManager._generate_session_result` loop remains the orchestrator:

```text
SessionPlan + CompositionBlueprint
        |
        v
resolve target chunk size
        |
        v
create chunk blueprint + continuation handoff
        |
        v
generate chunk through the existing model adapter
        |
        v
analyze chunk and boundary
        |
        +--> ordinary warning: build handoff for the next chunk
        |
        +--> severe boundary: retry this chunk once with corrective handoff
        |
        v
fixed crossfade and append
        |
        v
final stitched result + per-chunk metadata
```

The session's original plan remains authoritative. Audio analysis can add narrowly scoped
continuation constraints, but it cannot replace the selected focus, music preset, energy,
style, tempo range, key center, or motif.

## Audio analysis

Extend the existing `lofi_focus_tui.audio.continuity` module rather than adding an audio
analysis service or dependency.

Add a lightweight per-chunk profile based on the existing NumPy audio helpers. The profile
should include:

- duration and sample rate;
- RMS/loudness estimate and peak level;
- silence and clipping indicators;
- a short-window spectral balance estimate for the tail and head of a boundary.

The boundary report should continue to expose the current warnings and add a comparison of
short tail/head windows for abrupt spectral changes. It should not attempt to infer musical
key or tempo from the waveform. Those values already come from the deterministic plan and
are more reliable as continuity constraints.

Analysis should be deterministic, bounded to short windows, and serializable to JSON. The
normal path must not invoke an LLM, call a remote service, or load another model.

## Continuation handoff

Each generated chunk can produce a compact list of continuation notes for the next chunk.
The notes are categorical prompt constraints, not a dump of raw numeric measurements.

Examples:

| Detected condition | Next-chunk continuation note |
|---|---|
| loudness jump | `match the previous chunk's loudness at the transition` |
| boundary click or sharp transient | `avoid a sharp transient at the transition` |
| silence gap | `maintain continuous low-level texture through the transition` |
| clipping | `reduce peak density and avoid aggressive transients` |
| spectral change | `continue the established timbral balance into the next section` |

Clean boundaries produce no corrective warning. The base prompt still carries the existing
composition and continuity requirements, including a coherent arrangement and shared motif.

Add optional continuation constraints to the per-chunk composition blueprint. The existing
ACE-Step prompt builder appends those constraints only when present. Both embedded and HTTP
ACE-Step adapters therefore receive the same prompt without changing the REST payload shape.

The session manager carries the handoff in memory between chunks and records it in the
generation metadata. It does not mutate the original session plan.

## Boundary handling and retry policy

The existing fixed crossfade remains the stitching mechanism. Start with the current
one-second crossfade; do not add adaptive crossfade lengths in this iteration. A future
crossfade change should be driven by real listening tests rather than by speculative
configuration.

There are two response levels:

1. **Ordinary warning:** keep the generated chunk, record the report, and apply corrective
   notes only to the next chunk's prompt.
2. **Severe boundary failure:** retry the current chunk once with corrective continuation
   constraints and a deterministic seed offset. This is reserved for an objectively
   unusable transition such as a click, silence gap, clipping, or major discontinuity.

If the retry also fails the existing continuity gate, fail the generation task with a clear
error. Do not silently save a final file known to contain a severe broken boundary.

The retry must reuse the existing cancellation checks and task status updates. Stop remains
responsive between chunks and between a failed attempt and its retry.

## Metadata

The existing generated metadata gains a `chunks` list. Each entry records enough information
to explain the final result without storing duplicate audio:

```json
{
  "index": 1,
  "duration_seconds": 600,
  "profile": {"rms": 0.12, "peak": 0.71, "silent": false, "clipped": false},
  "boundary": {"accepted": true, "warnings": []},
  "handoff": [],
  "retry_count": 0
}
```

The exact numeric profile fields may expand as implementation requires, but all values must
remain JSON-compatible. Existing requested and actual duration fields remain unchanged.

## Error handling

- Invalid chunk configuration continues to fail at the Pydantic configuration boundary.
- An analyzer exception should be surfaced as a generation error when it prevents a reliable
  severe-boundary decision; it must not produce an unreported transition.
- Cancellation is checked before each chunk and before a retry.
- A failed retry includes the boundary warnings in the final task error.
- A successful retry is recorded in metadata and does not change the session's requested
  duration.

## Testing

Tests should cover the smallest meaningful behavior at each existing boundary:

- configuration accepts a 600-second cap, defaults to 600, and rejects values above 600;
- timing resolution maps a 5-minute request to `[300]`;
- timing resolution maps longer requests to 600-second chunks plus a final remainder;
- a lower explicit cap remains honored;
- chunk profiles and boundary reports are deterministic for clean, silent, clipped, loudness-
  jump, and spectral-change fixtures;
- clean boundaries add no corrective prompt notes;
- ordinary warnings change only the next chunk prompt;
- severe warnings cause exactly one retry with corrective constraints;
- a failed retry stops the task and reports the boundary reason;
- successful retries preserve duration, plan identity, and seed determinism;
- prompt generation includes continuation constraints for both embedded and HTTP ACE-Step
  adapters while preserving the existing REST payload shape;
- stitched output still uses the fixed crossfade and reports requested versus actual duration;
- metadata contains per-chunk profiles, reports, handoffs, and retry counts;
- existing short-generation, cancellation, HTTP adapter, and session-manager tests remain
  green.

Use small synthetic NumPy arrays and fake model adapters for unit tests. Real ACE-Step audio
is reserved for the existing opt-in live tests and manual listening checks.

## Non-goals

- No LLM or remote orchestration service.
- No new audio-analysis model or third-party dependency.
- No waveform-based key or tempo inference.
- No adaptive crossfade.
- No live streaming generation changes.
- No playback-control or user-selected export work; those belong to Plan 2.
- No change to the 240-minute request limit.
