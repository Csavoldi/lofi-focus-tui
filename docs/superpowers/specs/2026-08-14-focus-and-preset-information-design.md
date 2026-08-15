# Focus and Music Preset Information

## Status

Approved design for implementation on the `dev` branch.

## Goal

Make focus and music preset independent user choices. Explain the available focus,
preset, energy, and style options in the main TUI and in a dedicated help view.

## Current problem

The TUI currently uses one `preset` value for both the user's focus goal and the session
recipe. The main screen consequently renders duplicate `focus` and `preset` values. The
backend planner also stores only `preset`, so the two concepts cannot vary independently.

## User-facing model

```text
focus   = what the user is doing
preset  = the musical recipe
energy  = intensity and movement
style   = texture modifiers
```

Focus options:

- `deep_work`: sustained concentration and low distraction.
- `reading`: spacious, calm, gentle pulse.
- `coding`: forward momentum and a steady groove.
- `wind_down`: soft, slow decompression.

Music preset options:

- `classic_lofi`: dusty keys, swung drums, round bass.
- `neo_soul`: warm chords, pocketed rhythm, mellow bass.
- `ambient_tape`: sparse pulse, wide pads, tape haze.
- `jazz_vinyl`: brushed drums, jazz harmony, vinyl texture.

Energy options:

- `low`: soft movement and a restrained pulse.
- `steady`: balanced movement for ordinary focus work.
- `high`: more rhythmic momentum while remaining non-distracting.

Style options:

- `lofi, neo_soul`: warm, dusty, chord-forward texture.
- `ambient, tape`: spacious, hazy, slowly moving texture.
- `rainy, mellow`: soft atmosphere and subdued detail.
- `jazz, vinyl`: brushed, tactile, lightly swinging texture.

## Data flow

- Add a `focus` field to `SessionRequest`, defaulting to `deep_work` for compatibility
  with existing API clients.
- Keep `preset` as the music recipe and update its available values.
- Normalize legacy requests in a pre-validation step, before the `focus` default is
  applied: when the `focus` key is absent or its value is `null` and
  `preset` is one of the old focus values (`deep_work`, `reading`, `coding`, or
  `wind_down`), move that value to `focus` and use `classic_lofi` as the music preset.
  When `focus` is absent or explicitly `null` and `preset` is already a valid music preset, use
  `deep_work` as the focus. When `focus` is a non-null explicit value, validate both fields
  as their new independent values and do not apply legacy migration.
- Carry `focus` through `SessionPlan` and composition planning.
- Centralize enums, option values, and descriptions in one shared catalog so the backend
  and TUI do not maintain separate catalogs. Enum validation at the Pydantic request
  boundary rejects unknown new values.
- Use focus to select arrangement constraints:
  `deep_work` favors minimal variation, `reading` favors space and light percussion,
  `coding` favors a consistent forward pulse, and `wind_down` favors low-density texture
  and soft transitions.
- Use preset to select the musical recipe:
  `classic_lofi` uses dusty keys and a swung backbeat, `neo_soul` uses warm chords and
  pocketed rhythm, `ambient_tape` uses sparse pads and tape haze, and `jazz_vinyl` uses
  brushed rhythm and jazz harmony.
- Keep energy as the intensity control and style tags as additional texture modifiers.

Invalid focus or preset values must be rejected at the request boundary with a normal
validation error. Existing history records without `focus` use this migration table:

| Legacy `preset` | New `focus` | New `preset` |
|---|---|---|
| `deep_work` | `deep_work` | `classic_lofi` |
| `reading` | `reading` | `classic_lofi` |
| `coding` | `coding` | `classic_lofi` |
| `wind_down` | `wind_down` | `classic_lofi` |
| valid music preset | `deep_work` | unchanged |
| unknown value | `deep_work` | `classic_lofi`, with `legacy_preset:<old value>` appended to `tags` |

New history records and generated metadata persist both `focus` and `preset`. History
records that already contain both fields are not migrated.

Requests with an omitted `focus` and a valid music preset default to `deep_work`. Requests
with an omitted `focus` and a legacy focus-valued `preset` use the matching migrated focus.
Requests with an explicit `focus` and a legacy focus-valued `preset` fail validation rather
than silently changing either explicit value.

## Planning contract

The independent fields map to concrete planning outputs as follows:

| Input | `SessionPlan` | `CompositionBlueprint` | Metadata |
|---|---|---|---|
| focus | new `focus` and `focus_constraints` fields; existing `phases` remain `warmup`, `steady_work`, `cooldown` | `focus` plus arrangement sections and boundary constraints | `request.focus`, `plan.focus` |
| preset | music recipe name | motif, drum feel, and bass behavior | `request.preset`, `plan.preset` |
| energy | tempo range | selected tempo within that range | `request.energy`, `plan.energy` |
| style | style traits | texture layers | `request.style_tags`, `plan.style_traits` |

Focus constraints must be deterministic. The existing `SessionPlan.phases` values remain
unchanged; the focus-specific arrangement labels live in
`CompositionBlueprint.arrangement_sections`:

| Focus | `focus_constraints` | Arrangement sections | Boundary/avoid traits |
|---|---|---|---|
| `deep_work` | `list[str]`: `minimal variation`, `stable tempo`, `no abrupt changes` | `warmup`, `steady_work`, `cooldown` | same three constraints |
| `reading` | `list[str]`: `spacious pacing`, `light percussion`, `no abrupt changes` | `warmup`, `reading`, `cooldown` | same three constraints |
| `coding` | `list[str]`: `consistent forward pulse`, `stable groove`, `no abrupt changes` | `warmup`, `steady_work`, `momentum` | same three constraints |
| `wind_down` | `list[str]`: `low density`, `soft transitions`, `no abrupt changes` | `settle`, `unwind`, `cooldown` | same three constraints |

Preset traits must be deterministic:

| Preset | Motif | Drum feel | Bass behavior |
|---|---|---|---|
| `classic_lofi` | dusty electric-piano figure | soft swung lofi backbeat | round sustained bass |
| `neo_soul` | warm Rhodes-style chord figure | pocketed neo-soul groove | mellow melodic bass |
| `ambient_tape` | sparse washed pad motif | minimal soft pulse | long sustained low movement |
| `jazz_vinyl` | jazzy electric-piano motif | brushed light swing | warm upright-style movement |

The selected focus row and preset row combine directly; there is no hidden Cartesian
lookup table. Energy selects tempo within its existing intensity rules, and `style_tags`
are appended as modifiers.

The prompt builder must include the blueprint focus, arrangement sections, and boundary
constraints in the generation prompt. Focus therefore affects generated audio as well as
saved plan and blueprint metadata.

## TUI behavior

The initial TUI values are `focus=deep_work` and `preset=classic_lofi`. The main screen
shows separate values and short descriptions for focus, preset, energy, and style.
Existing duration, energy, and style bindings remain stable; the new key
bindings are:

```text
1  cycle focus
p  cycle music preset
2  cycle duration
3  cycle energy
4  cycle style
h  open the option guide
```

The option guide lists every focus, preset, energy, and style choice with its description.
It opens with `h` and closes with `Escape` or `h`. The existing start, pause/resume, stop,
refresh, duration, and quit controls remain available.

## Testing

- Verify omitted-focus requests with a valid music preset default to `deep_work`.
- Verify legacy requests that use an old focus value as `preset` normalize to that focus
  plus `classic_lofi`.
- Verify omitted and `null` focus follow the same migration path, while explicit non-null
  focus values do not migrate legacy presets.
- Verify explicit-focus requests with a legacy focus-valued `preset` fail validation.
- Verify invalid focus and music preset values return request-validation errors.
- Verify focus and preset are preserved independently through planning.
- Verify each focus maps to its documented arrangement constraints and each music preset
  maps to its documented recipe traits.
- Verify different focus/preset combinations produce the expected plan and blueprint
  traits without changing duration or energy behavior.
- Verify the TUI renders separate values, keeps duration on `2`, cycles the new fields,
  and opens/closes the option guide.
- Verify the shared catalog contains every selectable value and description.
- Verify legacy history records follow the migration table, including exact
  `legacy_preset:<old value>` tags for unknown values, and new records persist both focus
  and preset.
- Verify the README and usage guide show the updated key bindings.

`SessionRecord` gains `focus: str = "deep_work"`. History migration runs in a
pre-validation model step when each record is read. It does not require a separate
migration command or rewrite the history file immediately; a later normal history write
persists the normalized record. Migration is idempotent: if a record already has both
`focus` and a valid music `preset`, its tags are left unchanged, and an existing
`legacy_preset:<old value>` tag is never appended twice.

## Non-goals

- No change to the static screenshot/theme proof of concept.
- No new duration, playback, or ACE-Step server behavior.
- No user-configurable custom catalogs in this iteration.
