from lofi_focus_tui.composition import create_blueprint
from lofi_focus_tui.domain import EnergyLevel, SessionRequest
from lofi_focus_tui.presets import expand_preset


def test_blueprint_carries_continuity_identity():
    plan = expand_preset(
        SessionRequest(
            preset="deep_work",
            duration_minutes=90,
            energy=EnergyLevel.STEADY,
            style_tags=["lofi", "neo_soul"],
            avoid_tags=["vocals"],
        )
    )

    blueprint = create_blueprint(plan)

    assert blueprint.session_id == plan.session_id
    assert blueprint.seed == plan.seed
    assert blueprint.tempo_bpm >= plan.tempo_range[0]
    assert "shared motif" in " ".join(blueprint.boundary_constraints)
