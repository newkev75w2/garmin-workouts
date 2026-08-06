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
from pathlib import Path

from .constants import (
    ISOLATION_CATEGORIES,
    ISOLATION_CEILING,
    OUTLIER_HIGH,
    OUTLIER_LOW,
    WEIGHT_CEILING,
    WORKING_SET_THRESHOLD,
)

ROOT = Path(__file__).resolve().parent.parent
STORE_PATH = ROOT / "performance.json"
HISTORY_PATH = ROOT / "history.json"

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

def session_summaries(store: dict) -> dict:
    """
    {EXERCISE_NAME: [session, ...]} oldest first, where each session is
    {date, top_weight, working_reps, total_reps, volume, sets}.
    """
    by_exercise = defaultdict(list)

    for act in store.get("activities", {}).values():
        grouped = defaultdict(list)
        for s in act.get("sets", []):
            if s.get("exercise") and s.get("reps"):
                grouped[s["exercise"]].append(s)

        for name, sets in grouped.items():
            weights = [s["weight_kg"] for s in sets if s.get("weight_kg")]
            top = max(weights) if weights else None

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
                    "working_reps": [s["reps"] for s in working],
                    "total_reps": sum(s["reps"] for s in sets),
                    "volume": round(
                        sum((s.get("weight_kg") or 0) * s["reps"] for s in sets), 1
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
