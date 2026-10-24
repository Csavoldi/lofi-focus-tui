# The Quality Loop — User Guide

The quality loop is a built-in producer that listens to every session you
generate, scores it the way a human rater would, and quietly adjusts the next
session's prompt to ask for whatever the last take lacked. You do not have to
configure anything to benefit from it — it runs after each generation while
your music is already playing.

```
generate ──► play ──► score (AudioBox Aesthetics + envelope measurement)
   ▲                                              │
   └──── next prompt carries the adjustments ◄────┘  (refinement.json)
```

## Quick start

The loop ships enabled in this repository's configs:

```toml
[quality]
backend = "audiobox"
excerpt_seconds = 60.0
auto_refine = true
max_refinement_attempts = 2
```

Start the app as usual (`lofi`), generate a session, and watch the status
line once playback begins:

```
state: playing
message: playing · quality PQ 8.2
```

That is the whole day-to-day interaction. The rest of this guide explains
what the numbers mean, where the reports live, and how to take manual control
when you want it.

## Automatic refinement — the part you never see

With `auto_refine = true` (the default), weak takes are regenerated *before*
you hear them:

1. The first take is generated and scored immediately.
2. If it misses the quality targets (CE/CU/PQ below 6.0, or hiccupy dips),
   the app shows `refining take 2/2 · last PQ 5.4`, regenerates with an
   adjusted prompt (escalated wording for whatever failed, plus a fresh seed),
   and scores the new take.
3. The **best** take across attempts is the one saved, played, and exported —
   you never receive a take the producer already rejected.

Every attempt (seed, caption adjustments, scores) is recorded in the
session's `metadata.json` under `quality.refinement`. When the first take is
already good — the common case — refinement costs nothing extra.

`max_refinement_attempts` is the total number of takes per session
(`2` = one retry; up to `4`). Each retry is a full generation, so long
multi-chunk sessions multiply that cost — lower it or set `auto_refine =
false` if you prefer raw speed. With refinement disabled, the loop falls
back to next-session adjustment (see below).

## Reading the scores

AudioBox Aesthetics rates a 60-second excerpt from the middle of your session
on the same 1–10 scale its human raters used:

| Score | Meaning | Low score triggers |
|---|---|---|
| **PQ** — Production Quality | How clean and well-produced the audio sounds | "clean, polished, well-balanced production" |
| **CE** — Content Enjoyment | How enjoyable the musical content is | "memorable melodic hook with richer harmonic movement" |
| **CU** — Content Usefulness | How well it serves its purpose (here: focus music) | "steady, unobtrusive background character suited for focus" |
| **PC** — Production Complexity | How dense/complex the arrangement is | *(informational only — lo-fi is intentionally simple, so mid-range values are fine)* |

Alongside the model scores, two loudness-envelope measurements run on the
full track (no extra dependencies, always computed):

- **`dip_ratio`** — how deep the quiet moments between beat events go
  (p10/p90 of the loudness envelope). `0.03` ≈ the "hiccupy" era; `0.10` is
  smooth. Below `0.03` the loop asks for a "dense continuous pad bed".
- **`sustained_fraction`** — the share of time an audible background bed
  exists. Below `0.70` the loop asks for "constant sustained background
  texture under the beat".

Adjustment rules fire when CE, CU, or PQ fall below **6.0**, or when the
envelope measurements cross the thresholds above. At most three phrases are
added, so captions stay short. A take with everything above threshold adjusts
nothing — the loop goes quiet.

When the same aspect fails a *second* time, its wording escalates — e.g.
"memorable melodic hook…" becomes "strong singable melodic hook carried
through every section" — so retries push harder instead of repeating
themselves.

## Tuning the presets without doing the work yourself

`scripts/tune_prompts.py` runs the same refinement engine offline against
the live backend, exploring prompt variants per preset and energy and
ranking them by measured quality:

```bash
.venv/bin/python scripts/tune_prompts.py --preset classic_lofi --energy low
.venv/bin/python scripts/tune_prompts.py --all --attempts 2 --duration 60
```

It prints the best take's scores and which caption adjustments helped, and
appends full details (every attempt's caption and report) to
`.uat/prompt-tuning/results.jsonl` — the evidence base for tuning preset
wording and defaults by measurement.

## Where everything is saved

- **Per session:** the full report is written into the session's
  `metadata.json` under the `"quality"` key — scores, envelope measurements,
  and the suggestions that were derived. It travels with the export when you
  press `e`.
- **The refinement state:** `~/.cache/lofi-focus-tui/refinement.json` holds
  the *latest* report and the adjustment phrases the **next** session will
  carry. One file, always current; delete it to start fresh.

Example `refinement.json` after a weak take:

```json
{
  "session_id": "c864a6d4-…",
  "adjustments": [
    "memorable melodic hook with richer harmonic movement",
    "clean, polished, well-balanced production"
  ],
  "report": {
    "scores": {"CE": 4.1, "CU": 7.8, "PC": 5.2, "PQ": 5.6},
    "dip_ratio": 0.041,
    "sustained_fraction": 0.82,
    "suggestions": ["memorable melodic hook with richer harmonic movement",
                     "clean, polished, well-balanced production"]
  }
}
```

The adjustment phrases are woven into the next session's caption right after
the tempo/smoothness phrasing — check any session's own record in
`metadata.json` → `blueprint.quality_adjustments` to see exactly what was
applied.

## Digging deeper with `scripts/listen.py`

For a fuller producer's ear on any saved session (yours or an export), use
the listening profiler with your **system** python (it needs librosa from the
user site, not the app venv):

```bash
python3 scripts/listen.py ~/.cache/lofi-focus-tui/outputs/<session>/audio.wav
```

```
file            c233b57d-2aba-480f-8
seconds                        275.7
tempo                          148.0
beat_cv                        0.044
p10/p90                        0.027
sustained%                      80.4
onset/s                         3.38
top jumps (s) [266.9, 232.1, 225.5, 238.5, 235.3]
```

- `tempo / beat_cv`: pulse speed and steadiness (lower cv = steadier groove;
  tempo often reads at double-time — compare across tracks, not to the BPM in
  metadata).
- `p10/p90` and `sustained%`: the same dip/bed measurements the loop uses.
- `onset/s`: busyness — events per second.
- `top jumps (s)`: timestamps of the sharpest loudness steps, for scrubbing
  straight to the rough spots.

Pass several files to compare takes side by side — this is the A/B workflow:

```bash
python3 scripts/listen.py ~/Music/lofi-focus-tui/session_A/audio.wav \
                           ~/Music/lofi-focus-tui/session_B/audio.wav
```

## Manual control

**Force specific adjustments.** Write the phrases you want into the
refinement state and the next session will carry them:

```bash
python3 - <<'EOF'
import json
state = {
    "session_id": "manual",
    "adjustments": ["memorable melodic hook with richer harmonic movement"],
    "report": {"scores": {"CE": 4.0, "CU": 8.0, "PC": 5.0, "PQ": 8.0},
               "dip_ratio": 0.05, "sustained_fraction": 0.8, "suggestions": []},
}
path = "~/.cache/lofi-focus-tui/refinement.json"
open(path.replace("~", __import__("os").path.expanduser("~")), "w").write(
    json.dumps(state, indent=2))
EOF
```

The file is overwritten by the next completed session's report, so manual
seeding affects exactly one generation.

**Reset the loop.** `rm ~/.cache/lofi-focus-tui/refinement.json` — the next
session starts with an unadjusted prompt.

**Turn off automatic refinement** (keep next-session adjustment only). Set
`auto_refine = false` in the `[quality]` section.

**Disable scoring.** Set `backend = "none"` in the `[quality]` section (both
`config.toml` and `~/.config/lofi-focus-tui/config.toml` are checked, in that
order). Sessions still record the envelope measurements; only the AudioBox
scores and the adjustment rules go away.

## Requirements and troubleshooting

| Symptom | Cause / fix |
|---|---|
| `metadata.json` has `"quality"` but scores are `null` | `audiobox_aesthetics` is missing or failed to import. It is installed in this repo's venv (`uv pip install --python .venv/bin/python audiobox_aesthetics requests`). With the backend on but the package absent, reports degrade to envelope-only — sessions never fail because of analysis. |
| Status line never shows a PQ value | Same as above, or `backend = "none"` in the active config. Check which config file applies: the app reads `config.toml` from the launch directory first, then `~/.config/lofi-focus-tui/config.toml`. |
| First generation feels slower to reach "playing · quality" | The scoring model loads once per app run (~7s) and scores a 60s excerpt (~4s on CPU). It runs after playback starts, so music is never delayed. |
| Scores present but no adjustments ever fire | The takes are genuinely scoring above threshold (CE/CU/PQ ≥ 6.0, dip ≥ 0.03, sustained ≥ 0.70) — the loop is working and satisfied. |
| Want scoring on another machine | The analyzer runs in-process on the app machine (CPU is fine); no GPU or server-side change is needed. |

The scoring model is [Meta's AudioBox
Aesthetics](https://github.com/facebookresearch/audiobox-aesthetics) — human
rater-trained, predicting how a person would rate the audio, not ground truth.
Use it as a compass for iterating prompts and presets, and your ears as the
final judge.
