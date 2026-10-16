"""Listen to generated sessions the way a human hears them.

Prints a per-track listening profile — tempo feel, pulse depth, bed coverage,
event density, jump events — so "hiccupy" or "smooth" becomes a comparable
number across sessions and prompt changes.

Usage:
    python3 scripts/listen.py AUDIO.wav [MORE.wav ...]

Dependencies (install for the interpreter you run it with; the project venv
is pip-less, so the system python3 with `pip install --user librosa
soundfile numpy` is the easiest path):

    numpy, soundfile, librosa

What the metrics mean:
- tempo / beat_cv: pulse speed and steadiness (lower cv = steadier groove;
  tempo is often detected at double/half time — compare across tracks).
- p10/p90: how deep the dips between beat events go (0.03 ≈ -30 dB dips;
  low values sound sparse/gated, high values sound sustained/smooth).
- sustained%: share of time a background bed is audible (>30% of median
  loudness). Focus music should sit high.
- onset/s: perceptual busyness — events per second.
- jumps: loudness steps (>1.6x within 1s) with their times, for locating
  hiccups in the timeline.
"""

from __future__ import annotations

import sys
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

JUMP_RATIO = 1.6


def listening_profile(path: Path) -> dict[str, object]:
    audio, sample_rate = sf.read(path)
    mono = audio.mean(axis=1) if audio.ndim > 1 else audio
    y = mono.astype(np.float32)

    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
    median = float(np.median(rms))
    tempo, beats = librosa.beat.beat_track(y=y, sr=sample_rate)
    beat_ioi = np.diff(beats) / sample_rate if len(beats) > 2 else np.array([0.0])
    onsets = librosa.onset.onset_detect(y=y, sr=sample_rate, units="time", backtrack=False)
    p90, p10 = np.percentile(rms, [90, 10])

    hop_seconds = 512 / sample_rate
    window_seconds = 1.0
    step = max(1, int(window_seconds / hop_seconds))
    ratio = rms[:-step] / np.maximum(rms[step:], 1e-9)
    loud_rises = np.sort(ratio[ratio > JUMP_RATIO])[::-1]
    jump_times: list[float] = []
    for value in loud_rises:
        if len(jump_times) >= 5:
            break
        times = np.where(np.isclose(ratio, value))[0]
        t = round(float(times[0]) * hop_seconds, 1)
        if all(abs(t - seen) > 2 for seen in jump_times):
            jump_times.append(t)

    return {
        "file": path.parent.name[:20],
        "seconds": round(len(y) / sample_rate, 1),
        "tempo": round(float(np.atleast_1d(tempo)[0]), 1),
        "beat_cv": round(float(np.std(beat_ioi) / max(float(np.mean(beat_ioi)), 1e-9)), 3),
        "p10/p90": round(float(p10 / max(float(p90), 1e-9)), 3),
        "sustained%": round(100 * float(np.mean(rms > 0.3 * median)), 1),
        "onset/s": round(len(onsets) / (len(y) / sample_rate), 2),
        "top jumps (s)": jump_times,
    }


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    paths = [Path(arg) for arg in argv[1:]]
    profiles = [listening_profile(p) for p in paths]
    keys = list(profiles[0])
    for key in keys:
        values = "".join(f"{str(p[key]):>22}" for p in profiles)
        print(f"{key:<14}{values}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
