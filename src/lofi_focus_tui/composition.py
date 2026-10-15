from lofi_focus_tui.domain import CompositionBlueprint, SessionPlan
from lofi_focus_tui.options import FOCUS_OPTIONS, PRESET_OPTIONS


def create_blueprint(plan: SessionPlan) -> CompositionBlueprint:
    low, high = plan.tempo_range
    tempo = low + (plan.seed % max(1, high - low + 1))
    focus = FOCUS_OPTIONS[plan.focus]
    preset = PRESET_OPTIONS[plan.preset]
    variant = preset.variants[plan.seed % len(preset.variants)]

    return CompositionBlueprint(
        session_id=plan.session_id,
        seed=plan.seed,
        focus=plan.focus,
        focus_constraints=list(plan.focus_constraints),
        tempo_bpm=tempo,
        key_center=plan.key_center,
        harmonic_palette=["i", "VI", "III", "VII"],
        motif=variant.motif,
        drum_feel=variant.drum_feel,
        bass_behavior=variant.bass_behavior,
        texture_layers=plan.style_traits,
        genre_tags=preset.genre_tags,
        arrangement_sections=list(focus.arrangement_sections),
        boundary_constraints=[
            "preserve stable tempo",
            "preserve key center",
            "preserve shared motif",
            "avoid abrupt section jumps",
        ],
        prompt=plan.prompt,
        vocal_mode=plan.vocal_mode,
        energy=plan.energy,
    )


def create_chunk_blueprint(
    plan: SessionPlan,
    chunk_index: int,
    chunk_count: int,
    continuation_constraints: list[str] | None = None,
    base_blueprint: CompositionBlueprint | None = None,
) -> CompositionBlueprint:
    blueprint = base_blueprint if base_blueprint is not None else create_blueprint(plan)
    section = blueprint.arrangement_sections[
        min(chunk_index, len(blueprint.arrangement_sections) - 1)
    ]
    constraints = list(continuation_constraints or [])
    if chunk_count > 1:
        # The model tends to treat every generation as a complete song, fading
        # out at the end and fading in at the start; at internal chunk
        # boundaries those fades stack into seconds of near-silence. Ask for
        # energy held through the final bar / a mid-groove entry instead.
        if chunk_index < chunk_count - 1:
            constraints.append("carries full energy through the final bar, ending mid-groove")
        if chunk_index > 0:
            constraints.append(
                "begins mid-groove at full energy, continuing the established texture"
            )
    return blueprint.model_copy(
        update={
            "section": section,
            "continuation_constraints": constraints,
        }
    )
