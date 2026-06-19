from lofi_focus_tui.prompt_safety import map_style_tags


def test_maps_artist_reference_to_descriptive_traits():
    traits = map_style_tags(["DEFTONES", "lofi"])

    joined = " ".join(traits).lower()
    assert "deftones" not in joined
    assert "downtuned" in joined
    assert "hazy" in joined
    assert "lofi" in joined


def test_maps_cultural_style_tags_without_vocals_by_default():
    traits = map_style_tags(["japanese rap", "wizard"])

    joined = " ".join(traits).lower()
    assert "percussive japanese hip hop texture" in joined
    assert "mystic modal ambience" in joined
    assert "vocals" not in joined
