from lofi_focus_tui.domain import CompositionBlueprint, EnergyLevel

MAX_PROMPT_LENGTH = 1024
SEPARATOR = ". "

_ENERGY_CAPTION_WORDS = {
    EnergyLevel.LOW: "mellow",
    EnergyLevel.STEADY: "relaxed",
    EnergyLevel.HIGH: "lively",
}

_ENERGY_LYRICS_MODIFIERS = {
    EnergyLevel.LOW: "mellow",
    EnergyLevel.STEADY: "steady",
    EnergyLevel.HIGH: "driving",
}

_FOCUS_CAPTION_PHRASES = {
    "deep_work": "unobtrusive and hypnotic for deep focus",
    "reading": "spacious and calm with a gentle pulse",
    "coding": "steady forward momentum with a consistent groove",
    "wind_down": "soft and soothing for winding down",
}

_SECTION_CAPTION_PHRASES = {
    "warmup": "opening section that eases in gently",
    "settle": "soft opening section",
    "steady_work": "steady main section",
    "reading": "calm main section",
    "unwind": "gently unwinding main section",
    "momentum": "forward-driving section",
    "cooldown": "closing section that settles down",
}

_SECTION_LYRICS_TAGS = {
    "warmup": "Intro",
    "settle": "Intro",
    "steady_work": "Main Theme",
    "reading": "Main Theme",
    "unwind": "Main Theme",
    "momentum": "Build",
    "cooldown": "Outro",
}

# ACE-Step captions describe the music positively; negations ("no abrupt
# changes") and mixing instructions ("match the previous chunk's loudness")
# do not translate to the DiT. Rewrite known constraints and drop the rest.
_CONSTRAINT_REWRITES = {
    "no abrupt changes": "smooth transitions",
    "no abrupt section jumps": "smooth section transitions",
    "avoid abrupt section jumps": "smooth section transitions",
    "avoid a sharp transient at the transition": (
        "a smooth transition from the previous section"
    ),
    "avoid sharp transients": "smooth transients",
    "preserve stable tempo": "steady consistent tempo",
    "preserve key center": "consistent key center",
    "preserve shared motif": "recurring signature motif",
    "carry motif": "recurring motif",
    "match the previous chunk's loudness at the transition": "",
    "maintain continuous low-level texture through the transition": (
        "continuous low-level texture carried across the section change"
    ),
    "reduce peak density and avoid aggressive transients": "gentle transients",
    "continue the established timbral balance into the next section": (
        "timbre carried consistently from the previous section"
    ),
}

_NEGATIVE_PREFIXES = ("no ", "not ", "never ", "avoid ", "without ", "don't ")

# ACE-Step metadata expects a full key name like "A Minor"; "minor pentatonic"
# is the app's tonal flavor, not a key name the model anchors on.
_KEY_SCALE_ALIASES = {
    "minor pentatonic": "A Minor",
}

# Community guidance for ACE-Step 1.5 captions keeps tempo qualitative in the
# caption (the numeric bpm rides in metadata): short phrases beat prose, and
# the tempo slot sits between the instrument list and the vibe description.
_TEMPO_PHRASES = (
    (80, "slow, unhurried tempo"),
    (100, "easy mid-tempo pulse"),
    (120, "steady up-tempo pulse"),
)
_TEMPO_PHRASE_MAX = "driving up-tempo momentum"


def _qualitative_tempo(bpm: int) -> str:
    for threshold, phrase in _TEMPO_PHRASES:
        if bpm < threshold:
            return phrase
    return _TEMPO_PHRASE_MAX


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
    genre = (
        "instrumental lo-fi"
        if blueprint.vocal_mode == "instrumental"
        else "lo-fi with vocals"
    )
    mood = _ENERGY_CAPTION_WORDS[blueprint.energy]
    instruments = _clean_items(
        [
            blueprint.motif,
            blueprint.drum_feel,
            blueprint.bass_behavior,
            *blueprint.texture_layers,
        ]
    )
    # Caption slots follow the community-validated order for ACE-Step:
    # genre/style tags, lead instruments, qualitative tempo, vibe, then the
    # arrangement description. The preset's genre words lead so they survive
    # truncation, and the user's own wording slots in as atmosphere.
    genre_bits = [tag.strip() for tag in blueprint.genre_tags.split(",") if tag.strip()]
    style = ", ".join([*genre_bits, f"{mood} {genre}"])
    parts = [f"{style}: {', '.join(instruments)}" if instruments else style]
    parts.append(_qualitative_tempo(blueprint.tempo_bpm))
    parts.append(blueprint.prompt.strip())
    parts.append(_FOCUS_CAPTION_PHRASES.get(blueprint.focus, ""))
    parts.append(_SECTION_CAPTION_PHRASES.get(blueprint.section.strip(), ""))
    parts.append(_continuity_phrase(blueprint))
    return append_prompt_parts(parts)


def compose_instrumental_lyrics(blueprint: CompositionBlueprint) -> str:
    if blueprint.vocal_mode != "instrumental":
        return ""
    section = blueprint.section.strip()
    tag = _SECTION_LYRICS_TAGS.get(section)
    if not tag:
        return "[Instrumental]"
    modifier = _ENERGY_LYRICS_MODIFIERS[blueprint.energy]
    return f"[{tag} - {modifier}]"


def key_scale_for_metadata(key_center: str) -> str:
    key = key_center.strip()
    return _KEY_SCALE_ALIASES.get(key.lower(), key)


def compose_enriched_prompt(blueprint: CompositionBlueprint, caption: str) -> str:
    caption = caption.strip()
    prompt = blueprint.prompt.strip()
    return append_prompt_parts([prompt, caption]) if prompt else append_prompt_parts([caption])


def _continuity_phrase(blueprint: CompositionBlueprint) -> str:
    rewritten = []
    for constraint in (
        *blueprint.focus_constraints,
        *blueprint.boundary_constraints,
        *blueprint.continuation_constraints,
    ):
        phrase = _rewrite_constraint(constraint)
        if phrase and phrase not in rewritten:
            rewritten.append(phrase)
    return ", ".join(rewritten)


def _rewrite_constraint(constraint: str) -> str:
    text = constraint.strip().lower()
    if not text:
        return ""
    if text in _CONSTRAINT_REWRITES:
        return _CONSTRAINT_REWRITES[text]
    if text.startswith(_NEGATIVE_PREFIXES):
        return ""
    return constraint.strip()
