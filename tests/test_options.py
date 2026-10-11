from lofi_focus_tui.domain import EnergyLevel
from lofi_focus_tui.options import (
    ENERGY_OPTIONS,
    FOCUS_OPTIONS,
    LEGACY_FOCUS_VALUES,
    PRESET_OPTIONS,
    STYLE_OPTIONS,
)


def test_catalogs_expose_expected_values_and_descriptions():
    assert set(FOCUS_OPTIONS) == {"deep_work", "reading", "coding", "wind_down"}
    assert set(PRESET_OPTIONS) == {
        "classic_lofi",
        "neo_soul",
        "ambient_tape",
        "jazz_vinyl",
        "lofi_house",
        "synthwave",
        "city_pop",
        "boom_bap",
        "peaceful_piano",
    }
    assert set(ENERGY_OPTIONS) == set(EnergyLevel)
    assert set(STYLE_OPTIONS) == {
        "lofi, neo_soul",
        "ambient, tape",
        "rainy, mellow",
        "jazz, vinyl",
        "vinyl, dust",
        "neon, retro",
    }

    assert len(FOCUS_OPTIONS) == 4
    assert len(PRESET_OPTIONS) == 9
    assert len(ENERGY_OPTIONS) == 3
    assert len(STYLE_OPTIONS) == 6
    for catalog in (FOCUS_OPTIONS, PRESET_OPTIONS, ENERGY_OPTIONS, STYLE_OPTIONS):
        assert all(option.description for option in catalog.values())

    assert LEGACY_FOCUS_VALUES == {"deep_work", "reading", "coding", "wind_down"}
    assert LEGACY_FOCUS_VALUES.isdisjoint(PRESET_OPTIONS)


def test_style_values_split_into_two_texture_tags():
    for value in STYLE_OPTIONS:
        tags = [tag.strip() for tag in value.split(",")]
        assert len(tags) == 2
        assert all(tags)


def test_catalog_descriptions_are_exact():
    assert {
        value: option.description for value, option in FOCUS_OPTIONS.items()
    } == {
        "deep_work": "sustained concentration and low distraction",
        "reading": "spacious, calm, gentle pulse",
        "coding": "forward momentum and a steady groove",
        "wind_down": "soft, slow decompression",
    }
    assert {
        value: option.description for value, option in PRESET_OPTIONS.items()
    } == {
        "classic_lofi": "dusty keys, swung drums, round bass",
        "neo_soul": "warm chords, pocketed rhythm, mellow bass",
        "ambient_tape": "sparse pulse, wide pads, tape haze",
        "jazz_vinyl": "brushed drums, jazz harmony, vinyl texture",
        "lofi_house": "washed chord stabs, four-on-the-floor, tape hiss",
        "synthwave": "analog arps, gated drums, neon nostalgia",
        "city_pop": "funky bass, bright keys, 80s sheen",
        "boom_bap": "gritty breaks, sampled chops, vinyl grit",
        "peaceful_piano": "felt piano, dreamy pads, near-weightless",
    }
    assert {
        value: option.description for value, option in ENERGY_OPTIONS.items()
    } == {
        EnergyLevel.LOW: "slow and spacious, resting at the soft end of the preset's tempo range",
        EnergyLevel.STEADY: "the preset's natural tempo, balanced for ordinary focus work",
        EnergyLevel.HIGH: "livelier end of the preset's tempo range, still non-distracting",
    }
    assert {
        value: option.description for value, option in STYLE_OPTIONS.items()
    } == {
        "lofi, neo_soul": "warm, dusty, chord-forward texture",
        "ambient, tape": "spacious, hazy, slowly moving texture",
        "rainy, mellow": "rainy-day atmosphere, soft and subdued",
        "jazz, vinyl": "brushed, tactile, lightly swinging texture",
        "vinyl, dust": "crackly, gritty beattape texture",
        "neon, retro": "bright 80s sheen, nostalgic glow",
    }


def test_focus_constraints_and_arrangements_are_exact():
    assert {
        value: (option.focus_constraints, option.arrangement_sections)
        for value, option in FOCUS_OPTIONS.items()
    } == {
        "deep_work": (
            ["minimal variation", "stable tempo", "no abrupt changes"],
            ["warmup", "steady_work", "cooldown"],
        ),
        "reading": (
            ["spacious pacing", "light percussion", "no abrupt changes"],
            ["warmup", "reading", "cooldown"],
        ),
        "coding": (
            ["consistent forward pulse", "stable groove", "no abrupt changes"],
            ["warmup", "steady_work", "momentum"],
        ),
        "wind_down": (
            ["low density", "minimal percussion", "soft transitions", "no abrupt changes"],
            ["settle", "unwind", "cooldown"],
        ),
    }


def test_preset_traits_are_exact():
    assert {
        value: (option.motif, option.drum_feel, option.bass_behavior)
        for value, option in PRESET_OPTIONS.items()
    } == {
        "classic_lofi": (
            "dusty electric-piano figure",
            "soft swung lofi backbeat",
            "round sustained bass",
        ),
        "neo_soul": (
            "warm Rhodes-style chord figure",
            "pocketed neo-soul groove",
            "mellow melodic bass",
        ),
        "ambient_tape": (
            "sparse washed pad motif",
            "minimal soft pulse",
            "long sustained low movement",
        ),
        "jazz_vinyl": (
            "jazzy electric-piano motif",
            "brushed light swing",
            "warm upright-style movement",
        ),
        "lofi_house": (
            "washed chord-stab loop",
            "soft four-on-the-floor house kick",
            "deep rolling bassline",
        ),
        "synthwave": (
            "analog synth arpeggio",
            "gated 80s drum machine",
            "pulsing synth bass",
        ),
        "city_pop": (
            "bright electric-piano lick",
            "light funk groove",
            "bouncy fingered bassline",
        ),
        "boom_bap": (
            "sampled melodic chop",
            "dusty boom-bap break with a fat snare",
            "subby round bass",
        ),
        "peaceful_piano": (
            "soft felt-piano figure",
            "sparse gentle pulse",
            "sparse low piano notes",
        ),
    }


def test_every_music_preset_carries_a_tempo_range():
    expected = {
        "classic_lofi": (70, 90),
        "neo_soul": (65, 85),
        "ambient_tape": (60, 80),
        "jazz_vinyl": (65, 85),
        "lofi_house": (110, 125),
        "synthwave": (80, 110),
        "city_pop": (100, 115),
        "boom_bap": (75, 95),
        "peaceful_piano": (60, 75),
    }
    assert {
        value: option.tempo_range for value, option in PRESET_OPTIONS.items()
    } == expected
