"""
Loading synced sessions and shaping them into per-exercise history.

This module decides what the data says happened, including which of it is
trustworthy. It holds no opinion about training -- that lives in judging.py
and planning.py.
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from datetime import date, datetime

from .paths import history_path, performance_path
from .constants import (
    ISOLATION_CATEGORIES,
    ISOLATION_CEILING,
    OUTLIER_HIGH,
    OUTLIER_LOW,
    WEIGHT_CEILING,
    WORKING_SET_THRESHOLD,
)

STORE_PATH = performance_path()
HISTORY_PATH = history_path()


def read_store() -> dict:
    """
    Current contents, or an empty store if nothing has been synced.

    Used by the sync itself, which must cope with the file not existing yet.
    Analysis should call load_store() instead so an empty store is an error
    rather than silently producing verdicts about nothing.
    """
    if not STORE_PATH.exists():
        return {"activities": {}}
    return json.loads(STORE_PATH.read_text(encoding="utf-8"))


def write_store(store: dict) -> None:
    STORE_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")


def load_store() -> dict:
    if not STORE_PATH.exists():
        raise SystemExit(
            f"No {STORE_PATH.name} yet — run `python sync.py` first to pull your "
            "completed sessions down from Garmin Connect."
        )
    return json.loads(STORE_PATH.read_text(encoding="utf-8"))


def prescribed_reps() -> dict:
    """{EXERCISE_NAME: reps} from the most recent prescription in history.json."""
    if not HISTORY_PATH.exists():
        return {}
    targets = {}
    for entry in json.loads(HISTORY_PATH.read_text(encoding="utf-8")):
        for ex in entry.get("exercises", []):
            if ex.get("reps"):
                targets[ex["name"]] = ex["reps"]  # later entries overwrite earlier
    return targets


TIMED_CATEGORIES = {"PLANK"}


def is_timed(name: str, sets: list) -> bool:
    """
    Whether this exercise is held for time rather than counted in reps.

    Garmin still collects a rep count for holds, so the category is the reliable
    signal — backed up by every set carrying a duration.
    """
    if sets and sets[0].get("category") in TIMED_CATEGORIES:
        return True
    if "PLANK" in name or "HOLD" in name:
        return all(s.get("duration_s") for s in sets)
    return False


def set_value(s: dict, timed: bool):
    """
    The number that actually means something for this set.

    Seconds for a timed hold, reps otherwise — falling back to duration when the
    watch recorded no rep count at all, so the set still counts for something
    rather than being dropped or landing in the maths as None.
    """
    if timed and s.get("duration_s"):
        return round(s["duration_s"])
    if s.get("reps"):
        return s["reps"]
    if s.get("duration_s"):
        return round(s["duration_s"])
    return None


def session_summaries(store: dict) -> dict:
    """
    {EXERCISE_NAME: [session, ...]} oldest first, where each session is
    {date, top_weight, working_reps, total_reps, volume, sets}.
    """
    by_exercise = defaultdict(list)

    for act in store.get("activities", {}).values():
        grouped = defaultdict(list)
        for s in act.get("sets", []):
            # A timed hold records a meaningless rep count — a real 45s plank
            # came back as 5, 7 and 12 "reps" — but its duration is accurate.
            # Keep those sets on duration instead of discarding them.
            if s.get("exercise") and (s.get("reps") or s.get("duration_s")):
                grouped[s["exercise"]].append(s)

        for name, sets in grouped.items():
            weights = [s["weight_kg"] for s in sets if s.get("weight_kg")]
            top = max(weights) if weights else None
            timed = is_timed(name, sets)

            if top:
                working = [
                    s
                    for s in sets
                    if s.get("weight_kg")
                    and s["weight_kg"] >= top * WORKING_SET_THRESHOLD
                ]
            else:
                working = sets  # bodyweight movement, every set counts

            by_exercise[name].append(
                {
                    "date": act["date"],
                    "category": sets[0].get("category"),
                    "top_weight": top,
                    "timed": timed,
                    "unit": "s" if timed else "reps",
                    # For a timed hold the useful number is seconds held, not the
                    # rep count the watch insists on collecting.
                    "working_reps": [v for v in (set_value(s, timed) for s in working)
                                     if v is not None],
                    "total_reps": sum(set_value(s, timed) or 0 for s in sets),
                    "volume": round(
                        sum((s.get("weight_kg") or 0) * (s.get("reps") or 0)
                            for s in sets), 1
                    ),
                    "num_sets": len(sets),
                    # sets recorded without a weight against them — a session
                    # built mostly from these isn't solid enough to judge on
                    "unweighted_sets": sum(1 for s in sets if not s.get("weight_kg")),
                }
            )

    for sessions in by_exercise.values():
        sessions.sort(key=lambda s: s["date"])
        flag_suspect_sessions(sessions)
    return dict(by_exercise)


def flag_suspect_sessions(sessions: list) -> None:
    """
    Mark sessions whose top weight can't be trusted, in place.

    Manual entry means a single session can read 16kg on a leg press that
    otherwise sits at 120-200kg. Comparing against that number produces a
    confident, wrong "you regressed" call, so anything far off the exercise's
    own median gets excluded from comparisons instead.
    """
    weights = [s["top_weight"] for s in sessions if s["top_weight"]]
    med = statistics.median(weights) if weights else None

    for s in sessions:
        reasons = []
        ceiling = (
            ISOLATION_CEILING
            if s.get("category") in ISOLATION_CATEGORIES
            else WEIGHT_CEILING
        )
        if s["top_weight"] and s["top_weight"] > ceiling:
            reasons.append(f"{s['top_weight']}kg is not a plausible load here")
        elif med and s["top_weight"]:
            if s["top_weight"] < med * OUTLIER_LOW:
                reasons.append(f"{s['top_weight']}kg far below usual {med:g}kg")
            elif s["top_weight"] > med * OUTLIER_HIGH:
                reasons.append(f"{s['top_weight']}kg far above usual {med:g}kg")
        # a session where most sets carry no weight tells us little
        if s["unweighted_sets"] and s["unweighted_sets"] >= s["num_sets"] / 2:
            reasons.append(f"{s['unweighted_sets']}/{s['num_sets']} sets logged without weight")
        s["suspect"] = bool(reasons)
        s["suspect_reason"] = "; ".join(reasons)


def unlabelled_work(store: dict) -> list:
    """
    Sets with real reps and weight that the watch never attached an exercise to.

    These would otherwise vanish from every verdict, and they are not trivial —
    they're often the heaviest sets of a session (the watch struggles to
    classify heavy barbell work), which can make a lift look like it regressed
    when the missing sets were the lift. Nothing here can be safely attributed
    to an exercise, so it is reported rather than guessed at.
    """
    out = []
    for act in store.get("activities", {}).values():
        sets = [
            s
            for s in act.get("sets", [])
            if not s.get("exercise") and s.get("reps") and s.get("weight_kg")
        ]
        if sets:
            out.append(
                {
                    "date": act["date"],
                    "name": act["name"],
                    "sets": [(s["reps"], s["weight_kg"]) for s in sets],
                    "top_weight": max(s["weight_kg"] for s in sets),
                }
            )
    out.sort(key=lambda x: x["date"], reverse=True)
    return out


def days_since(iso_date: str, as_of: date | None = None) -> int:
    """
    Days between a session and the day being planned for.

    `as_of` exists because "what should I train on Monday?" is a different
    question from "what should I train now" — by Monday, groups that are inside
    the recovery window today will have cleared it. Defaults to today.
    """
    try:
        reference = as_of or date.today()
        return (reference - datetime.strptime(iso_date, "%Y-%m-%d").date()).days
    except ValueError:
        return 0


def ever_performed(store: dict | None = None) -> set:
    """Every exercise name that appears anywhere in the synced history."""
    store = store if store is not None else read_store()
    return {
        s["exercise"]
        for act in store.get("activities", {}).values()
        for s in act.get("sets", [])
        if s.get("exercise")
    }


def never_done(names: list, store: dict | None = None) -> list:
    """
    Which of these the athlete has no record of ever doing.

    Judged against synced history, so an exercise done before syncing started
    reads as new. That is the safe direction: an unnecessary form video costs a
    few seconds, whereas silently programming an unfamiliar movement is how
    people load a lift they have never performed.
    """
    performed = ever_performed(store)
    return [n for n in names if n not in performed]


def demo_url(exercise: str) -> str:
    """A YouTube search for how to perform an exercise."""
    import urllib.parse

    query = exercise.lstrip("_").replace("_", " ").lower() + " proper form"
    return "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
