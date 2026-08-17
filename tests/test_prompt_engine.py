import pytest
from pydantic import ValidationError

from lofi_focus_tui.domain import CompositionBlueprint, EnergyLevel, SessionPlan, SessionRequest


def make_request(**overrides):
    values = {
        "preset": "classic_lofi",
        "duration_minutes": 30,
        "energy": EnergyLevel.STEADY,
    }
    values.update(overrides)
    return SessionRequest(**values)


def test_prompt_is_stripped_and_whitespace_only_becomes_empty():
    assert make_request(prompt="  rainy evening  ").prompt == "rainy evening"
    assert make_request(prompt=" \t\n ").prompt == ""


def test_prompt_accepts_normalized_unicode_lengths_up_to_512():
    assert len(make_request(prompt="e\u0301" * 511).prompt) == 1022
    assert len(make_request(prompt="e\u0301" * 512).prompt) == 1024


def test_prompt_rejects_normalized_unicode_longer_than_512():
    with pytest.raises(ValidationError):
        make_request(prompt="e\u0301" * 513)


def test_prompt_rejects_non_string_values():
    with pytest.raises(ValidationError):
        make_request(prompt=123)


def test_vocal_mode_is_stripped_and_lowercased():
    assert make_request(vocal_mode="  VoCaLs ").vocal_mode == "vocals"


def test_prompt_and_vocal_mode_default_values():
    request = make_request()
    assert request.prompt == ""
    assert request.vocal_mode == "instrumental"


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
