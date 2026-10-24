from lofi_focus_tui.domain import EnergyLevel
from lofi_focus_tui.options import (
    ENERGY_OPTIONS,
    FOCUS_OPTIONS,
    LEGACY_FOCUS_VALUES,
    PRESET_OPTIONS,
    STYLE_OPTIONS,
    PresetVariant,
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


def test_every_preset_offers_ten_distinct_variants():
    for option in PRESET_OPTIONS.values():
        assert len(option.variants) == 10
        assert len(set(option.variants)) == len(option.variants)


def test_preset_variant_pools_are_exact():
    assert {
        value: option.variants for value, option in PRESET_OPTIONS.items()
    } == {
        "classic_lofi": (
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
        "neo_soul": (
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
        "ambient_tape": (
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
        "jazz_vinyl": (
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
        "lofi_house": (
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
        "synthwave": (
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
        "city_pop": (
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
        "boom_bap": (
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
        "peaceful_piano": (
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


def test_every_music_preset_names_its_genre_for_the_caption():
    expected = {
        "classic_lofi": "lo-fi hip hop",
        "neo_soul": "neo soul",
        "ambient_tape": "ambient",
        "jazz_vinyl": "jazz, vinyl",
        "lofi_house": "lo-fi house",
        "synthwave": "synthwave",
        "city_pop": "city pop",
        "boom_bap": "boom bap hip hop",
        "peaceful_piano": "peaceful piano",
    }
    assert {
        value: option.genre_tags for value, option in PRESET_OPTIONS.items()
    } == expected
