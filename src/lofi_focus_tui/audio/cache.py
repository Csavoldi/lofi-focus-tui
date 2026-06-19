from pathlib import Path


def default_cache_dir() -> Path:
    path = Path.home() / ".cache" / "lofi-focus-tui"
    path.mkdir(parents=True, exist_ok=True)
    return path
