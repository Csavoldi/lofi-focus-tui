# Freeform Prompt Engine Design

**Date:** 2026-08-17  
**Status:** Approved

## Goal

Make ACE-Step prompting more expressive without removing the existing style,
energy, focus, and music-preset categories.

## Requirements

- Let the user enter an optional freeform music prompt.
- Keep style, energy, focus, and music preset as selectable categories.
- Treat categories as optional hints rather than fixed recipes or hard commands.
- Give explicit user wording precedence over category hints and generated defaults.
- Add an explicit instrumental/vocal toggle; default to instrumental.
- Use ACE-Step prompt enrichment when the HTTP backend supports it.
- Fall back to the local prompt when enrichment is unavailable or invalid.
- Preserve the existing generation, chunking, continuity, playback, and export flows.
- Keep older API clients compatible by defaulting missing prompt fields.

## Design

### Input model

`SessionRequest` gains:

- `prompt: str = ""`, with a maximum length of 512 characters; surrounding
  whitespace is stripped first, whitespace-only input becomes `""`, and the
  normalized value—not the raw value—is checked against the 512-character
  maximum; a normalized value over 512 characters is rejected by the existing
  Pydantic/API validation path;
- `vocal_mode: Literal["instrumental", "vocals"] = "instrumental"`; supplied
  string values are normalized with `strip().lower()` before validation, while
  non-string values and blank explicit values are rejected.

The TUI keeps the existing category controls and adds a prompt editor plus a
vocal-mode toggle. The prompt is optional, so category-only requests remain
valid.

The fields flow through the existing models without a second request object:

| Stage | `prompt` | `vocal_mode` | `energy` |
|---|---|---|---|
| `SessionRequest` | user input, default `""` | user selection, default `instrumental` | existing field |
| `SessionPlan` | copied from request, default `""` | copied from request, default `instrumental` | existing field |
| `CompositionBlueprint` | copied from plan, default `""` | copied from plan, default `instrumental` | copied from plan, default `steady` for legacy/direct construction |
| adapters | read from blueprint | read from blueprint | read from blueprint |

Defaults on `SessionPlan` and `CompositionBlueprint` allow older serialized
plans and direct constructors to continue loading. `create_blueprint()` is the
single mapping point for the plan-to-blueprint copy. `SessionPlan.energy`
remains its existing required field; the new `CompositionBlueprint.energy`
field defaults to `EnergyLevel.STEADY` only when an older/direct blueprint
omits it. `prompt` and `vocal_mode` use the defaults above on both models, and
the `vocal_mode` validator applies the stated trim/lowercase normalization on
both models.

All prompt lengths are Unicode character counts (`len(str)`), never encoded
byte counts. Every prompt emitted to `/format_input` or `/release_task` is
normalized and must be at most 512 characters.

### Prompt precedence

The prompt engine combines input in this order:

1. User freeform wording.
2. Selected category hints.
3. Existing blueprint details and generated defaults.

The local engine produces natural-language guidance, not a large hardcoded
style/energy/focus matrix. Category text describes possible texture, rhythm,
instrumentation, and focus behavior. It does not rewrite or contradict a
user-provided idea. Existing style tags, preset motifs, and continuation notes
are folded into the blueprint's `texture_layers`, `motif`, and
`continuation_constraints`; they are not appended by a second prompt rule.
The exact part/item order below is the sole canonical output rule.

The local composition rule is deterministic:

1. Normalize every part with `part.strip()` and discard empty parts.
2. Build parts in this exact order: user prompt; an optional musical-context
   part; an optional technical-direction part; and the selected vocal
   direction. The musical-context items are, in order:
   `blueprint.texture_layers`, `blueprint.motif`, `blueprint.drum_feel`,
   `blueprint.bass_behavior`,
   `f"{energy.value} energy: {ENERGY_OPTIONS[energy].description}"`, and
   `f"{focus} focus: {', '.join(focus_constraints)}"`. The part is omitted
   when its item list is empty and otherwise has the exact prefix
   `Optional musical context: ` with items joined by `, `.
3. The technical-direction items are, in order: `f"{tempo_bpm} BPM"`,
   `key_center`, `f"meter {meter}"`,
   `f"arrangement: {', '.join(arrangement_sections)}"`, every
   `boundary_constraints` item, and every `continuation_constraints` item.
   Empty items are omitted. The part is omitted when empty and otherwise has
   the exact prefix `Technical direction: ` with items joined by `, `.
   List-valued fields are flattened in their existing order: each non-empty
   `texture_layers`, boundary, and continuation item is one item; arrangement
   sections and focus constraints are first filtered and then joined by `, `
   inside their labeled item. Every scalar and list item is stripped before
   this filtering. An empty `focus_constraints` list omits the focus item, and
   an empty `arrangement_sections` list omits the arrangement item.
4. The exact vocal direction is `Vocal direction: instrumental, no vocals`
   for instrumental mode and `Vocal direction: vocals allowed` for vocal
   mode.
5. Join accepted parts with the literal separator `. `.
6. Append parts left-to-right using the 512-character budget. Before each
   part, calculate the separator (`""` for the first part, otherwise `. `).
   If fewer than `len(separator) + 1` characters remain, append neither
   separator nor part and stop. Otherwise append the leading substring that
   fits after `rstrip()`; append the separator only if that substring is
   non-empty. If the part was truncated, stop and drop later parts. This
   guarantees no dangling `. ` separator and no trailing whitespace.

The user prompt is never parsed, deleted, or replaced. If the assembled prompt
would exceed 512 characters, the first part that does not fit is truncated and
all later parts are dropped; the normalized user prompt is the first preserved
substring. No attempt is made to algorithmically resolve conflicting user and
category language. The explicit vocal toggle is a safety control: its vocal
direction is appended when the 512-character budget permits, while the
instrumental/vocal lyrics payload remains authoritative even if the freeform
wording mentions the opposite mode.

The same 512-character budget applies after remote enrichment. If the user
prompt plus the enriched caption exceed the budget, keep the full user prompt
and apply the same separator calculation and leading-substring rule to the
enriched caption; if no character fits, the final prompt is the user prompt
alone.

Technical generation values remain explicit request fields where supported:
duration, BPM, key, meter, batch size, and inference settings. Continuity
requirements remain local orchestration constraints rather than relying only
on prose in the prompt.

### Local prompt engine

Add a focused prompt-engine module responsible for composing the local prompt
from the composition blueprint. It reuses the existing option catalogs and
the blueprint fields described by the canonical composition rule. It is used
by embedded, HTTP, mock, and other adapters so all backends see the same
baseline prompt.

The engine should produce a useful prompt even when `prompt` is empty. It must
remain deterministic for the same blueprint and seed so tests and repeated
sessions are reproducible.

`expand_preset()` copies `request.prompt` and `request.vocal_mode` into the
plan. `create_blueprint()` copies those fields and `plan.energy` into the
blueprint. `create_chunk_blueprint()` uses `model_copy()` without replacing
those fields, so every chunk inherits the same user intent and vocal mode.

`SessionManager.start_session()` calls `expand_preset()` and
`create_blueprint()` once before submitting the generation task. For a
multi-chunk session, `_generate_session_result()` reuses that one
`SessionPlan` and passes the already-created base blueprint to
`create_chunk_blueprint(plan, ..., base_blueprint=blueprint)`. With
`base_blueprint` supplied, the helper only calls `model_copy(update=...)`; it
does not call `create_blueprint()` again. Direct callers may omit the optional
`base_blueprint` and retain the existing helper behavior. Chunk creation may
add section and continuation details, but it must not re-plan the user prompt,
categories, energy, or vocal mode. Tests must assert one
`create_blueprint()` call per session and that every chunk retains the base
blueprint's prompt, energy, and vocal mode.

When `vocal_mode="instrumental"`, planning adds the automatic `vocals` avoid
trait. When `vocal_mode="vocals"`, that automatic trait is omitted and a
literal `vocals` or `no vocals` value supplied through the legacy `avoid_tags`
field is filtered out so the explicit toggle cannot contradict itself. Tag
normalization for comparison is `replace("_", " ").strip().lower()`. Filtering
compares that normalized value against `{"vocals", "no vocals"}`. Every other
tag is preserved using the existing `replace("_", " ")` transformation without
lowercasing it.

### ACE-Step enrichment

For the HTTP ACE-Step backend, pass the local prompt through the official
`POST /format_input` endpoint when the service is available. Supply the
selected metadata in `param_obj` so the LM can expand the caption without
silently changing user-selected duration, BPM, key, or meter.

The exact request is:

```json
{
  "prompt": "<local prompt>",
  "lyrics": "[Instrumental]" or "",
  "temperature": 0.85,
  "param_obj": "{\"bpm\":80,\"duration\":60,\"key\":\"minor pentatonic\",\"language\":\"unknown\",\"time_signature\":\"4\"}"
}
```

For this enrichment request specifically, `lyrics` is exactly
`[Instrumental]` in instrumental mode and exactly `""` in vocal mode. This is
separate from the later `/release_task` payload, where vocal mode may use the
returned formatted lyrics.

The `param_obj` value is produced with
`json.dumps(metadata, sort_keys=True, separators=(",", ":"))` from this exact
metadata mapping: `duration` (integer seconds), `bpm` (integer), `key` (key
center string), `time_signature` (meter numerator string), and `language`
(`"unknown"`).

`bpm`, `key`, and `time_signature` come from the blueprint. `duration` comes
authoritatively from the `duration_seconds` argument to `submit_task()` and is
encoded in seconds. `time_signature` is the numerator from the blueprint
meter, for example `"4"` for `4/4`.

The response must unwrap a dictionary under `data` and contain a string
`caption` whose stripped value is non-empty and no longer than 512 characters.
The stripped caption value is accepted as the enrichment result. An optional
string `lyrics` field is stripped first and used only when the stripped value
is non-empty and no longer than 4096 characters; an
invalid optional lyrics field is treated as missing while a valid caption is
still usable. When a user prompt exists, the final prompt starts with the
normalized user wording, then uses the literal separator `. `, then appends as
much of the accepted enriched caption as fits the 512-character budget using
the same separator and leading-substring rule as local composition. Thus the
original wording remains present and first. When no user prompt exists, the
enriched caption is used directly.

The adapter invokes the endpoint as
`self.client.post("/format_input", json=payload, headers=self._headers(),
timeout=min(30.0, self.timeout_seconds))`. There is no retry. An HTTP status
error, connection or timeout error, invalid JSON, non-dictionary `data`,
missing or blank `caption`, an overlong `caption`, or a caption schema/type
error causes a local fallback and does not fail generation. A malformed
optional `lyrics` value is ignored and treated as missing when the caption is
valid.

The required sequence is: compose the local prompt; call `/format_input` once;
derive the final prompt from the accepted caption or local fallback using the
rules above; then send that exact final prompt as the `prompt` field of
`/release_task`. A valid caption with no user wording is therefore sent
unchanged (after stripping) to `/release_task`; a failed enrichment sends the
local prompt instead. The polling and audio download steps follow unchanged.

The enrichment step must not change the existing `/release_task` polling or
audio download contract. It is a prompt-quality enhancement, not a new model
adapter.

### Vocal mode

- `instrumental` sends `lyrics="[Instrumental]"` to ACE-Step.
- HTTP/RunPod `vocals` always sends `thinking=true`; it sends the enriched
  `lyrics` response when one is available, otherwise `lyrics=""` so ACE-Step
  can generate lyrics from the prompt. Embedded mode preserves its existing
  pipeline flags and does not receive a new `thinking` argument.
- The freeform prompt does not automatically change vocal mode.

Instrumental generation preserves the current `thinking=false` behavior.
Vocal mode is the explicit exception because it needs an LM-generated lyric
path when the user has not supplied lyrics separately.

This keeps vocal behavior explicit and avoids accidental vocals in focus
sessions.

Adapter behavior is explicit:

| Adapter | Local prompt | Instrumental payload | Vocal payload |
|---|---|---|---|
| `AceStepHttpAdapter` | shared local/enriched prompt | `lyrics="[Instrumental]"`, `thinking=false` | enriched lyrics or `""`, `thinking=true` |
| `RunPodAceStepAdapter` | inherited HTTP behavior | inherited HTTP behavior | inherited HTTP behavior |
| `AceStepAdapter` | shared local prompt | `lyrics="[Instrumental]"` | `lyrics=""`; existing embedded pipeline flags remain unchanged |
| `MockModelAdapter` | blueprint retains prompt and vocal mode; audio behavior unchanged | no remote payload | no remote payload |

HTTP/RunPod are the supported paths for LM-generated vocals. Embedded and mock
backends preserve their existing capabilities and do not gain a separate
lyrics-generation subsystem in this change.

`RunPodAceStepAdapter` inherits the complete HTTP implementation and does not
override prompt enrichment or vocal payload construction. `AceStepAdapter`
passes the exact lyrics value shown in the table to its existing pipeline call;
it does not receive a new `thinking` argument. `MockModelAdapter` remains a
local audio stub, while its blueprint still exposes the new fields for request
and propagation tests.

### TUI interaction

- The main screen contains a normal `Input` prompt editor configured with a
  512-character Unicode-character maximum for raw input. It accepts arbitrary
  text, preserves the editor's current value while category keys are used, and
  submits its stripped value; the model validator rechecks the normalized
  value, and whitespace-only input becomes `""`. It starts blurred/unfocused
  so the existing app bindings remain active on startup.
- `i` focuses the prompt editor; it does not open a category picker or replace
  existing text. While the editor is focused, ordinary characters—including
  `v` and category keys—are inserted into the prompt rather than dispatched as
  app actions.
- `escape` blurs the editor without changing its value. Enter submits the
  editor value, updates the draft summary, and blurs the editor. App actions
  such as `v`, `1`, `p`, `2`, `3`, and `4` are dispatched only when the editor
  is not focused; `s` starts a session only in that unfocused state.
- `v` toggles instrumental/vocal mode when the editor is not focused.
- Existing keys continue to cycle focus, preset, duration, energy, and style
  when the editor is not focused.
- Starting a session reads the editor value and sends `avoid_tags=["vocals"]`
  only in instrumental mode; vocal mode sends an empty legacy avoid-tag list.
- The session display shows the active vocal mode and a prompt summary. The
  summary is `(category-generated)` when the normalized prompt is empty, the
  exact prompt when its length is at most 80 characters, and the first 77
  characters plus `...` otherwise. It is derived from the normalized current
  editor draft and refreshed after text changes, Enter, blur, and category
  changes; it is not replaced by the later enriched caption.

The prompt editor is a normal text input, not a constrained list. Categories
remain visible as context and quick starting points.

## Error handling

Prompt enrichment failures are non-fatal. The adapter should catch transport,
HTTP, JSON, and schema failures at the enrichment boundary and use the local
prompt. Generation failures after submission retain their existing error
handling behavior.

The local engine remains the only required prompt path, so mock mode and
offline development do not need ACE-Step or another LLM service.

## Testing

Add focused tests for:

- freeform text appearing first and surviving category composition;
- conflicting category/default wording never replacing the user's wording;
- normalized prompt lengths of 511, 512, and 513 Unicode characters with and
  without surrounding whitespace;
- category-only prompts producing useful local output;
- deterministic output for the same blueprint and seed;
- instrumental and vocal request payloads;
- successful `/format_input` enrichment using preserved metadata;
- user wording retained ahead of an enriched caption;
- 512-character boundary for local and enriched prompts;
- exact local separator and truncation order;
- golden local output covering flattened list items, empty lists, separator
  boundaries, and trailing-whitespace truncation with no dangling separator;
- fallback for connection refusal, timeout, HTTP failure, malformed response,
  missing data, whitespace-only caption, and overlong caption;
- exact `/format_input` request shape, timeout cap, and no-retry behavior;
- exact `/format_input` then `/release_task` prompt sequence for both enriched
  and fallback paths;
- exact `param_obj` JSON serialization and vocal-mode normalization;
- invalid optional lyrics and caption schema/type handling;
- vocal-mode behavior with and without returned lyrics;
- request-to-plan-to-blueprint-to-chunk propagation;
- one session plan reused across all chunks without re-planning;
- one base `create_blueprint()` call per session and chunk copies derived from
  that base blueprint;
- vocal mode omitting the automatic anti-vocal trait;
- case/whitespace/underscore normalization for legacy vocal avoid tags;
- RunPod HTTP behavior inheritance and mock blueprint field availability;
- API defaults when `prompt` and `vocal_mode` are omitted;
- TUI prompt editing, focus behavior, Enter/Escape state transitions, focused
  key insertion versus unfocused app actions, 512-character input boundary,
  exact summary truncation, vocal toggling, and request construction.

Existing ACE-Step task polling, audio decoding, chunking, and playback tests
should remain unchanged. HTTP request-order, enrichment, prompt-content, and
vocal-payload assertions must be updated for the new `/format_input` call;
other existing payload assertions change only where the new vocal-mode fields
require it.

## Scope exclusions

- No ComfyUI integration.
- No new external LLM provider.
- No large static prompt matrix.
- No changes to audio stitching, continuity analysis, normalization, or
  playback.
- No separate prompt service or persistent prompt database.

## Acceptance criteria

1. A user can enter a prompt such as “late-night rainy room, slightly melodic”
   while retaining category selections.
2. The final prompt respects the user’s wording and adds category context
   without rigidly replacing it.
3. HTTP ACE-Step uses enriched captions when `/format_input` succeeds.
4. Music generation still works with the local prompt when enrichment fails or
   the ACE-Step service is unavailable.
5. Instrumental mode never depends on the LM guessing that vocals are unwanted.
6. Existing category-only and API-client workflows continue to work.
7. A multi-chunk session uses one plan lineage and keeps the same prompt and
   vocal mode across all chunks.
