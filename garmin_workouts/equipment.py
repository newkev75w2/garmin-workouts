"""
What the athlete's gym actually has.

Without this, programming variety means guessing: suggest a leg extension and it
may not exist, or never suggest one that does. Neither failure is visible from
the training history — an exercise absent from the log might be unavailable, or
might simply never have been chosen, and those need different responses.

Deliberately a plain editable file rather than anything clever. Gym inventories
change, nobody wants to maintain a database, and a list that is easy to correct
stays accurate longer than one that is hard to.
"""

from __future__ import annotations

import json

from .paths import data_home

EQUIPMENT_PATH = data_home() / "equipment.json"

TEMPLATE = {
    "gym": "",
    "has": [],
    "lacks": [],
    "limits": {},   # e.g. {"dumbbell_kg": 50} — the heaviest that exists
    "source": "",   # where this came from, so its reliability is visible
    "notes": "",
}


def load() -> dict:
    if not EQUIPMENT_PATH.exists():
        return dict(TEMPLATE)
    data = json.loads(EQUIPMENT_PATH.read_text(encoding="utf-8"))
    return {**TEMPLATE, **data}


def save(data: dict) -> None:
    EQUIPMENT_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def available(item: str) -> bool | None:
    """
    Whether a piece of kit is there.

    Three answers, not two: True, False, and None for "not recorded". None must
    not be treated as absent — an unrecorded machine is unknown, and refusing to
    prescribe something the gym has is as unhelpful as prescribing something it lacks.
    """
    data = load()
    key = item.strip().lower()
    if any(key == h.strip().lower() for h in data["has"]):
        return True
    if any(key == l.strip().lower() for l in data["lacks"]):
        return False
    return None


def exceeds_limit(exercise: str, weight: float) -> str | None:
    """
    Whether a logged weight is impossible at this gym.

    A figure above what the gym owns is not a strong lift, it is a logging
    convention problem — a dumbbell press recorded at 52kg where the heaviest
    dumbbell is 50kg was recorded as the pair, not per hand. That is worth
    saying, because every verdict compares an exercise against its own history
    and mixed conventions corrupt it.
    """
    limits = load().get("limits") or {}
    ceiling = limits.get("dumbbell_kg")
    if ceiling and "DUMBBELL" in exercise.upper() and weight > ceiling:
        return (
            f"{weight}kg exceeds the heaviest dumbbell here ({ceiling}kg) — "
            "this looks like the pair total rather than one dumbbell"
        )
    return None


def unused_kit(store: dict | None = None, days: int = 45) -> list:
    """
    Equipment the gym has that has not been touched lately.

    This is the variety prompt: kit sitting unused is where a session can change
    shape without inventing anything the gym does not own.
    """
    from datetime import date, timedelta

    from . import store as _store

    data = load()
    if not data["has"]:
        return []

    store = store if store is not None else _store.read_store()
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    recent = {
        (s.get("exercise") or "").lower()
        for act in store.get("activities", {}).values()
        if act.get("date", "") >= cutoff
        for s in act.get("sets", [])
    }

    idle = []
    for item in data["has"]:
        token = item.strip().lower().replace(" ", "_")
        if not any(token in name for name in recent if name):
            idle.append(item)
    return idle
