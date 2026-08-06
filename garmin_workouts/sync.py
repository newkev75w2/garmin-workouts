"""
Pulling completed strength sessions down from Garmin Connect.

history.json records what was *prescribed*; performance.json records what was
*lifted* — reps and weight per set, straight off the watch. store.py reads the
result and judging.py forms an opinion about it.

Notes on the data Garmin gives back:
  - weight arrives in grams and is stored here in kg.
  - exercise names are the watch's own detection, which reports a confidence and,
    for workouts pushed by upload.py, a wktStepIndex mapping back to the
    prescribed step. Both are kept so the analysis can prefer the prescription
    over auto-detection when they disagree.
  - sets with setType REST are dropped; only ACTIVE working sets are stored.
  - warmup sets are NOT filtered here. That judgement belongs in store.py, so
    this stays a faithful record of what the watch recorded.
"""

from __future__ import annotations

from .client import get_client
from .store import STORE_PATH, read_store, write_store


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

    store = read_store()
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

    write_store(store)
    print(
        f"\n{added} new session(s) added. "
        f"{len(store['activities'])} total in {STORE_PATH.name}."
    )
    if added:
        print("Run `python coach.py` to see how you're progressing.")
    return store
