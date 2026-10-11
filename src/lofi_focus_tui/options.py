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
class PresetVariant:
    motif: str
    drum_feel: str
    bass_behavior: str


@dataclass(frozen=True, slots=True)
class PresetOption:
    value: MusicPresetValue
    description: str
    tempo_range: tuple[int, int]
    variants: tuple[PresetVariant, ...]


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
        (70, 90),
        (
            PresetVariant(
                "dusty electric-piano figure",
                "soft swung lofi backbeat",
                "round sustained bass",
            ),
            PresetVariant(
                "muted clean-guitar figure with tape wobble",
                "lazy swung drum loop",
                "soft rounded bass",
            ),
            PresetVariant(
                "muffled sampled melody",
                "dusty swung breakbeat",
                "warm rounded bass",
            ),
            PresetVariant(
                "soft music-box melody",
                "hazy swung beat with shuffled hats",
                "mellow round bass",
            ),
            PresetVariant(
                "rainy electric-piano figure",
                "slow swung backbeat",
                "deep soft bass",
            ),
            PresetVariant(
                "warm flute phrase",
                "gentle swung lofi groove",
                "round mellow bass",
            ),
            PresetVariant(
                "taped melodic-hook sample",
                "dusty mid-tempo swing",
                "soft subby bass",
            ),
            PresetVariant(
                "nostalgic bell melody",
                "loose swung drum loop",
                "rounded warm bass",
            ),
            PresetVariant(
                "dreamy synthesizer melody",
                "soft swung beat with vinyl dust",
                "mellow deep bass",
            ),
            PresetVariant(
                "wistful tape-warped piano figure",
                "laid-back swung backbeat",
                "smooth rounded bass",
            ),
        ),
    ),
    MusicPresetValue.NEO_SOUL: PresetOption(
        MusicPresetValue.NEO_SOUL,
        "warm chords, pocketed rhythm, mellow bass",
        (65, 85),
        (
            PresetVariant(
                "warm Rhodes-style chord figure",
                "pocketed neo-soul groove",
                "mellow melodic bass",
            ),
            PresetVariant(
                "silky clean-guitar chords",
                "laid-back pocket groove",
                "sliding melodic bass",
            ),
            PresetVariant(
                "gospel-tinged organ chords",
                "head-nod pocket groove",
                "deep melodic bass",
            ),
            PresetVariant(
                "velvet Rhodes chords with string swells",
                "smooth mid-tempo pocket groove",
                "round melodic bass",
            ),
            PresetVariant(
                "shimmering electric-piano chords",
                "relaxed swing-pocket groove",
                "warm melodic bass",
            ),
            PresetVariant(
                "lush wah-wah guitar licks",
                "head-bob pocket groove",
                "rolling melodic bass",
            ),
            PresetVariant(
                "mellow Rhodes-and-flute interplay",
                "silky slow-jam groove",
                "soft melodic bass",
            ),
            PresetVariant(
                "warm clavinet licks",
                "bouncy pocket groove",
                "plucky melodic bass",
            ),
            PresetVariant(
                "hazy vibraphone chords",
                "smooth pocket groove with soft brushes",
                "deep warm melodic bass",
            ),
            PresetVariant(
                "soulful sampled-chord stacks",
                "gently swinging pocket groove",
                "mellow round melodic bass",
            ),
        ),
    ),
    MusicPresetValue.AMBIENT_TAPE: PresetOption(
        MusicPresetValue.AMBIENT_TAPE,
        "sparse pulse, wide pads, tape haze",
        (60, 80),
        (
            PresetVariant(
                "sparse washed pad motif",
                "minimal soft pulse",
                "long sustained low movement",
            ),
            PresetVariant(
                "hazy field-recording drone",
                "barely-there soft pulse",
                "distant sustained low movement",
            ),
            PresetVariant(
                "gentle music-box motif",
                "weightless slow pulse",
                "soft sustained low movement",
            ),
            PresetVariant(
                "layered tape-warped synth pads",
                "slow breathing pulse",
                "deep sustained drone",
            ),
            PresetVariant(
                "warm analog drone swells",
                "drifting ambient pulse",
                "subsonic sustained movement",
            ),
            PresetVariant(
                "soft choral pad texture",
                "nearly still slow pulse",
                "warm sustained low movement",
            ),
            PresetVariant(
                "filtered rain-washed keys",
                "faint slow pulse",
                "muted sustained low movement",
            ),
            PresetVariant(
                "gauzy choir-and-tape texture",
                "weightless drifting pulse",
                "long deep low movement",
            ),
            PresetVariant(
                "shimmering bell overtones over pads",
                "glacial slow pulse",
                "cavernous sustained movement",
            ),
            PresetVariant(
                "dusty cassette-loop motif",
                "hazy minimal pulse",
                "warm sustained low movement",
            ),
        ),
    ),
    MusicPresetValue.JAZZ_VINYL: PresetOption(
        MusicPresetValue.JAZZ_VINYL,
        "brushed drums, jazz harmony, vinyl texture",
        (65, 85),
        (
            PresetVariant(
                "jazzy electric-piano motif",
                "brushed light swing",
                "warm upright-style movement",
            ),
            PresetVariant(
                "smoky saxophone phrase",
                "brushed mid-tempo swing",
                "walking upright bass movement",
            ),
            PresetVariant(
                "muted jazz-guitar motif",
                "soft brushed swing",
                "warm upright bass movement",
            ),
            PresetVariant(
                "late-night piano motif with lush voicings",
                "relaxed brush swing",
                "round upright movement",
            ),
            PresetVariant(
                "mellow vibraphone motif",
                "soft brush-and-rim swing",
                "walking upright bass movement",
            ),
            PresetVariant(
                "warm muted-trumpet phrase",
                "gentle swung brush pattern",
                "plump upright movement",
            ),
            PresetVariant(
                "soulful organ vamps",
                "lazy brushed swing",
                "deep walking bass movement",
            ),
            PresetVariant(
                "airy flute lead over jazz chords",
                "light brushed swing",
                "supple upright movement",
            ),
            PresetVariant(
                "taped piano-trio refrain",
                "brushed swing with soft ride",
                "warm sustained upright movement",
            ),
            PresetVariant(
                "dusty horn-section stab",
                "medium brushed swing",
                "firm walking upright movement",
            ),
        ),
    ),
    MusicPresetValue.LOFI_HOUSE: PresetOption(
        MusicPresetValue.LOFI_HOUSE,
        "washed chord stabs, four-on-the-floor, tape hiss",
        (110, 125),
        (
            PresetVariant(
                "washed chord-stab loop",
                "soft four-on-the-floor house kick",
                "deep rolling bassline",
            ),
            PresetVariant(
                "dubbed-out chord washes",
                "muffled four-on-the-floor kick",
                "dubby rolling bassline",
            ),
            PresetVariant(
                "warped organ-chord loop",
                "soft four-on-the-floor groove with shuffled hats",
                "bouncing deep bassline",
            ),
            PresetVariant(
                "dusty piano-chord loop",
                "tape-saturated four-on-the-floor kick",
                "warm rolling bassline",
            ),
            PresetVariant(
                "hazy chopped-sample texture",
                "muted thumping house groove",
                "deep pulsing bassline",
            ),
            PresetVariant(
                "filtered synth-string swells",
                "soft four-on-the-floor groove with offbeat hats",
                "smooth rolling bassline",
            ),
            PresetVariant(
                "lo-fi Rhodes-chord loop",
                "gently swinging four-on-the-floor kick",
                "round deep bassline",
            ),
            PresetVariant(
                "tape-warped acid bass hook",
                "muffled pumping house kick",
                "squelchy rolling bassline",
            ),
            PresetVariant(
                "misty pad washes with vinyl crackle",
                "steady soft house kick",
                "subsonic rolling bassline",
            ),
            PresetVariant(
                "glittering toy-piano loop",
                "laid-back four-on-the-floor groove",
                "bouncing warm bassline",
            ),
        ),
    ),
    MusicPresetValue.SYNTHWAVE: PresetOption(
        MusicPresetValue.SYNTHWAVE,
        "analog arps, gated drums, neon nostalgia",
        (80, 110),
        (
            PresetVariant(
                "analog synth arpeggio",
                "gated 80s drum machine",
                "pulsing synth bass",
            ),
            PresetVariant(
                "soaring analog pad theme",
                "steady 80s drum machine with gated snare",
                "smooth sliding synth bass",
            ),
            PresetVariant(
                "bright retro lead-melody arp",
                "crisp 80s drum machine",
                "driving synth bass",
            ),
            PresetVariant(
                "neon synth-brass stabs",
                "punchy gated drum machine",
                "driving octave synth bass",
            ),
            PresetVariant(
                "dreamy synth-bell melody",
                "soft 80s drum machine with gated reverb",
                "gliding synth bass",
            ),
            PresetVariant(
                "chrome analog arp with tape warble",
                "steady mid-tempo gated drums",
                "warm pulsing synth bass",
            ),
            PresetVariant(
                "airy analog pad theme",
                "relaxed 80s drum groove",
                "mellow synth bass",
            ),
            PresetVariant(
                "retro arcade-lead melody",
                "crisp gated drum machine with electronic hats",
                "bouncy synth bass",
            ),
            PresetVariant(
                "widescreen analog-string swells",
                "slow gated drum pulse",
                "deep sliding synth bass",
            ),
            PresetVariant(
                "pulsing sequencer motif",
                "tight 80s drum machine with rimshots",
                "rolling synth bass",
            ),
        ),
    ),
    MusicPresetValue.CITY_POP: PresetOption(
        MusicPresetValue.CITY_POP,
        "funky bass, bright keys, 80s sheen",
        (100, 115),
        (
            PresetVariant(
                "bright electric-piano lick",
                "light funk groove",
                "bouncy fingered bassline",
            ),
            PresetVariant(
                "mellow electric-piano theme",
                "smooth soft funk groove",
                "gliding fingered bassline",
            ),
            PresetVariant(
                "sparkling synth-key lick with string swells",
                "disco-tinged light funk groove",
                "pumping fingered bassline",
            ),
            PresetVariant(
                "warm saxophone phrase",
                "sleek mid-tempo city groove",
                "round fingered bassline",
            ),
            PresetVariant(
                "glassy Rhodes chords with brass flourishes",
                "upbeat light funk groove",
                "popping fingered bassline",
            ),
            PresetVariant(
                "tropical synth-key theme",
                "breezy soft funk groove",
                "smooth sliding bassline",
            ),
            PresetVariant(
                "airy flute lick over bright chords",
                "sunny light funk groove",
                "bouncy round bassline",
            ),
            PresetVariant(
                "velvety clean-guitar licks with chorus",
                "polished soft funk groove",
                "warm fingered bassline",
            ),
            PresetVariant(
                "shimmering marimba-like synth motif",
                "easygoing light funk groove",
                "nimble fingered bassline",
            ),
            PresetVariant(
                "nostalgic piano-and-strings theme",
                "gentle city-night groove",
                "mellow fingered bassline",
            ),
        ),
    ),
    MusicPresetValue.BOOM_BAP: PresetOption(
        MusicPresetValue.BOOM_BAP,
        "gritty breaks, sampled chops, vinyl grit",
        (75, 95),
        (
            PresetVariant(
                "sampled melodic chop",
                "dusty boom-bap break with a fat snare",
                "subby round bass",
            ),
            PresetVariant(
                "jazzy sampled horn stab",
                "head-nod boom-bap break",
                "deep round bass",
            ),
            PresetVariant(
                "filtered soul-sample loop",
                "crackling dusty boom-bap break",
                "warm round bass",
            ),
            PresetVariant(
                "chopped soul-sample hook",
                "hard-hitting boom-bap break",
                "thick round bass",
            ),
            PresetVariant(
                "muffled Rhodes sample loop",
                "shuffling boom-bap break",
                "deep rounded bass",
            ),
            PresetVariant(
                "gritty funk-sample riff",
                "punchy boom-bap break with crisp snare",
                "rolling round bass",
            ),
            PresetVariant(
                "melancholy piano-sample loop",
                "slow heavy boom-bap break",
                "sub-heavy round bass",
            ),
            PresetVariant(
                "bright bell-sample melody",
                "tight boom-bap break with swung hats",
                "soft round bass",
            ),
            PresetVariant(
                "wah-wah funk-guitar sample",
                "bouncy boom-bap break",
                "deep melodic round bass",
            ),
            PresetVariant(
                "orchestral soul-sample swell",
                "fat mid-tempo boom-bap break",
                "warm subby bass",
            ),
        ),
    ),
    MusicPresetValue.PEACEFUL_PIANO: PresetOption(
        MusicPresetValue.PEACEFUL_PIANO,
        "felt piano, dreamy pads, near-weightless",
        (60, 75),
        (
            PresetVariant(
                "soft felt-piano figure",
                "sparse gentle pulse",
                "sparse low piano notes",
            ),
            PresetVariant(
                "tender piano-and-strings figure",
                "barely-there gentle pulse",
                "warm low piano notes",
            ),
            PresetVariant(
                "dreamy piano-and-pad figure",
                "weightless gentle pulse",
                "soft low piano notes",
            ),
            PresetVariant(
                "slow lullaby piano motif",
                "almost still gentle pulse",
                "deep soft piano notes",
            ),
            PresetVariant(
                "rain-washed piano figure",
                "faint gentle pulse",
                "muted low piano notes",
            ),
            PresetVariant(
                "hymn-like piano chords",
                "serene slow pulse",
                "warm sustained piano notes",
            ),
            PresetVariant(
                "delicate piano-and-harp figure",
                "weightless slow pulse",
                "soft sustained low notes",
            ),
            PresetVariant(
                "wistful solo piano phrase",
                "spacious gentle pulse",
                "sparse deep piano notes",
            ),
            PresetVariant(
                "music-box-like piano twinkles",
                "hazy gentle pulse",
                "soft low piano notes",
            ),
            PresetVariant(
                "warm piano-with-choir-pad figure",
                "serene nearly still pulse",
                "round low piano notes",
            ),
        ),
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
    "PresetVariant",
    "MusicPresetValue",
    "STYLE_OPTIONS",
    "StyleValue",
]
