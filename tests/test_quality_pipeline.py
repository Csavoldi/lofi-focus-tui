import json
from pathlib import Path

import numpy as np

from lofi_focus_tui.audio.output import OutputManager
from lofi_focus_tui.backend.session_manager import SessionManager
from lofi_focus_tui.domain import EnergyLevel, SessionRequest
from lofi_focus_tui.generation.base import GenerationResult


class BlueprintCapturingModel:
    name = "capturing"
    sample_rate = 1000

    def __init__(self) -> None:
        self.blueprints = []

    def generate(self, blueprint, duration_seconds, settings=None):
        self.blueprints.append(blueprint)
        return GenerationResult(
            audio=np.full(duration_seconds * self.sample_rate, 0.05, dtype=np.float32),
            sample_rate=self.sample_rate,
            duration_seconds=duration_seconds,
            metadata={
                "session_id": blueprint.session_id,
                "backend": self.name,
                "output_path": f"{blueprint.session_id}.wav",
            },
        )


class HighScoresAnalyzer:
    """Stands in for AudioBox: strong scores, so no adjustments are suggested."""

    def scores_for(self, audio, sample_rate):
        from lofi_focus_tui.quality import QualityScores

        return QualityScores(ce=9.0, cu=9.0, pc=9.0, pq=9.0)


class LowScoresAnalyzer:
    def scores_for(self, audio, sample_rate):
        from lofi_focus_tui.quality import QualityScores

        return QualityScores(ce=4.0, cu=9.0, pc=9.0, pq=4.0)


def make_request():
    return SessionRequest(
        focus="deep_work",
        preset="classic_lofi",
        duration_minutes=5,
        energy=EnergyLevel.STEADY,
        style_tags=["lofi"],
    )


def test_quality_report_persists_and_adjusts_next_prompt(tmp_path):
    model = BlueprintCapturingModel()
    refinement = tmp_path / "refinement.json"
    manager = SessionManager(
        model=model,
        playback=None,
        output_manager=OutputManager(tmp_path / "outputs"),
        quality_analyzer=LowScoresAnalyzer(),
        refinement_path=refinement,
        render_seconds_limit=1,
    )

    manager.start_session(make_request())
    first = manager.wait_for_active_task()
    assert first.state == "playing"

    state = json.loads(refinement.read_text(encoding="utf-8"))
    assert state["session_id"] == first.active_session_id
    assert "memorable melodic hook" in " ".join(state["adjustments"])
    assert state["report"]["scores"]["PQ"] == 4.0
    metadata = json.loads(Path(first.output_path).parent.joinpath("metadata.json").read_text())
    assert metadata["quality"]["scores"]["PQ"] == 4.0

    manager.start_session(make_request())
    second = manager.wait_for_active_task()
    assert second.state == "playing"

    assert model.blueprints[0].quality_adjustments == []
    assert "memorable melodic hook" in " ".join(model.blueprints[-1].quality_adjustments)
    assert "clean, polished, well-balanced production" in " ".join(
        model.blueprints[-1].quality_adjustments
    )


def test_good_scores_keep_next_prompt_unadjusted(tmp_path):
    model = BlueprintCapturingModel()
    refinement = tmp_path / "refinement.json"
    manager = SessionManager(
        model=model,
        output_manager=OutputManager(tmp_path / "outputs"),
        quality_analyzer=HighScoresAnalyzer(),
        refinement_path=refinement,
        render_seconds_limit=1,
    )

    manager.start_session(make_request())
    manager.wait_for_active_task()

    state = json.loads(refinement.read_text(encoding="utf-8"))
    assert state["adjustments"] == []


def test_quality_adjustments_land_in_composed_caption():
    from lofi_focus_tui.composition import create_blueprint
    from lofi_focus_tui.generation.prompt_engine import compose_local_prompt
    from lofi_focus_tui.presets import expand_preset

    plan = expand_preset(make_request())
    base = create_blueprint(plan)
    adjusted = base.model_copy(
        update={"quality_adjustments": ["memorable melodic hook with richer harmonic movement"]}
    )

    caption = compose_local_prompt(adjusted)

    assert "memorable melodic hook with richer harmonic movement" in caption
    assert "memorable melodic hook" not in compose_local_prompt(base)


class ImprovingAnalyzer:
    """Scores the first take low, every later take high — forces one retry."""

    def __init__(self) -> None:
        self.calls = 0

    def scores_for(self, audio, sample_rate):
        from lofi_focus_tui.quality import QualityScores

        self.calls += 1
        if self.calls == 1:
            return QualityScores(ce=4.0, cu=9.0, pc=9.0, pq=4.0)
        return QualityScores(ce=9.0, cu=9.0, pc=9.0, pq=9.0)


def test_auto_refinement_regenerates_and_delivers_the_better_take(tmp_path):
    from lofi_focus_tui.generation.refiner import RefinementPolicy

    model = BlueprintCapturingModel()
    analyzer = ImprovingAnalyzer()
    manager = SessionManager(
        model=model,
        output_manager=OutputManager(tmp_path / "outputs"),
        quality_analyzer=analyzer,
        refinement_path=tmp_path / "refinement.json",
        refinement_policy=RefinementPolicy(max_attempts=2),
        render_seconds_limit=1,
    )

    manager.start_session(make_request())
    final = manager.wait_for_active_task()

    assert final.state == "playing"
    assert len(model.blueprints) == 2  # first take rejected, second generated
    assert model.blueprints[0].quality_adjustments == []
    assert "memorable melodic hook" in " ".join(model.blueprints[1].quality_adjustments)
    assert model.blueprints[1].seed != model.blueprints[0].seed

    metadata = json.loads(Path(final.output_path).parent.joinpath("metadata.json").read_text())
    attempts = metadata["quality"]["refinement"]
    assert [entry["attempt"] for entry in attempts] == [1, 2]
    assert attempts[1]["report"]["scores"]["PQ"] == 9.0
    assert metadata["quality"]["scores"]["PQ"] == 9.0  # delivered take is the best one


def test_auto_refinement_keeps_best_take_when_all_are_weak(tmp_path):
    from lofi_focus_tui.generation.refiner import RefinementPolicy
    from lofi_focus_tui.quality import QualityScores

    model = BlueprintCapturingModel()

    class WeakAnalyzer:
        def __init__(self) -> None:
            self.calls = 0

        def scores_for(self, audio, sample_rate):
            self.calls += 1
            # second take scores slightly better; both below target
            pq = 4.0 if self.calls == 1 else 5.5
            return QualityScores(ce=6.0, cu=9.0, pc=9.0, pq=pq)

    manager = SessionManager(
        model=model,
        output_manager=OutputManager(tmp_path / "outputs"),
        quality_analyzer=WeakAnalyzer(),
        refinement_path=tmp_path / "refinement.json",
        refinement_policy=RefinementPolicy(max_attempts=2),
        render_seconds_limit=1,
    )

    manager.start_session(make_request())
    final = manager.wait_for_active_task()

    assert final.state == "playing"
    metadata = json.loads(Path(final.output_path).parent.joinpath("metadata.json").read_text())
    assert metadata["quality"]["scores"]["PQ"] == 5.5


def test_auto_refinement_disabled_without_analyzer(tmp_path):
    from lofi_focus_tui.generation.refiner import RefinementPolicy

    model = BlueprintCapturingModel()
    manager = SessionManager(
        model=model,
        output_manager=OutputManager(tmp_path / "outputs"),
        quality_analyzer=None,
        refinement_policy=RefinementPolicy(max_attempts=2),
        render_seconds_limit=1,
    )

    manager.start_session(make_request())
    final = manager.wait_for_active_task()

    assert final.state == "playing"
    assert len(model.blueprints) == 1
