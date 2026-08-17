import pytest
from pydantic import ValidationError

from lofi_focus_tui.domain import EnergyLevel, SessionRequest
from lofi_focus_tui.options import FOCUS_OPTIONS, PRESET_OPTIONS, FocusValue
from lofi_focus_tui.presets import expand_preset


def test_session_request_defaults_to_auto_device():
    request = SessionRequest(
        focus="deep_work",
        preset="classic_lofi",
        duration_minutes=30,
        energy=EnergyLevel.STEADY,
        style_tags=["lofi", "neo_soul"],
        avoid_tags=["vocals"],
    )

    assert request.device_preference == "auto"
    assert request.duration_minutes == 30


def test_music_preset_defaults_to_deep_work_focus():
    request = SessionRequest(preset="classic_lofi", duration_minutes=30, energy="steady")

    assert request.focus == "deep_work"


def test_legacy_focus_preset_migrates_to_classic_lofi():
    request = SessionRequest(preset="reading", duration_minutes=30, energy="steady")

    assert request.focus == "reading"
    assert request.preset == "classic_lofi"


def test_explicit_focus_keeps_music_preset():
    request = SessionRequest(
        focus="coding",
        preset="classic_lofi",
        duration_minutes=30,
        energy="steady",
    )

    assert request.preset == "classic_lofi"


@pytest.mark.parametrize("music_preset", [value.value for value in PRESET_OPTIONS])
@pytest.mark.parametrize("focus_is_null", [False, True])
def test_omitted_or_null_focus_defaults_for_music_presets(music_preset, focus_is_null):
    data = {"preset": music_preset, "duration_minutes": 30, "energy": "steady"}
    if focus_is_null:
        data["focus"] = None

    request = SessionRequest(**data)

    assert request.focus == "deep_work"
    assert request.preset == music_preset


@pytest.mark.parametrize("legacy_focus", [value.value for value in FocusValue])
@pytest.mark.parametrize("focus_is_null", [False, True])
def test_omitted_or_null_focus_migrates_legacy_presets(legacy_focus, focus_is_null):
    data = {"preset": legacy_focus, "duration_minutes": 30, "energy": "steady"}
    if focus_is_null:
        data["focus"] = None

    request = SessionRequest(**data)

    assert request.focus == legacy_focus
    assert request.preset == "classic_lofi"


def test_explicit_focus_rejects_legacy_focus_preset():
    with pytest.raises(ValidationError):
        SessionRequest(
            focus="coding",
            preset="reading",
            duration_minutes=30,
            energy="steady",
        )


@pytest.mark.parametrize("field", ["focus", "preset"])
def test_unknown_focus_or_preset_is_rejected(field):
    data = {
        "focus": "deep_work",
        "preset": "classic_lofi",
        "duration_minutes": 30,
        "energy": "steady",
    }
    data[field] = "unknown"

    with pytest.raises(ValidationError):
        SessionRequest(**data)


def test_expand_deep_work_preset_has_focus_constraints():
    plan = expand_preset(
        SessionRequest(
            focus="deep_work",
            preset="classic_lofi",
            duration_minutes=30,
            energy=EnergyLevel.STEADY,
            style_tags=["lofi"],
            avoid_tags=["vocals"],
        )
    )

    assert plan.focus == "deep_work"
    assert plan.preset == "classic_lofi"
    assert plan.focus_constraints == FOCUS_OPTIONS["deep_work"].focus_constraints
    assert [phase.value for phase in plan.phases] == ["warmup", "steady_work", "cooldown"]
    assert "sudden drops" in plan.avoid_traits
    assert "stable tempo" in plan.continuity_requirements


def test_expand_preset_filters_legacy_vocal_avoid_tags_by_mode():
    request = SessionRequest(
        focus="deep_work",
        preset="classic_lofi",
        duration_minutes=30,
        energy=EnergyLevel.STEADY,
        style_tags=["neo_soul_tag"],
        avoid_tags=["vocals", "no_vocals", " NO VOCALS ", "keep_warm"],
        vocal_mode="vocals",
    )

    vocal_plan = expand_preset(request)
    instrumental_plan = expand_preset(request.model_copy(update={"vocal_mode": "instrumental"}))

    assert "vocals" not in vocal_plan.avoid_traits
    assert "no vocals" not in vocal_plan.avoid_traits
    assert "keep warm" in vocal_plan.avoid_traits
    assert "sharp transients" in vocal_plan.avoid_traits
    assert "sudden drops" in vocal_plan.avoid_traits
    assert "vocals" in instrumental_plan.avoid_traits
    assert "no vocals" in instrumental_plan.avoid_traits
    assert " NO VOCALS " in instrumental_plan.avoid_traits


def test_expand_preset_uses_request_seed_when_provided():
    plan = expand_preset(
        SessionRequest(
            focus="deep_work",
            preset="classic_lofi",
            duration_minutes=30,
            energy=EnergyLevel.STEADY,
            seed=12345,
        )
    )

    assert plan.seed == 12345


def test_expand_preset_uses_stable_default_seed():
    request = SessionRequest(
        focus="deep_work",
        preset="classic_lofi",
        duration_minutes=30,
        energy=EnergyLevel.STEADY,
        style_tags=["lofi", "neo_soul"],
    )

    assert expand_preset(request).seed == 623529743


@pytest.mark.parametrize("focus, option", list(FOCUS_OPTIONS.items()))
def test_expand_preset_uses_catalog_focus_constraints(focus, option):
    request = SessionRequest(
        focus=focus,
        preset="ambient_tape",
        duration_minutes=30,
        energy=EnergyLevel.STEADY,
    )

    plan = expand_preset(request)

    assert plan.focus == focus
    assert plan.preset == "ambient_tape"
    assert plan.focus_constraints == option.focus_constraints
