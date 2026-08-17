import hashlib
from uuid import uuid4

from lofi_focus_tui.domain import EnergyLevel, SessionPhase, SessionPlan, SessionRequest
from lofi_focus_tui.options import FOCUS_OPTIONS


def expand_preset(request: SessionRequest) -> SessionPlan:
    tempo_range = (72, 88) if request.energy != EnergyLevel.HIGH else (82, 96)
    avoid_traits = [tag.replace("_", " ") for tag in request.avoid_tags]
    legacy_vocal_tags = {"vocals", "no vocals"}
    avoid_traits = [
        tag
        for tag in avoid_traits
        if tag.replace("_", " ").strip().lower() not in legacy_vocal_tags
        or request.vocal_mode == "instrumental"
    ]
    if request.vocal_mode == "instrumental":
        avoid_traits.append("vocals")
    avoid_traits.extend(["sharp transients", "sudden drops"])
    seed = request.seed
    if seed is None:
        payload = "|".join([request.preset, str(request.duration_minutes), *request.style_tags])
        seed = int.from_bytes(hashlib.sha256(payload.encode("utf-8")).digest()[:4], "big") % 2**31

    return SessionPlan(
        session_id=str(uuid4()),
        focus=request.focus,
        seed=seed,
        preset=request.preset,
        duration_minutes=request.duration_minutes,
        energy=request.energy,
        phases=[SessionPhase.WARMUP, SessionPhase.STEADY_WORK, SessionPhase.COOLDOWN],
        tempo_range=tempo_range,
        key_center="minor pentatonic",
        style_traits=[tag.replace("_", " ") for tag in request.style_tags],
        avoid_traits=sorted(set(avoid_traits)),
        focus_constraints=list(FOCUS_OPTIONS[request.focus].focus_constraints),
        continuity_requirements=[
            "stable tempo",
            "consistent key center",
            "shared motif",
            "no abrupt section jumps",
        ],
        prompt=request.prompt,
        vocal_mode=request.vocal_mode,
    )
