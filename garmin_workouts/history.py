"""
Shared helpers for logging every uploaded workout to history.json and reading it
back. upload.py appends to this after each successful push; progress.py and the
Garmin-workout skill read from it to inform progression (reps/sets/rest trends)
in future sessions.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .paths import history_path

HISTORY_PATH = history_path()


def load() -> list:
    """Every uploaded session, oldest first."""
    if not HISTORY_PATH.exists():
        return []
    return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))


def _save(entries: list) -> None:
    HISTORY_PATH.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def log_session(workout_file: str, workout: dict) -> None:
    entries = load()
    entries.append(
        {
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "file": workout_file,
            "name": workout["name"],
            "description": workout.get("description", ""),
            "exercises": workout["exercises"],
        }
    )
    _save(entries)


def last_session_for(slug: str):
    """
    Most recent logged session whose file stem matches this muscle-group slug
    (e.g. slug="chest_shoulders" matches workouts/chest_shoulders_3.py). Returns
    None if nothing has been logged for that slug yet.
    """
    matches = [
        e for e in load() if Path(e["file"]).stem.rsplit("_", 1)[0] == slug
    ]
    return matches[-1] if matches else None
