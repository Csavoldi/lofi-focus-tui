import pytest
from pydantic import ValidationError

from lofi_focus_tui.composition import create_blueprint, create_chunk_blueprint
from lofi_focus_tui.domain import CompositionBlueprint, EnergyLevel, SessionPlan, SessionRequest
from lofi_focus_tui.generation.prompt_engine import (
    MAX_PROMPT_LENGTH,
    append_prompt_parts,
    compose_enriched_prompt,
    compose_local_prompt,
)
from lofi_focus_tui.presets import expand_preset


def make_request(**overrides):
    values = {
        "preset": "classic_lofi",
        "duration_minutes": 30,
        "energy": EnergyLevel.STEADY,
    }
    values.update(overrides)
    return SessionRequest(**values)


@pytest.fixture
def golden_blueprint():
    return CompositionBlueprint(
        session_id="session",
        seed=1,
        prompt="rainy room",
        texture_layers=[" dusty tape ", "", "soft piano"],
        motif="motif",
        drum_feel="drums",
        bass_behavior="bass",
        energy=EnergyLevel.STEADY,
        focus="deep_work",
        focus_constraints=["minimal variation", " stable tempo ", "", "no abrupt changes"],
        tempo_bpm=80,
        key_center="D minor",
        meter="4/4",
        arrangement_sections=["warmup", "", "steady_work"],
        boundary_constraints=[" stable tempo ", ""],
        continuation_constraints=["carry motif"],
        harmonic_palette=[],
    )


def test_compose_local_prompt_has_canonical_golden_output(golden_blueprint):
    assert compose_local_prompt(golden_blueprint) == (
        "rainy room. Optional musical context: dusty tape, soft piano, motif, drums, "
        "bass, steady energy: balanced movement for ordinary focus work, deep_work focus: "
        "minimal variation, stable tempo, no abrupt changes. Technical direction: 80 BPM, "
        "D minor, meter 4/4, arrangement: warmup, steady_work, stable tempo, carry motif. "
        "Vocal direction: instrumental, no vocals"
    )


def test_compose_local_prompt_has_vocal_suffix(golden_blueprint):
    golden_blueprint.vocal_mode = "vocals"
    assert compose_local_prompt(golden_blueprint).endswith("Vocal direction: vocals allowed")


def test_compose_local_prompt_handles_category_only_and_empty_items(golden_blueprint):
    golden_blueprint.prompt = ""
    golden_blueprint.texture_layers = [" ", "rain", "", "  "]
    golden_blueprint.focus_constraints = []
    golden_blueprint.arrangement_sections = []
    golden_blueprint.boundary_constraints = []
    golden_blueprint.continuation_constraints = []

    result = compose_local_prompt(golden_blueprint)

    assert result.startswith("Optional musical context: rain, motif, drums, bass")
    assert "focus:" not in result
    assert "arrangement:" not in result
    assert "  " not in result


def test_compose_local_prompt_is_deterministic_and_preserves_user_wording(golden_blueprint):
    first = compose_local_prompt(golden_blueprint)
    second = compose_local_prompt(golden_blueprint)

    assert first == second
    assert first.startswith("rainy room. ")
    assert ". " in first


@pytest.mark.parametrize(
    ("parts", "expected"),
    [
        (["x" * 512, "tail"], "x" * 512),
        (["x" * 509, "tail"], "x" * 509 + ". t"),
        (["x" * 510, "tail"], "x" * 510),
    ],
)
def test_append_prompt_parts_obeys_512_character_boundary(parts, expected):
    result = append_prompt_parts(parts)

    assert result == expected
    assert len(result) <= MAX_PROMPT_LENGTH
    assert result == result.rstrip()
    assert not result.endswith(". ")


def test_compose_enriched_prompt_uses_stripped_caption_without_user_prompt(golden_blueprint):
    golden_blueprint.prompt = "  "

    assert compose_enriched_prompt(golden_blueprint, "  a generated caption  ") == (
        "a generated caption"
    )


def test_compose_enriched_prompt_appends_caption_to_user_prompt(golden_blueprint):
    golden_blueprint.prompt = "  user wording  "

    assert compose_enriched_prompt(golden_blueprint, "  generated caption  ") == (
        "user wording. generated caption"
    )


def test_compose_enriched_prompt_trims_whitespace_and_respects_caption_boundary(golden_blueprint):
    golden_blueprint.prompt = "  user wording  "

    result = compose_enriched_prompt(golden_blueprint, f"  {'caption' * 100}  ")

    assert result.startswith("user wording. caption")
    assert len(result) == MAX_PROMPT_LENGTH
    assert result == result.rstrip()
    assert not result.endswith(". ")


def test_compose_enriched_prompt_uses_full_trimmed_caption_at_boundary(golden_blueprint):
    golden_blueprint.prompt = "  "
    caption = f"  {'x' * MAX_PROMPT_LENGTH}  "

    assert compose_enriched_prompt(golden_blueprint, caption) == "x" * MAX_PROMPT_LENGTH


def test_prompt_is_stripped_and_whitespace_only_becomes_empty():
    assert make_request(prompt="  rainy evening  ").prompt == "rainy evening"
    assert make_request(prompt=" \t\n ").prompt == ""


def test_prompt_accepts_raw_unicode_lengths_up_to_512():
    assert len(make_request(prompt="é" * 511).prompt) == 511
    assert len(make_request(prompt="é" * 512).prompt) == 512


def test_prompt_rejects_raw_unicode_longer_than_512():
    with pytest.raises(ValidationError):
        make_request(prompt="é" * 513)


def test_prompt_rejects_decomposed_value_over_raw_length_limit():
    with pytest.raises(ValidationError):
        make_request(prompt=("e" + chr(0x301)) * 257)


def test_prompt_rejects_non_string_values():
    with pytest.raises(ValidationError):
        make_request(prompt=123)


def test_vocal_mode_is_stripped_and_lowercased():
    assert make_request(vocal_mode="  VoCaLs ").vocal_mode == "vocals"


def test_prompt_and_vocal_mode_default_values():
    request = make_request()
    assert request.prompt == ""
    assert request.vocal_mode == "instrumental"


def test_prompt_and_vocal_mode_propagate_through_blueprints():
    plan = expand_preset(
        make_request(prompt="late-night rainy room", vocal_mode="vocals", seed=7)
    )
    blueprint = create_blueprint(plan)
    chunk = create_chunk_blueprint(plan, chunk_index=0, chunk_count=1)

    for value in (plan, blueprint, chunk):
        assert value.prompt == "late-night rainy room"
        assert value.vocal_mode == "vocals"


@pytest.mark.parametrize("value", ["", "  ", 123])
def test_vocal_mode_rejects_blank_and_non_string_values(value):
    with pytest.raises(ValidationError):
        make_request(vocal_mode=value)


def test_session_plan_defaults_new_fields_when_validating_old_payload():
    plan = SessionPlan(
        session_id="session",
        focus="deep_work",
        seed=1,
        preset="classic_lofi",
        duration_minutes=30,
        energy=EnergyLevel.STEADY,
        phases=[],
        tempo_range=(72, 88),
        key_center="minor pentatonic",
        style_traits=[],
        avoid_traits=[],
        focus_constraints=[],
        continuity_requirements=[],
    )
    payload = plan.model_dump()
    payload.pop("prompt")
    payload.pop("vocal_mode")
    restored = SessionPlan.model_validate(payload)
    assert restored.prompt == ""
    assert restored.vocal_mode == "instrumental"
    assert SessionPlan.model_validate({**payload, "vocal_mode": "  VoCaLs "}).vocal_mode == "vocals"


def test_composition_blueprint_defaults_new_fields_when_validating_old_payload():
    blueprint = CompositionBlueprint(
        session_id="session",
        seed=1,
        focus="deep_work",
        focus_constraints=[],
        tempo_bpm=80,
        key_center="minor pentatonic",
        harmonic_palette=[],
        motif="motif",
        drum_feel="laid back",
        bass_behavior="steady",
        texture_layers=[],
        arrangement_sections=[],
        boundary_constraints=[],
    )
    payload = blueprint.model_dump()
    payload.pop("prompt")
    payload.pop("vocal_mode")
    payload.pop("energy")
    restored = CompositionBlueprint.model_validate(payload)
    assert restored.prompt == ""
    assert restored.vocal_mode == "instrumental"
    assert restored.energy == EnergyLevel.STEADY
    assert CompositionBlueprint.model_validate(
        {**payload, "vocal_mode": "  VoCaLs "}
    ).vocal_mode == "vocals"
