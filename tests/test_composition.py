from lofi_focus_tui.composition import create_blueprint, create_chunk_blueprint
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


def test_chunk_blueprints_preserve_identity_with_chunk_context():
    plan = expand_preset(
        SessionRequest(
            preset="deep_work",
            duration_minutes=90,
            energy=EnergyLevel.STEADY,
            style_tags=["lofi", "neo_soul"],
            avoid_tags=["vocals"],
        )
    )

    base = create_blueprint(plan)
    first = create_chunk_blueprint(plan, chunk_index=0, chunk_count=3)
    second = create_chunk_blueprint(plan, chunk_index=1, chunk_count=3)

    assert first.session_id == base.session_id
    assert first.seed == base.seed
    assert first.tempo_bpm == base.tempo_bpm
    assert first.key_center == base.key_center
    assert first.motif == base.motif
    assert first.boundary_constraints == base.boundary_constraints
    assert first.texture_layers != second.texture_layers
    assert "chunk 1 of 3" in " ".join(first.texture_layers)
    assert "chunk 2 of 3" in " ".join(second.texture_layers)
