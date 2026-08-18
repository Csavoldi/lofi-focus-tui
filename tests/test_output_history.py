import json
import os
import wave

import numpy as np
import pytest

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


def test_output_manager_exports_audio_and_metadata_to_selected_directory(tmp_path):
    manager = OutputManager(tmp_path / "cache")
    source_dir = manager.create_session_dir("session-1", "deep_work")
    audio_path = manager.save_wav(make_result(), source_dir)
    metadata_path = manager.save_metadata({"seed": 123}, source_dir)

    exported_audio, exported_metadata = manager.export_session(
        audio_path,
        tmp_path / "exports" / "nested",
    )

    assert exported_audio == tmp_path / "exports" / "nested" / source_dir.name / "audio.wav"
    assert exported_metadata == tmp_path / "exports" / "nested" / source_dir.name / "metadata.json"
    assert exported_audio.read_bytes() == audio_path.read_bytes()
    assert exported_metadata.read_bytes() == metadata_path.read_bytes()


def test_output_manager_replaces_existing_export_files(tmp_path):
    manager = OutputManager(tmp_path / "cache")
    source_dir = manager.create_session_dir("session-1", "deep_work")
    audio_path = manager.save_wav(make_result(), source_dir)
    manager.save_metadata({"seed": 1}, source_dir)
    export_dir = tmp_path / "exports"
    manager.export_session(audio_path, export_dir)

    manager.save_metadata({"seed": 2}, source_dir)
    _, exported_metadata = manager.export_session(audio_path, export_dir)

    assert json.loads(exported_metadata.read_text(encoding="utf-8")) == {"seed": 2}


def test_output_manager_rejects_missing_export_source(tmp_path):
    manager = OutputManager(tmp_path / "cache")

    with pytest.raises(FileNotFoundError, match="audio file"):
        manager.export_session(tmp_path / "missing" / "audio.wav", tmp_path / "exports")


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


def test_history_atomic_write_failure_preserves_original_records(tmp_path, monkeypatch):
    path = tmp_path / "history.jsonl"
    store = HistoryStore(path)
    original = SessionRecord(
        session_id="session-1",
        preset="deep_work",
        created_at="2026-06-21T10:00:00+00:00",
        duration_seconds=30,
        audio_path="one.wav",
        metadata_path="one.json",
        seed=1,
        tags=["lofi"],
    )
    replacement = SessionRecord(
        session_id="session-2",
        preset="reading",
        created_at="2026-06-21T11:00:00+00:00",
        duration_seconds=60,
        audio_path="two.wav",
        metadata_path="two.json",
        seed=2,
        tags=["ambient"],
    )
    store.append(original)

    def fail_replace(source, target):
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        store.append(replacement)

    assert store.list() == [original]
    assert list(tmp_path.glob(".history.jsonl.*")) == []


def test_history_migrates_legacy_rows_without_rewriting_on_read(tmp_path):
    path = tmp_path / "history.jsonl"
    rows = [
        {"session_id": "legacy-deep-work", "preset": "deep_work"},
        {"session_id": "legacy-reading", "preset": "reading"},
        {"session_id": "legacy-coding", "preset": "coding"},
        {"session_id": "legacy-wind-down", "preset": "wind_down"},
        {"session_id": "music-classic_lofi", "preset": "classic_lofi"},
        {"session_id": "music-neo_soul", "preset": "neo_soul"},
        {"session_id": "music-ambient_tape", "preset": "ambient_tape"},
        {"session_id": "music-jazz_vinyl", "preset": "jazz_vinyl"},
        {"session_id": "unknown", "preset": "future_preset"},
    ]
    for index, row in enumerate(rows):
        row.update(
            created_at=f"2026-08-14T10:0{index}:00+00:00",
            duration_seconds=30,
            audio_path=f"{row['session_id']}.wav",
            metadata_path=f"{row['session_id']}.json",
            seed=index,
            tags=[],
        )
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    original_bytes = path.read_bytes()
    store = HistoryStore(path)

    records = {record.session_id: record for record in store.list(limit=20)}

    for focus in ("deep_work", "reading", "coding", "wind_down"):
        record = records[f"legacy-{focus.replace('_', '-')}"]
        assert (record.focus, record.preset, record.tags) == (focus, "classic_lofi", [])
    for preset in ("classic_lofi", "neo_soul", "ambient_tape", "jazz_vinyl"):
        record = records[f"music-{preset}"]
        assert (record.focus, record.preset, record.tags) == ("deep_work", preset, [])
    assert (records["unknown"].focus, records["unknown"].preset) == (
        "deep_work",
        "classic_lofi",
    )
    assert records["unknown"].tags == ["legacy_preset:future_preset"]
    assert path.read_bytes() == original_bytes

    assert store.mark_favorite("unknown") is True
    persisted = {
        row["session_id"]: row
        for row in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())
    }
    assert persisted["legacy-reading"]["focus"] == "reading"
    assert persisted["legacy-reading"]["preset"] == "classic_lofi"
    assert persisted["music-jazz_vinyl"]["focus"] == "deep_work"
    assert persisted["music-jazz_vinyl"]["preset"] == "jazz_vinyl"
    assert persisted["unknown"]["tags"] == ["legacy_preset:future_preset"]

    assert store.mark_favorite("unknown", favorite=False) is True
    persisted_again = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
    ]
    unknown = next(row for row in persisted_again if row["session_id"] == "unknown")
    assert unknown["tags"] == ["legacy_preset:future_preset"]


def test_history_preserves_tags_on_already_normalized_rows(tmp_path):
    path = tmp_path / "history.jsonl"
    row = {
        "session_id": "normalized",
        "focus": "reading",
        "preset": "ambient_tape",
        "created_at": "2026-08-14T11:00:00+00:00",
        "duration_seconds": 30,
        "audio_path": "normalized.wav",
        "metadata_path": "normalized.json",
        "seed": 1,
        "tags": ["keep", "legacy_preset:historic"],
    }
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    store = HistoryStore(path)

    record = store.find("normalized")
    assert record is not None
    assert (record.focus, record.preset, record.tags) == (
        "reading",
        "ambient_tape",
        ["keep", "legacy_preset:historic"],
    )

    assert store.mark_favorite("normalized") is True
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert (persisted["focus"], persisted["preset"], persisted["tags"]) == (
        "reading",
        "ambient_tape",
        ["keep", "legacy_preset:historic"],
    )


def test_history_migrates_null_focus_like_omitted_focus(tmp_path):
    path = tmp_path / "history.jsonl"
    rows = [
        {
            "session_id": "null-legacy",
            "focus": None,
            "preset": "reading",
            "created_at": "2026-08-14T12:00:00+00:00",
            "duration_seconds": 30,
            "audio_path": "null-legacy.wav",
            "metadata_path": "null-legacy.json",
            "seed": 1,
            "tags": [],
        },
        {
            "session_id": "null-music",
            "focus": None,
            "preset": "neo_soul",
            "created_at": "2026-08-14T12:01:00+00:00",
            "duration_seconds": 30,
            "audio_path": "null-music.wav",
            "metadata_path": "null-music.json",
            "seed": 2,
            "tags": [],
        },
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    records = {record.session_id: record for record in HistoryStore(path).list()}

    assert (records["null-legacy"].focus, records["null-legacy"].preset) == (
        "reading",
        "classic_lofi",
    )
    assert (records["null-music"].focus, records["null-music"].preset) == (
        "deep_work",
        "neo_soul",
    )


def test_history_migrates_unknown_rows_with_malformed_tags(tmp_path):
    path = tmp_path / "history.jsonl"
    rows = [
        {
            "session_id": "unknown-null-tags",
            "preset": "future_null",
            "created_at": "2026-08-14T12:00:00+00:00",
            "duration_seconds": 30,
            "audio_path": "unknown-null-tags.wav",
            "metadata_path": "unknown-null-tags.json",
            "seed": 1,
            "tags": None,
        },
        {
            "session_id": "unknown-string-tags",
            "preset": "future-string",
            "created_at": "2026-08-14T12:01:00+00:00",
            "duration_seconds": 30,
            "audio_path": "unknown-string-tags.wav",
            "metadata_path": "unknown-string-tags.json",
            "seed": 2,
            "tags": "not-a-list",
        },
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    store = HistoryStore(path)

    records = {record.session_id: record for record in store.list()}

    assert records["unknown-null-tags"].tags == ["legacy_preset:future_null"]
    assert records["unknown-string-tags"].tags == ["legacy_preset:future-string"]
    assert store.mark_favorite("unknown-null-tags") is True
    assert store.mark_favorite("unknown-string-tags") is True


def test_history_preserves_extra_fields_on_normal_rewrite(tmp_path):
    path = tmp_path / "history.jsonl"
    row = {
        "session_id": "with-extra",
        "focus": "reading",
        "preset": "ambient_tape",
        "created_at": "2026-08-14T13:00:00+00:00",
        "duration_seconds": 30,
        "audio_path": "with-extra.wav",
        "metadata_path": "with-extra.json",
        "seed": 1,
        "tags": [],
        "extra_field": {"source": "legacy"},
    }
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    store = HistoryStore(path)

    assert store.mark_favorite("with-extra") is True

    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["extra_field"] == {"source": "legacy"}


def test_history_filters_non_string_tags_before_migrating_unknown_row(tmp_path):
    path = tmp_path / "history.jsonl"
    row = {
        "session_id": "unknown-list-tags",
        "preset": "future-list",
        "created_at": "2026-08-14T14:00:00+00:00",
        "duration_seconds": 30,
        "audio_path": "unknown-list-tags.wav",
        "metadata_path": "unknown-list-tags.json",
        "seed": 1,
        "tags": [1, "keep", None, "also"],
    }
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    original_bytes = path.read_bytes()
    store = HistoryStore(path)

    record = store.find("unknown-list-tags")
    assert record is not None
    assert record.tags == ["keep", "also", "legacy_preset:future-list"]
    assert path.read_bytes() == original_bytes

    assert store.mark_favorite("unknown-list-tags") is True
    assert store.mark_favorite("unknown-list-tags", favorite=False) is True
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["tags"] == ["keep", "also", "legacy_preset:future-list"]


@pytest.mark.parametrize(
    ("preset", "expected_focus"),
    [("reading", "reading"), ("neo_soul", "deep_work")],
)
@pytest.mark.parametrize(
    ("raw_tags", "expected_tags"),
    [
        (None, []),
        ("not-a-list", []),
        ([1, None], []),
        (["first", 1, "second", None], ["first", "second"]),
    ],
)
def test_history_normalizes_tags_for_all_migration_branches(
    tmp_path, preset, expected_focus, raw_tags, expected_tags
):
    path = tmp_path / "history.jsonl"
    row = {
        "session_id": f"{preset}-{str(raw_tags)}",
        "preset": preset,
        "created_at": "2026-08-14T15:00:00+00:00",
        "duration_seconds": 30,
        "audio_path": "migration.wav",
        "metadata_path": "migration.json",
        "seed": 1,
        "tags": raw_tags,
    }
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    original_bytes = path.read_bytes()
    store = HistoryStore(path)

    record = store.find(row["session_id"])
    assert record is not None
    assert (record.focus, record.preset, record.tags) == (
        expected_focus,
        "classic_lofi" if preset == "reading" else preset,
        expected_tags,
    )
    assert path.read_bytes() == original_bytes

    assert store.mark_favorite(row["session_id"]) is True
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["tags"] == expected_tags
