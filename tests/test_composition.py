from lofi_focus_tui.composition import create_blueprint, create_chunk_blueprint
from lofi_focus_tui.domain import EnergyLevel, SessionRequest
from lofi_focus_tui.options import FOCUS_OPTIONS, PRESET_OPTIONS
from lofi_focus_tui.presets import expand_preset

BOUNDARY_CONSTRAINTS = [
    "preserve stable tempo",
    "preserve key center",
    "preserve shared motif",
    "avoid abrupt section jumps",
]


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
    assert blueprint.boundary_constraints == BOUNDARY_CONSTRAINTS
    assert blueprint.genre_tags == PRESET_OPTIONS["classic_lofi"].genre_tags


def test_blueprint_applies_each_focus_recipe():
    for focus, option in FOCUS_OPTIONS.items():
        plan = expand_preset(
            SessionRequest(
                focus=focus,
                preset="classic_lofi",
                duration_minutes=30,
                energy=EnergyLevel.STEADY,
                seed=123,
            )
        )

        blueprint = create_blueprint(plan)

        assert blueprint.focus == plan.focus == focus
        assert blueprint.focus_constraints == plan.focus_constraints == option.focus_constraints
        assert blueprint.arrangement_sections == option.arrangement_sections


def test_blueprint_applies_each_music_preset_recipe():
    for preset, option in PRESET_OPTIONS.items():
        plan = expand_preset(
            SessionRequest(
                focus="coding",
                preset=preset,
                duration_minutes=30,
                energy=EnergyLevel.STEADY,
                seed=123,
            )
        )

        blueprint = create_blueprint(plan)

        assert (blueprint.motif, blueprint.drum_feel, blueprint.bass_behavior) in {
            (variant.motif, variant.drum_feel, variant.bass_behavior)
            for variant in option.variants
        }


def test_blueprint_picks_preset_variant_from_session_seed():
    option = PRESET_OPTIONS["boom_bap"]
    pool = {
        (variant.motif, variant.drum_feel, variant.bass_behavior)
        for variant in option.variants
    }

    def traits_for(seed):
        plan = expand_preset(
            SessionRequest(
                preset="boom_bap", duration_minutes=30, energy="steady", seed=seed
            )
        )
        blueprint = create_blueprint(plan)
        return (blueprint.motif, blueprint.drum_feel, blueprint.bass_behavior)

    picked = {traits_for(seed) for seed in range(12)}

    assert picked <= pool
    assert len(picked) >= 2
    assert traits_for(5) == traits_for(5)


def test_focus_and_preset_recipes_preserve_request_settings_and_vary_expected_traits():
    def build(focus, preset):
        plan = expand_preset(
            SessionRequest(
                focus=focus,
                preset=preset,
                duration_minutes=45,
                energy=EnergyLevel.HIGH,
                seed=321,
            )
        )
        return plan, create_blueprint(plan)

    coding_classic_plan, coding_classic = build("coding", "classic_lofi")
    coding_ambient_plan, coding_ambient = build("coding", "ambient_tape")
    reading_classic_plan, reading_classic = build("reading", "classic_lofi")

    for plan in (coding_classic_plan, coding_ambient_plan, reading_classic_plan):
        assert (plan.duration_minutes, plan.energy, plan.seed) == (45, EnergyLevel.HIGH, 321)

    assert coding_classic.focus_constraints == coding_ambient.focus_constraints
    assert coding_classic.arrangement_sections == coding_ambient.arrangement_sections
    assert (coding_classic.motif, coding_classic.drum_feel, coding_classic.bass_behavior) != (
        coding_ambient.motif,
        coding_ambient.drum_feel,
        coding_ambient.bass_behavior,
    )

    assert (coding_classic.motif, coding_classic.drum_feel, coding_classic.bass_behavior) == (
        reading_classic.motif,
        reading_classic.drum_feel,
        reading_classic.bass_behavior,
    )
    assert coding_classic.focus_constraints != reading_classic.focus_constraints
    assert coding_classic.arrangement_sections != reading_classic.arrangement_sections


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
    assert first.section == "warmup"
    assert second.section == "steady_work"
    assert first.texture_layers == second.texture_layers == base.texture_layers


def test_chunk_blueprint_reuses_supplied_base_blueprint(monkeypatch):
    plan = expand_preset(
        SessionRequest(
            focus="deep_work",
            preset="classic_lofi",
            duration_minutes=30,
            energy=EnergyLevel.HIGH,
            prompt="late-night rainy room",
            vocal_mode="vocals",
            seed=123,
        )
    )
    base = create_blueprint(plan)

    def fail_create_blueprint(_plan):
        raise AssertionError("create_blueprint should not be called")

    monkeypatch.setattr("lofi_focus_tui.composition.create_blueprint", fail_create_blueprint)
    chunk = create_chunk_blueprint(plan, 0, 2, base_blueprint=base)

    assert chunk.prompt == base.prompt == plan.prompt
    assert chunk.energy == base.energy == plan.energy
    assert chunk.vocal_mode == base.vocal_mode == plan.vocal_mode
    assert chunk.seed == base.seed == plan.seed
    assert chunk.session_id == base.session_id == plan.session_id


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
        "avoid a sharp transient at the transition",
        # chunk 1 of 2 is the final chunk: it must enter mid-groove, and the
        # fade-out constraint belongs to non-final chunks only.
        "begins mid-groove at full energy, continuing the established texture",
    ]


def test_chunk_blueprint_adds_boundary_continuity_constraints_per_position():
    plan = expand_preset(
        SessionRequest(
            focus="deep_work",
            preset="classic_lofi",
            duration_minutes=30,
            energy=EnergyLevel.STEADY,
        )
    )

    first = create_chunk_blueprint(plan, chunk_index=0, chunk_count=3)
    middle = create_chunk_blueprint(plan, chunk_index=1, chunk_count=3)
    last = create_chunk_blueprint(plan, chunk_index=2, chunk_count=3)

    tail = "carries full energy through the final bar, ending mid-groove"
    head = "begins mid-groove at full energy, continuing the established texture"
    assert tail in first.continuation_constraints
    assert head not in first.continuation_constraints
    assert tail in middle.continuation_constraints
    assert head in middle.continuation_constraints
    assert head in last.continuation_constraints
    assert tail not in last.continuation_constraints

    # The constraints are positive music captions, so the prompt engine must
    # keep them verbatim instead of dropping them as negations.
    from lofi_focus_tui.generation.prompt_engine import compose_local_prompt

    assert tail in compose_local_prompt(first)
    assert head in compose_local_prompt(last)
