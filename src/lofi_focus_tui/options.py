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


class StyleValue(StrEnum):
    LOFI_NEO_SOUL = "lofi, neo_soul"
    AMBIENT_TAPE = "ambient, tape"
    RAINY_MELLOW = "rainy, mellow"
    JAZZ_VINYL = "jazz, vinyl"


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
        ["low density", "soft transitions", "no abrupt changes"],
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
    ),
    MusicPresetValue.NEO_SOUL: PresetOption(
        MusicPresetValue.NEO_SOUL,
        "warm chords, pocketed rhythm, mellow bass",
        "warm Rhodes-style chord figure",
        "pocketed neo-soul groove",
        "mellow melodic bass",
    ),
    MusicPresetValue.AMBIENT_TAPE: PresetOption(
        MusicPresetValue.AMBIENT_TAPE,
        "sparse pulse, wide pads, tape haze",
        "sparse washed pad motif",
        "minimal soft pulse",
        "long sustained low movement",
    ),
    MusicPresetValue.JAZZ_VINYL: PresetOption(
        MusicPresetValue.JAZZ_VINYL,
        "brushed drums, jazz harmony, vinyl texture",
        "jazzy electric-piano motif",
        "brushed light swing",
        "warm upright-style movement",
    ),
}

ENERGY_OPTIONS = {
    EnergyLevel.LOW: DescribedOption(
        EnergyLevel.LOW,
        "soft movement and a restrained pulse",
    ),
    EnergyLevel.STEADY: DescribedOption(
        EnergyLevel.STEADY,
        "balanced movement for ordinary focus work",
    ),
    EnergyLevel.HIGH: DescribedOption(
        EnergyLevel.HIGH,
        "more rhythmic momentum while remaining non-distracting",
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
        "soft atmosphere and subdued detail",
    ),
    StyleValue.JAZZ_VINYL: DescribedOption(
        StyleValue.JAZZ_VINYL,
        "brushed, tactile, lightly swinging texture",
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
