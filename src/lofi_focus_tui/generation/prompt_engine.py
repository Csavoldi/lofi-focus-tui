from lofi_focus_tui.domain import CompositionBlueprint
from lofi_focus_tui.options import ENERGY_OPTIONS

MAX_PROMPT_LENGTH = 512
SEPARATOR = ". "


def _clean_items(items):
    return [item.strip() for item in items if item.strip()]


def append_prompt_parts(parts) -> str:
    result = ""
    for raw_part in parts:
        part = raw_part.strip()
        if not part:
            continue
        separator = SEPARATOR if result else ""
        remaining = MAX_PROMPT_LENGTH - len(result)
        if remaining < len(separator) + 1:
            break
        prefix = part[: remaining - len(separator)].rstrip()
        if not prefix:
            break
        result += separator + prefix
        if len(prefix) < len(part):
            break
    return result


def compose_local_prompt(blueprint: CompositionBlueprint) -> str:
    context = _clean_items(
        [
            *blueprint.texture_layers,
            blueprint.motif,
            blueprint.drum_feel,
            blueprint.bass_behavior,
            f"{blueprint.energy.value} energy: {ENERGY_OPTIONS[blueprint.energy].description}",
        ]
    )
    focus_constraints = _clean_items(blueprint.focus_constraints)
    if focus_constraints:
        context.append(f"{blueprint.focus.strip()} focus: {', '.join(focus_constraints)}")

    technical = [
        f"{blueprint.tempo_bpm} BPM",
        blueprint.key_center,
        f"meter {blueprint.meter}",
    ]
    arrangement = _clean_items(blueprint.arrangement_sections)
    if arrangement:
        technical.append(f"arrangement: {', '.join(arrangement)}")
    technical.extend(_clean_items(blueprint.boundary_constraints))
    technical.extend(_clean_items(blueprint.continuation_constraints))

    vocal = (
        "Vocal direction: vocals allowed"
        if blueprint.vocal_mode == "vocals"
        else "Vocal direction: instrumental, no vocals"
    )
    return append_prompt_parts(
        [
            blueprint.prompt,
            f"Optional musical context: {', '.join(context)}",
            f"Technical direction: {', '.join(_clean_items(technical))}",
            vocal,
        ]
    )


def compose_enriched_prompt(blueprint: CompositionBlueprint, caption: str) -> str:
    caption = caption.strip()
    prompt = blueprint.prompt.strip()
    return append_prompt_parts([prompt, caption]) if prompt else append_prompt_parts([caption])
