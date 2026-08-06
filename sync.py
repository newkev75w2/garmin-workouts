#!/usr/bin/env python3
"""
Pull completed strength sessions down from Garmin Connect into performance.json.

    python sync.py            # last 30 activities
    python sync.py 100        # look further back

This is the "what actually happened" half of the loop. history.json records what
was *prescribed*; performance.json records what was *lifted* — reps and weight
per set, straight off the watch. coach.py reads this to judge progression.

Notes on the data Garmin gives back:
  - weight arrives in grams and is stored here in kg.
  - exercise names are the watch's own detection (it reports a confidence, and
    for workouts pushed by upload.py it also reports wktStepIndex, which maps
    back to the prescribed step). Both are kept so coach.py can prefer the
    prescription over auto-detection when they disagree.
  - sets with setType REST are dropped; only ACTIVE working sets are stored.
  - warmup sets are NOT filtered here — that judgment belongs in coach.py, so
    this file stays a faithful record of the session.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from garmin_workouts.client import get_client

STORE_PATH = Path(__file__).resolve().parent / "performance.json"


def _load() -> dict:
    if not STORE_PATH.exists():
        return {"activities": {}}
    return json.loads(STORE_PATH.read_text(encoding="utf-8"))


def _save(store: dict) -> None:
    STORE_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")


def extract_sets(raw_sets: list) -> list:
    """Flatten Garmin's exerciseSets payload into plain per-set records."""
    out = []
    for s in raw_sets:
        if s.get("setType") != "ACTIVE":
            continue
        exercises = s.get("exercises") or []
        first = exercises[0] if exercises else {}
        grams = s.get("weight")
        out.append(
            {
                "exercise": first.get("name"),
                "category": first.get("category"),
                "confidence": first.get("probability"),
                "reps": s.get("repetitionCount"),
                "weight_kg": round(grams / 1000.0, 2) if grams else None,
                "duration_s": round(s["duration"], 1) if s.get("duration") else None,
                "step_index": s.get("wktStepIndex"),
                "start_time": s.get("startTime"),
            }
        )
    return out


def sync(limit: int = 30) -> dict:
    client = get_client()
    print(f"Connected as: {client.get_full_name()}")

    store = _load()
    activities = client.get_activities(0, limit)
    strength = [
        a
        for a in activities
        if a.get("activityType", {}).get("typeKey") == "strength_training"
    ]
    print(f"Found {len(strength)} strength sessions in the last {limit} activities.\n")

    added = 0
    for a in strength:
        aid = str(a["activityId"])
        if aid in store["activities"]:
            continue  # already pulled — re-syncing is idempotent

        try:
            raw = client.get_activity_exercise_sets(a["activityId"]) or {}
        except Exception as exc:
            print(f"  ! could not fetch sets for {a.get('activityName')}: {exc}")
            continue

        sets = extract_sets(raw.get("exerciseSets") or [])
        store["activities"][aid] = {
            "activity_id": a["activityId"],
            "date": (a.get("startTimeLocal") or "")[:10],
            "name": a.get("activityName", ""),
            "sets": sets,
        }
        added += 1
        weighted = sum(1 for s in sets if s["weight_kg"])
        print(
            f"  + {store['activities'][aid]['date']}  "
            f"{a.get('activityName','')[:30]:<32} "
            f"{len(sets)} sets ({weighted} with weight)"
        )

    _save(store)
    print(
        f"\n{added} new session(s) added. "
        f"{len(store['activities'])} total in {STORE_PATH.name}."
    )
    if added:
        print("Run `python coach.py` to see how you're progressing.")
    return store


def main():
    parser = argparse.ArgumentParser(
        description="Pull completed strength sessions from Garmin Connect."
    )
    parser.add_argument(
        "limit", nargs="?", type=int, default=30,
        help="how many recent activities to scan (default 30)",
    )
    sync(parser.parse_args().limit)


if __name__ == "__main__":
    main()
