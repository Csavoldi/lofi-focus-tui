from lofi_focus_tui.domain import CompositionBlueprint, SessionPlan
from lofi_focus_tui.options import FOCUS_OPTIONS, PRESET_OPTIONS


def create_blueprint(plan: SessionPlan) -> CompositionBlueprint:
    low, high = plan.tempo_range
    tempo = low + (plan.seed % max(1, high - low + 1))
    focus = FOCUS_OPTIONS[plan.focus]
    preset = PRESET_OPTIONS[plan.preset]

    return CompositionBlueprint(
        session_id=plan.session_id,
        seed=plan.seed,
        focus=plan.focus,
        focus_constraints=list(plan.focus_constraints),
        tempo_bpm=tempo,
        key_center=plan.key_center,
        harmonic_palette=["i", "VI", "III", "VII"],
        motif=preset.motif,
        drum_feel=preset.drum_feel,
        bass_behavior=preset.bass_behavior,
        texture_layers=plan.style_traits,
        arrangement_sections=list(focus.arrangement_sections),
        boundary_constraints=[
            "preserve stable tempo",
            "preserve key center",
            "preserve shared motif",
            "avoid abrupt section jumps",
        ],
    )


def create_chunk_blueprint(
    plan: SessionPlan,
    chunk_index: int,
    chunk_count: int,
    continuation_constraints: list[str] | None = None,
) -> CompositionBlueprint:
    blueprint = create_blueprint(plan)
    section = blueprint.arrangement_sections[
        min(chunk_index, len(blueprint.arrangement_sections) - 1)
    ]
    chunk_label = f"chunk {chunk_index + 1} of {chunk_count}"
    return blueprint.model_copy(
        update={
            "texture_layers": [
                *blueprint.texture_layers,
                f"{chunk_label} {section} texture",
            ],
            "arrangement_sections": [section, chunk_label],
            "continuation_constraints": continuation_constraints or [],
        }
    )
