from lofi_focus_tui.domain import CompositionBlueprint, SessionPlan


def create_blueprint(plan: SessionPlan) -> CompositionBlueprint:
    low, high = plan.tempo_range
    tempo = low + (plan.seed % max(1, high - low + 1))

    return CompositionBlueprint(
        session_id=plan.session_id,
        seed=plan.seed,
        tempo_bpm=tempo,
        key_center=plan.key_center,
        harmonic_palette=["i", "VI", "III", "VII"],
        motif="short dusty electric-piano figure with soft delay",
        drum_feel="soft swung lofi backbeat",
        bass_behavior="round sustained bass with minimal jumps",
        texture_layers=plan.style_traits,
        arrangement_sections=["warmup", "steady_work", "cooldown"],
        boundary_constraints=[
            "preserve stable tempo",
            "preserve key center",
            "preserve shared motif",
            "avoid abrupt timbre changes",
        ],
    )
