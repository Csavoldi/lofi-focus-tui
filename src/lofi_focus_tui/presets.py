from uuid import uuid4

from lofi_focus_tui.domain import EnergyLevel, SessionPhase, SessionPlan, SessionRequest


def expand_preset(request: SessionRequest) -> SessionPlan:
    tempo_range = (72, 88) if request.energy != EnergyLevel.HIGH else (82, 96)
    avoid_traits = [tag.replace("_", " ") for tag in request.avoid_tags]
    avoid_traits.extend(["vocals", "sharp transients", "sudden drops"])
    seed = request.seed
    if seed is None:
        seed = (
            abs(hash((request.preset, request.duration_minutes, tuple(request.style_tags))))
            % 2**31
        )

    return SessionPlan(
        session_id=str(uuid4()),
        seed=seed,
        preset=request.preset,
        duration_minutes=request.duration_minutes,
        energy=request.energy,
        phases=[SessionPhase.WARMUP, SessionPhase.STEADY_WORK, SessionPhase.COOLDOWN],
        tempo_range=tempo_range,
        key_center="minor pentatonic",
        style_traits=[tag.replace("_", " ") for tag in request.style_tags],
        avoid_traits=sorted(set(avoid_traits)),
        continuity_requirements=[
            "stable tempo",
            "consistent key center",
            "shared motif",
            "no abrupt section jumps",
        ],
    )
