from dataclasses import dataclass
from typing import Generic, TypeVar

try:
    from enum import StrEnum
except ImportError:  # pragma: no cover - compatibility for Python 3.10
    from enum import Enum

    class StrEnum(str, Enum):
        pass

from lofi_focus_tui.domain import EnergyLevel


class FocusValue(StrEnum):
    DEEP_WORK = "deep_work"
    READING = "reading"
    CODING = "coding"
    WIND_DOWN = "wind_down"


class MusicPresetValue(StrEnum):
    CLASSIC_LOFI = "classic_lofi"
    NEO_SOUL = "neo_soul"
    AMBIENT_TAPE = "ambient_tape"
    JAZZ_VINYL = "jazz_vinyl"
    LOFI_HOUSE = "lofi_house"
    SYNTHWAVE = "synthwave"
    CITY_POP = "city_pop"
    BOOM_BAP = "boom_bap"
    PEACEFUL_PIANO = "peaceful_piano"


class StyleValue(StrEnum):
    LOFI_NEO_SOUL = "lofi, neo_soul"
    AMBIENT_TAPE = "ambient, tape"
    RAINY_MELLOW = "rainy, mellow"
    JAZZ_VINYL = "jazz, vinyl"
    VINYL_DUST = "vinyl, dust"
    NEON_RETRO = "neon, retro"


@dataclass(frozen=True, slots=True)
class FocusOption:
    value: FocusValue
    description: str
    focus_constraints: list[str]
    arrangement_sections: list[str]


@dataclass(frozen=True, slots=True)
class PresetOption:
    value: MusicPresetValue
    description: str
    motif: str
    drum_feel: str
    bass_behavior: str
    tempo_range: tuple[int, int]


OptionValue = TypeVar("OptionValue")


@dataclass(frozen=True, slots=True)
class DescribedOption(Generic[OptionValue]):
    value: OptionValue
    description: str


FOCUS_OPTIONS = {
    FocusValue.DEEP_WORK: FocusOption(
        FocusValue.DEEP_WORK,
        "sustained concentration and low distraction",
        ["minimal variation", "stable tempo", "no abrupt changes"],
        ["warmup", "steady_work", "cooldown"],
    ),
    FocusValue.READING: FocusOption(
        FocusValue.READING,
        "spacious, calm, gentle pulse",
        ["spacious pacing", "light percussion", "no abrupt changes"],
        ["warmup", "reading", "cooldown"],
    ),
    FocusValue.CODING: FocusOption(
        FocusValue.CODING,
        "forward momentum and a steady groove",
        ["consistent forward pulse", "stable groove", "no abrupt changes"],
        ["warmup", "steady_work", "momentum"],
    ),
    FocusValue.WIND_DOWN: FocusOption(
        FocusValue.WIND_DOWN,
        "soft, slow decompression",
        ["low density", "minimal percussion", "soft transitions", "no abrupt changes"],
        ["settle", "unwind", "cooldown"],
    ),
}

PRESET_OPTIONS = {
    MusicPresetValue.CLASSIC_LOFI: PresetOption(
        MusicPresetValue.CLASSIC_LOFI,
        "dusty keys, swung drums, round bass",
        "dusty electric-piano figure",
        "soft swung lofi backbeat",
        "round sustained bass",
        (70, 90),
    ),
    MusicPresetValue.NEO_SOUL: PresetOption(
        MusicPresetValue.NEO_SOUL,
        "warm chords, pocketed rhythm, mellow bass",
        "warm Rhodes-style chord figure",
        "pocketed neo-soul groove",
        "mellow melodic bass",
        (65, 85),
    ),
    MusicPresetValue.AMBIENT_TAPE: PresetOption(
        MusicPresetValue.AMBIENT_TAPE,
        "sparse pulse, wide pads, tape haze",
        "sparse washed pad motif",
        "minimal soft pulse",
        "long sustained low movement",
        (60, 80),
    ),
    MusicPresetValue.JAZZ_VINYL: PresetOption(
        MusicPresetValue.JAZZ_VINYL,
        "brushed drums, jazz harmony, vinyl texture",
        "jazzy electric-piano motif",
        "brushed light swing",
        "warm upright-style movement",
        (65, 85),
    ),
    MusicPresetValue.LOFI_HOUSE: PresetOption(
        MusicPresetValue.LOFI_HOUSE,
        "washed chord stabs, four-on-the-floor, tape hiss",
        "washed chord-stab loop",
        "soft four-on-the-floor house kick",
        "deep rolling bassline",
        (110, 125),
    ),
    MusicPresetValue.SYNTHWAVE: PresetOption(
        MusicPresetValue.SYNTHWAVE,
        "analog arps, gated drums, neon nostalgia",
        "analog synth arpeggio",
        "gated 80s drum machine",
        "pulsing synth bass",
        (80, 110),
    ),
    MusicPresetValue.CITY_POP: PresetOption(
        MusicPresetValue.CITY_POP,
        "funky bass, bright keys, 80s sheen",
        "bright electric-piano lick",
        "light funk groove",
        "bouncy fingered bassline",
        (100, 115),
    ),
    MusicPresetValue.BOOM_BAP: PresetOption(
        MusicPresetValue.BOOM_BAP,
        "gritty breaks, sampled chops, vinyl grit",
        "sampled melodic chop",
        "dusty boom-bap break with a fat snare",
        "subby round bass",
        (75, 95),
    ),
    MusicPresetValue.PEACEFUL_PIANO: PresetOption(
        MusicPresetValue.PEACEFUL_PIANO,
        "felt piano, dreamy pads, near-weightless",
        "soft felt-piano figure",
        "sparse gentle pulse",
        "sparse low piano notes",
        (60, 75),
    ),
}

ENERGY_OPTIONS = {
    EnergyLevel.LOW: DescribedOption(
        EnergyLevel.LOW,
        "slow and spacious, resting at the soft end of the preset's tempo range",
    ),
    EnergyLevel.STEADY: DescribedOption(
        EnergyLevel.STEADY,
        "the preset's natural tempo, balanced for ordinary focus work",
    ),
    EnergyLevel.HIGH: DescribedOption(
        EnergyLevel.HIGH,
        "livelier end of the preset's tempo range, still non-distracting",
    ),
}

STYLE_OPTIONS = {
    StyleValue.LOFI_NEO_SOUL: DescribedOption(
        StyleValue.LOFI_NEO_SOUL,
        "warm, dusty, chord-forward texture",
    ),
    StyleValue.AMBIENT_TAPE: DescribedOption(
        StyleValue.AMBIENT_TAPE,
        "spacious, hazy, slowly moving texture",
    ),
    StyleValue.RAINY_MELLOW: DescribedOption(
        StyleValue.RAINY_MELLOW,
        "rainy-day atmosphere, soft and subdued",
    ),
    StyleValue.JAZZ_VINYL: DescribedOption(
        StyleValue.JAZZ_VINYL,
        "brushed, tactile, lightly swinging texture",
    ),
    StyleValue.VINYL_DUST: DescribedOption(
        StyleValue.VINYL_DUST,
        "crackly, gritty beattape texture",
    ),
    StyleValue.NEON_RETRO: DescribedOption(
        StyleValue.NEON_RETRO,
        "bright 80s sheen, nostalgic glow",
    ),
}

LEGACY_FOCUS_VALUES = {value.value for value in FocusValue}

__all__ = [
    "DescribedOption",
    "ENERGY_OPTIONS",
    "EnergyLevel",
    "FOCUS_OPTIONS",
    "FocusOption",
    "FocusValue",
    "LEGACY_FOCUS_VALUES",
    "PRESET_OPTIONS",
    "PresetOption",
    "MusicPresetValue",
    "STYLE_OPTIONS",
    "StyleValue",
]
