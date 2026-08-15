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
    assert set(PRESET_OPTIONS) == {"classic_lofi", "neo_soul", "ambient_tape", "jazz_vinyl"}
    assert set(ENERGY_OPTIONS) == set(EnergyLevel)
    assert set(STYLE_OPTIONS) == {"lofi, neo_soul", "ambient, tape", "rainy, mellow", "jazz, vinyl"}

    assert len(FOCUS_OPTIONS) == 4
    assert len(PRESET_OPTIONS) == 4
    assert len(ENERGY_OPTIONS) == 3
    assert len(STYLE_OPTIONS) == 4
    for catalog in (FOCUS_OPTIONS, PRESET_OPTIONS, ENERGY_OPTIONS, STYLE_OPTIONS):
        assert all(option.description for option in catalog.values())

    assert LEGACY_FOCUS_VALUES == {"deep_work", "reading", "coding", "wind_down"}
    assert LEGACY_FOCUS_VALUES.isdisjoint(PRESET_OPTIONS)


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
    }
    assert {
        value: option.description for value, option in ENERGY_OPTIONS.items()
    } == {
        EnergyLevel.LOW: "soft movement and a restrained pulse",
        EnergyLevel.STEADY: "balanced movement for ordinary focus work",
        EnergyLevel.HIGH: "more rhythmic momentum while remaining non-distracting",
    }
    assert {
        value: option.description for value, option in STYLE_OPTIONS.items()
    } == {
        "lofi, neo_soul": "warm, dusty, chord-forward texture",
        "ambient, tape": "spacious, hazy, slowly moving texture",
        "rainy, mellow": "soft atmosphere and subdued detail",
        "jazz, vinyl": "brushed, tactile, lightly swinging texture",
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
            ["low density", "soft transitions", "no abrupt changes"],
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
    }
