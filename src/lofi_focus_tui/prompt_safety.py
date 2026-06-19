TAG_MAP = {
    "deftones": [
        "hazy downtuned alternative texture",
        "soft chorus-like guitar ambience",
        "restrained quiet-loud dynamics",
    ],
    "japanese rap": [
        "percussive japanese hip hop texture",
        "tight swung drums",
        "instrumental city-night energy",
    ],
    "wizard": [
        "mystic modal ambience",
        "soft bell-like accents",
        "ancient library atmosphere",
    ],
}


def map_style_tags(tags: list[str]) -> list[str]:
    traits: list[str] = []
    for tag in tags:
        normalized = tag.strip().lower()
        mapped = TAG_MAP.get(normalized)
        if mapped:
            traits.extend(mapped)
        else:
            traits.append(normalized.replace("_", " "))
    return traits
