from lofi_focus_tui.domain import BackendStatus, EnergyLevel
from lofi_focus_tui.options import ENERGY_OPTIONS, FOCUS_OPTIONS, PRESET_OPTIONS, STYLE_OPTIONS

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


def render_status(status: BackendStatus) -> str:
    progress = round(status.progress * 100)
    chunk_line = ""
    if status.chunk_count > 1:
        chunk_line = f"\nchunks: {status.chunk_index}/{status.chunk_count}"
    return (
        f"state: {_enum_value(status.state)}\n"
        f"backend: {status.backend}  device: {status.device}\n"
        f"playback: {status.playback}\n"
        f"volume: {round(status.volume * 100)}%\n"
        f"position: {status.position_seconds:.1f}s / {status.duration_seconds:.1f}s\n"
        f"progress: {progress}%\n"
        f"message: {status.message}"
        f"{chunk_line}"
    )


def render_session(
    focus: str,
    preset: str,
    duration_minutes: int,
    energy: EnergyLevel,
    style_tags: str,
    prompt: str = "",
    vocal_mode: str = "instrumental",
) -> str:
    return (
        f"focus: {_enum_value(focus)} — {FOCUS_OPTIONS[focus].description}\n"
        f"preset: {_enum_value(preset)} — {PRESET_OPTIONS[preset].description}\n"
        f"duration: {duration_minutes} minutes\n"
        f"energy: {_enum_value(energy)} — {ENERGY_OPTIONS[energy].description}\n"
        f"style: {_enum_value(style_tags)} — {STYLE_OPTIONS[style_tags].description}\n"
        f"prompt: {prompt_summary(prompt)}\n"
        f"mode: {_enum_value(vocal_mode)}"
    )


def render_option_guide() -> str:
    sections = (
        ("focus", FOCUS_OPTIONS),
        ("music preset", PRESET_OPTIONS),
        ("energy", ENERGY_OPTIONS),
        ("style", STYLE_OPTIONS),
    )
    return "\n\n".join(
        f"{title}:\n"
        + "\n".join(
            f"- {_enum_value(value)} — {option.description}"
            for value, option in catalog.items()
        )
        for title, catalog in sections
    )


def render_controls(status: BackendStatus) -> str:
    pause_label = "resume" if _enum_value(status.state) == "paused" else "pause"
    return (
        f"s start  space {pause_label}  x stop  r refresh  [ ] volume  "
        ", . seek  0 restart  e export"
    )


def render_history(status: BackendStatus) -> str:
    if not status.recent_sessions:
        return "recent:\n-"
    return "recent:\n" + "\n".join(status.recent_sessions[:5])


def _enum_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)
