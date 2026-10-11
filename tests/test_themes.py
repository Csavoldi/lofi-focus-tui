from rich.style import Style

from lofi_focus_tui.tui.themes import DEFAULT_THEME, THEMES


def test_default_theme_exists():
    assert DEFAULT_THEME in THEMES


def test_all_theme_styles_are_parseable_by_rich():
    for theme in THEMES.values():
        for color in (
            theme.label,
            theme.value,
            theme.desc,
            theme.accent,
            theme.info,
            theme.ok,
            theme.error,
        ):
            Style.parse(color)


def test_theme_state_styles_cover_all_backend_states():
    states = {"idle", "planning", "generating", "ready", "playing", "paused", "error"}
    for theme in THEMES.values():
        assert set(theme.state_styles) == states


def test_theme_names_match_catalog_keys():
    for name, theme in THEMES.items():
        assert theme.name == name
