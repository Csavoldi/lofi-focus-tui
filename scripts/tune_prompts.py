"""Offline prompt tuner: explore prompt variants and rank them by quality.

Uses the same refiner engine the app uses in-session, but runs standalone
against the live backend so preset/option defaults can be tuned by
measurement instead of by hand. For each requested (preset, energy) pair it
generates takes, scores each through AudioBox Aesthetics + the envelope
metrics, applies escalating adjustments between attempts, and prints a
ranked table with the winning caption adjustments.

Run with the project venv python (it has audiobox_aesthetics installed):

    .venv/bin/python scripts/tune_prompts.py --preset classic_lofi --energy low
    .venv/bin/python scripts/tune_prompts.py --all --attempts 2

Results are appended to .uat/prompt-tuning/results.jsonl.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lofi_focus_tui.composition import create_blueprint  # noqa: E402
from lofi_focus_tui.config import AppConfig, load_config  # noqa: E402
from lofi_focus_tui.domain import EnergyLevel, SessionRequest  # noqa: E402
from lofi_focus_tui.generation.prompt_engine import compose_local_prompt  # noqa: E402
from lofi_focus_tui.generation.refiner import PromptRefiner, RefinementPolicy  # noqa: E402
from lofi_focus_tui.generation.settings import GenerationSettings  # noqa: E402
from lofi_focus_tui.options import ENERGY_OPTIONS, PRESET_OPTIONS  # noqa: E402
from lofi_focus_tui.presets import expand_preset  # noqa: E402
from lofi_focus_tui.quality import AudioboxAnalyzer, build_report  # noqa: E402
from lofi_focus_tui.runtime import build_model  # noqa: E402


def tune_one(config: AppConfig, analyzer: AudioboxAnalyzer, preset: str, energy: str,
             attempts: int, duration_seconds: int) -> dict:
    model = build_model(config)
    request = SessionRequest(
        focus="deep_work",
        preset=preset,
        duration_minutes=max(5, duration_seconds // 60),  # domain requires >= 5
        energy=EnergyLevel(energy),
        style_tags=[],
    )
    plan = expand_preset(request)
    blueprint = create_blueprint(plan)
    settings = GenerationSettings(seed=blueprint.seed)
    policy = RefinementPolicy(max_attempts=attempts)
    refiner = PromptRefiner(policy)

    results = []
    last_report = None
    for attempt in range(1, attempts + 1):
        if attempt == 1:
            candidate = blueprint
            seed = blueprint.seed
        else:
            seed = refiner.next_seed(blueprint.seed, attempt - 1)
            candidate = blueprint.model_copy(
                update={
                    "quality_adjustments": refiner.adjustments_for(last_report),
                    "seed": seed,
                }
            )
        print(f"  generating {preset}/{energy} take {attempt}/{attempts} "
              f"(adjustments: {candidate.quality_adjustments or 'none'})…", flush=True)
        result = model.generate(candidate, duration_seconds=duration_seconds,
                                settings=settings.model_copy(update={"seed": seed}))
        scores = analyzer.scores_for(result.audio, result.sample_rate)
        report = build_report(result.audio, result.sample_rate, scores)
        entry = {
            "attempt": attempt,
            "seed": seed,
            "caption": compose_local_prompt(candidate),
            "adjustments": list(candidate.quality_adjustments),
            "report": report.to_dict(),
            "rank": round(policy.rank(report), 2),
            "accepted": policy.accepts(report),
        }
        results.append(entry)
        last_report = report
        if policy.accepts(report):
            break
    return {"preset": preset, "energy": energy, "takes": results,
            "best": max(results, key=lambda t: t["rank"])}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", choices=[p.value for p in PRESET_OPTIONS])
    parser.add_argument("--energy", choices=[e.value for e in ENERGY_OPTIONS])
    parser.add_argument("--all", action="store_true", help="tune every preset at steady energy")
    parser.add_argument("--attempts", type=int, default=2)
    parser.add_argument("--duration", type=int, default=60, help="seconds per take")
    args = parser.parse_args(argv[1:])

    config: AppConfig = load_config()
    analyzer = AudioboxAnalyzer(excerpt_seconds=config.quality.excerpt_seconds)
    jobs: list[tuple[str, str]] = []
    if args.all:
        jobs = [(preset.value, "steady") for preset in PRESET_OPTIONS]
    else:
        if not args.preset or not args.energy:
            parser.error("provide --preset and --energy, or --all")
        jobs = [(args.preset, args.energy)]

    out_dir = Path(".uat") / "prompt-tuning"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "results.jsonl"

    for preset, energy in jobs:
        print(f"\n=== {preset} / {energy} ===", flush=True)
        outcome = tune_one(config, analyzer, preset, energy, args.attempts, args.duration)
        with out_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(outcome) + "\n")
        best = outcome["best"]
        scores = best["report"]["scores"]
        print(
            f"  best: rank {best['rank']} · CE {scores.get('CE')} · CU {scores.get('CU')} "
            f"· PQ {scores.get('PQ')} · dip {best['report'].get('dip_ratio'):.3f}\n"
            f"  adjustments that helped: {best['adjustments'] or 'none needed'}",
            flush=True,
        )
    print(f"\nresults appended to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
