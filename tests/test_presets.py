from lofi_focus_tui.domain import EnergyLevel, SessionRequest
from lofi_focus_tui.presets import expand_preset


def test_session_request_defaults_to_auto_device():
    request = SessionRequest(
        preset="deep_work",
        duration_minutes=90,
        energy=EnergyLevel.STEADY,
        style_tags=["lofi", "neo_soul"],
        avoid_tags=["vocals"],
    )

    assert request.device_preference == "auto"
    assert request.duration_minutes == 90


def test_expand_deep_work_preset_has_focus_constraints():
    plan = expand_preset(
        SessionRequest(
            preset="deep_work",
            duration_minutes=90,
            energy=EnergyLevel.STEADY,
            style_tags=["lofi"],
            avoid_tags=["vocals"],
        )
    )

    assert plan.preset == "deep_work"
    assert [phase.value for phase in plan.phases] == ["warmup", "steady_work", "cooldown"]
    assert "sudden drops" in plan.avoid_traits
    assert "stable tempo" in plan.continuity_requirements
