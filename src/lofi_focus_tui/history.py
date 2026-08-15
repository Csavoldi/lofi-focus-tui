from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from lofi_focus_tui.options import LEGACY_FOCUS_VALUES, PRESET_OPTIONS, MusicPresetValue


class SessionRecord(BaseModel):
    session_id: str
    preset: str
    focus: str = "deep_work"
    created_at: str
    duration_seconds: int
    audio_path: str
    metadata_path: str
    favorite: bool = False
    seed: int
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_preset(cls, values):
        if not isinstance(values, dict) or "focus" in values:
            return values

        values = dict(values)
        preset = values.get("preset")
        if isinstance(preset, str) and preset in LEGACY_FOCUS_VALUES:
            values["focus"] = preset
            values["preset"] = MusicPresetValue.CLASSIC_LOFI.value
        elif isinstance(preset, str) and preset in PRESET_OPTIONS:
            values["focus"] = "deep_work"
        else:
            values["focus"] = "deep_work"
            values["preset"] = MusicPresetValue.CLASSIC_LOFI.value
            legacy_tag = f"legacy_preset:{preset}"
            tags = list(values.get("tags", []))
            if legacy_tag not in tags:
                tags.append(legacy_tag)
            values["tags"] = tags
        return values


class HistoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: SessionRecord) -> None:
        with self.path.open("a", encoding="utf-8") as history_file:
            history_file.write(record.model_dump_json() + "\n")

    def list(self, limit: int = 20) -> list[SessionRecord]:
        records = self._read_records()
        return list(reversed(records))[:limit]

    def mark_favorite(self, session_id: str, favorite: bool = True) -> bool:
        records = self._read_records()
        found = False
        updated = []
        for record in records:
            if record.session_id == session_id:
                record = record.model_copy(update={"favorite": favorite})
                found = True
            updated.append(record)
        if found:
            self._write_records(updated)
        return found

    def find(self, session_id: str) -> SessionRecord | None:
        for record in self._read_records():
            if record.session_id == session_id:
                return record
        return None

    def _read_records(self) -> list[SessionRecord]:
        if not self.path.exists():
            return []
        records = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(SessionRecord.model_validate(json.loads(line)))
        return records

    def _write_records(self, records: list[SessionRecord]) -> None:
        with self.path.open("w", encoding="utf-8") as history_file:
            for record in records:
                history_file.write(record.model_dump_json() + "\n")
