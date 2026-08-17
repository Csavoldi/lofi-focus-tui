from rich.text import Text

from lofi_focus_tui.domain import BackendStatus, EnergyLevel
from lofi_focus_tui.options import ENERGY_OPTIONS, FOCUS_OPTIONS, PRESET_OPTIONS, STYLE_OPTIONS
from lofi_focus_tui.tui.themes import DEFAULT_THEME, THEMES, Theme

DURATIONS = [5, 25, 30, 45, 60, 90]


def cycle_value(values, current):
    values = list(values)
    return values[(values.index(current) + 1) % len(values)]


def parse_style_tags(style_tags: str) -> list[str]:
    return [tag.strip() for tag in style_tags.split(",") if tag.strip()]


def prompt_summary(prompt: str) -> str:
    prompt = prompt.strip()
    if not prompt:
        return "(category-generated)"
    return prompt if len(prompt) <= 80 else f"{prompt[:77]}..."


def _resolve_theme(theme: Theme | None) -> Theme:
    return theme or THEMES[DEFAULT_THEME]


def _field_line(label: str, value: str, value_style: str) -> Text:
    line = Text()
    line.append(f"{label}: ", style="dim")
    line.append(value, style=value_style)
    return line


def _option_line(label: str, value: str, description: str, theme: Theme) -> Text:
    line = Text()
    line.append(f"{label}: ", style=theme.label)
    line.append(value, style=theme.value)
    line.append(f" — {description}", style=theme.desc)
    return line


def _bar(fraction: float, width: int, theme: Theme) -> Text:
    filled = max(0, min(width, round(fraction * width)))
    bar = Text()
    bar.append("█" * filled, style=theme.accent)
    bar.append("░" * (width - filled), style=theme.label)
    return bar


def _bar_line(label: str, value: str, fraction: float, theme: Theme) -> Text:
    line = Text()
    line.append(f"{label}: ", style=theme.label)
    line.append(value, style=theme.value)
    line.append(" ")
    line.append(_bar(fraction, 10, theme))
    return line


def _join_lines(lines: list[Text]) -> Text:
    text = Text()
    for index, line in enumerate(lines):
        if index:
            text.append("\n")
        text.append(line)
    return text


def render_status(status: BackendStatus, theme: Theme | None = None) -> Text:
    theme = _resolve_theme(theme)
    progress = round(status.progress * 100)
    state = _enum_value(status.state)
    message_style = theme.error if state == "error" else theme.value
    lines = [
        _field_line("state", state, theme.state_styles.get(state, "")),
        _field_line("backend", f"{status.backend}  device: {status.device}", theme.value),
        _field_line("playback", status.playback, theme.value),
        _bar_line("volume", f"{round(status.volume * 100)}%", status.volume, theme),
        _field_line(
            "position",
            f"{status.position_seconds:.1f}s / {status.duration_seconds:.1f}s",
            theme.value,
        ),
        _bar_line("progress", f"{progress}%", status.progress, theme),
        _field_line("message", status.message, message_style),
    ]
    if status.chunk_count > 1:
        lines.append(
            _field_line("chunks", f"{status.chunk_index}/{status.chunk_count}", theme.value)
        )
    return _join_lines(lines)


def render_session(
    focus: str,
    preset: str,
    duration_minutes: int,
    energy: EnergyLevel,
    style_tags: str,
    prompt: str = "",
    vocal_mode: str = "instrumental",
    theme: Theme | None = None,
) -> Text:
    theme = _resolve_theme(theme)
    lines = [
        _option_line("theme", theme.name, theme.description, theme),
        _option_line("focus", _enum_value(focus), FOCUS_OPTIONS[focus].description, theme),
        _option_line("preset", _enum_value(preset), PRESET_OPTIONS[preset].description, theme),
        _field_line("duration", f"{duration_minutes} minutes", theme.value),
        _option_line(
            "energy", _enum_value(energy), ENERGY_OPTIONS[energy].description, theme
        ),
        _option_line(
            "style", _enum_value(style_tags), STYLE_OPTIONS[style_tags].description, theme
        ),
        _field_line("prompt", prompt_summary(prompt), theme.value),
        _field_line("mode", _enum_value(vocal_mode), theme.value),
    ]
    return _join_lines(lines)


def render_option_guide(theme: Theme | None = None) -> Text:
    theme = _resolve_theme(theme)
    sections = (
        ("focus", FOCUS_OPTIONS),
        ("music preset", PRESET_OPTIONS),
        ("energy", ENERGY_OPTIONS),
        ("style", STYLE_OPTIONS),
        ("theme", THEMES),
    )
    blocks = []
    for title, catalog in sections:
        block = Text()
        block.append(f"{title}:\n", style=theme.accent)
        for value, option in catalog.items():
            block.append("- ", style=theme.label)
            block.append(_enum_value(value), style=theme.value)
            block.append(f" — {option.description}\n", style=theme.desc)
        blocks.append(block)
    return _join_lines(blocks)


def render_controls(status: BackendStatus, theme: Theme | None = None) -> Text:
    theme = _resolve_theme(theme)
    pause_label = "resume" if _enum_value(status.state) == "paused" else "pause"
    pairs = (
        ("s", "start"),
        ("space", pause_label),
        ("x", "stop"),
        ("r", "refresh"),
        ("t", "theme"),
        ("[ ]", "volume"),
        (", .", "seek"),
        ("0", "restart"),
        ("e", "export"),
    )
    line = Text()
    for index, (key, label) in enumerate(pairs):
        if index:
            line.append("  ")
        line.append(key, style=theme.accent)
        line.append(f" {label}", style=theme.desc)
    return line


def render_history(status: BackendStatus, theme: Theme | None = None) -> Text:
    theme = _resolve_theme(theme)
    text = Text()
    text.append("recent:\n", style=theme.label)
    if not status.recent_sessions:
        text.append("-", style=theme.desc)
    else:
        for index, entry in enumerate(status.recent_sessions[:5]):
            if index:
                text.append("\n")
            text.append(entry, style=theme.value)
    return text


def _enum_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)
