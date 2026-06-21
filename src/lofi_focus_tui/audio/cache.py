from pathlib import Path


def default_cache_dir() -> Path:
    path = Path.home() / ".cache" / "lofi-focus-tui"
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_output_dir() -> Path:
    path = default_cache_dir() / "outputs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_history_path() -> Path:
    return default_cache_dir() / "history.jsonl"
