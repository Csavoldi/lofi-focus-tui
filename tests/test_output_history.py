import json
import wave

import numpy as np

from lofi_focus_tui.audio.output import OutputManager, slugify
from lofi_focus_tui.generation.base import GenerationResult
from lofi_focus_tui.history import HistoryStore, SessionRecord


def make_result() -> GenerationResult:
    return GenerationResult(
        audio=np.array([0.0, 0.25, -0.25], dtype=np.float32),
        sample_rate=22050,
        duration_seconds=1,
        metadata={"backend": "mock"},
    )


def test_slugify_uses_safe_bounded_directory_names():
    assert slugify("Deep Work!") == "deep_work"
    assert slugify("  !!!  ") == "session"
    assert slugify("A" * 80) == "a" * 40


def test_output_manager_creates_session_dir_with_safe_name(tmp_path):
    manager = OutputManager(tmp_path)

    directory = manager.create_session_dir("session-123456789", "Deep Work!")

    assert directory.exists()
    assert directory.name == "session-123456789_deep_work"


def test_output_manager_saves_valid_wav_and_metadata(tmp_path):
    manager = OutputManager(tmp_path)
    directory = manager.create_session_dir("session-1", "deep_work")
    result = make_result()
    metadata = {
        "seed": 123,
        "blueprint": {"session_id": "session-1", "tempo_bpm": 72},
    }

    audio_path = manager.save_wav(result, directory)
    metadata_path = manager.save_metadata(metadata, directory)

    assert audio_path.stat().st_size > 44
    with wave.open(str(audio_path), "rb") as wav:
        assert wav.getframerate() == 22050
        assert wav.getnchannels() == 1
        assert wav.getnframes() == 3

    saved_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert saved_metadata["seed"] == 123
    assert saved_metadata["blueprint"]["tempo_bpm"] == 72


def test_history_store_lists_newest_first_and_persists_favorites(tmp_path):
    store = HistoryStore(tmp_path / "history.jsonl")
    first = SessionRecord(
        session_id="session-1",
        preset="deep_work",
        created_at="2026-06-21T10:00:00+00:00",
        duration_seconds=30,
        audio_path="one.wav",
        metadata_path="one.json",
        seed=1,
        tags=["lofi"],
    )
    second = SessionRecord(
        session_id="session-2",
        preset="reading",
        created_at="2026-06-21T11:00:00+00:00",
        duration_seconds=60,
        audio_path="two.wav",
        metadata_path="two.json",
        seed=2,
        tags=["ambient"],
    )

    store.append(first)
    store.append(second)

    assert [record.session_id for record in store.list()] == ["session-2", "session-1"]
    assert store.mark_favorite("session-1") is True
    assert store.mark_favorite("missing") is False

    reloaded = HistoryStore(tmp_path / "history.jsonl")
    assert reloaded.find("session-1").favorite is True
    assert reloaded.list(limit=1)[0].session_id == "session-2"
