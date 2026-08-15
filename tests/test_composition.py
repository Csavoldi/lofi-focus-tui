from lofi_focus_tui.composition import create_blueprint, create_chunk_blueprint
from lofi_focus_tui.domain import EnergyLevel, SessionRequest
from lofi_focus_tui.presets import expand_preset


def test_blueprint_carries_continuity_identity():
    plan = expand_preset(
        SessionRequest(
            focus="deep_work",
            preset="classic_lofi",
            duration_minutes=30,
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
            focus="deep_work",
            preset="classic_lofi",
            duration_minutes=30,
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


def test_chunk_blueprint_carries_continuation_constraints():
    plan = expand_preset(
        SessionRequest(
            focus="deep_work",
            preset="classic_lofi",
            duration_minutes=30,
            energy=EnergyLevel.STEADY,
        )
    )

    blueprint = create_chunk_blueprint(
        plan,
        chunk_index=1,
        chunk_count=2,
        continuation_constraints=["avoid a sharp transient at the transition"],
    )

    assert blueprint.continuation_constraints == [
        "avoid a sharp transient at the transition"
    ]
