from lofi_focus_tui.domain import BackendStatus, EnergyLevel

PRESETS = ["deep_work", "reading", "coding", "wind_down"]
DURATIONS = [25, 30, 45, 60, 90]
ENERGIES = [EnergyLevel.LOW, EnergyLevel.STEADY, EnergyLevel.HIGH]
STYLE_TAG_SETS = ["lofi, neo_soul", "ambient, tape", "rainy, mellow", "jazz, vinyl"]


def cycle_value(values, current):
    index = values.index(current)
    return values[(index + 1) % len(values)]


def parse_style_tags(style_tags: str) -> list[str]:
    return [tag.strip() for tag in style_tags.split(",") if tag.strip()]


def render_status(status: BackendStatus) -> str:
    progress = round(status.progress * 100)
    chunk_line = ""
    if status.chunk_count > 1:
        chunk_line = f"\nchunks: {status.chunk_index}/{status.chunk_count}"
    return (
        f"state: {_enum_value(status.state)}\n"
        f"backend: {status.backend}  device: {status.device}\n"
        f"progress: {progress}%\n"
        f"message: {status.message}"
        f"{chunk_line}"
    )


def render_session(
    preset: str,
    duration_minutes: int,
    energy: EnergyLevel,
    style_tags: str,
) -> str:
    return (
        f"focus: {preset}\n"
        f"preset: {preset}\n"
        f"duration: {duration_minutes} minutes\n"
        f"energy: {_enum_value(energy)}\n"
        f"style: {style_tags}"
    )


def render_controls(status: BackendStatus) -> str:
    pause_label = "resume" if _enum_value(status.state) == "paused" else "pause"
    return f"s start  space {pause_label}  x stop  r refresh"


def render_history(status: BackendStatus) -> str:
    if not status.recent_sessions:
        return "recent:\n-"
    return "recent:\n" + "\n".join(status.recent_sessions[:5])


def _enum_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)
