"""
Naming the sets the watch recorded but could not identify.

The watch logs every set, but only names the ones it recognises. Anything added
mid-session, or any movement its classifier does not know, comes back with reps
and weight but no exercise — and is then invisible to every verdict. In a real
log that was 29 sets, frequently the heaviest of the day.

Labelling turns that back into training data. Consecutive unnamed sets are
grouped into blocks, because sets of one exercise arrive together; the athlete
names the block, and it counts from then on.

Names are validated against the FIT SDK before being written, so a label cannot
introduce an exercise that would later fail an upload.
"""

from __future__ import annotations

from . import store as _store


def blocks(date: str, store: dict | None = None) -> list:
    """
    Runs of consecutive unnamed sets in one session.

    Grouped by adjacency rather than by weight: sets of the same exercise are
    logged together, while weight often changes across them as the athlete ramps
    up, so splitting on weight would break one exercise into three.
    """
    store = store if store is not None else _store.read_store()
    found = []

    for activity in store.get("activities", {}).values():
        if activity.get("date") != date:
            continue

        current = []
        for index, s in enumerate(activity.get("sets", [])):
            unnamed = not s.get("exercise") and (s.get("reps") or s.get("duration_s"))
            if unnamed:
                current.append((index, s))
            elif current:
                found.extend(_split(activity, current))
                current = []
        if current:
            found.extend(_split(activity, current))

    return found


# Weight falling this far below the block's running peak reads as a new exercise
# rather than a drop set: you ramp up on one movement, then start the next one
# light again.
NEW_EXERCISE_DROP = 0.75


def _split(activity: dict, sets: list) -> list:
    """
    Break one run of unnamed sets where a new exercise plainly starts.

    Adjacent unnamed sets are usually one exercise, but two added back to back
    arrive as a single run. The giveaway is the weight pattern: ramping up and
    then dropping well below the peak means the next movement has begun.
    """
    groups, current, peak = [], [], 0.0

    for index, s in sets:
        weight = s.get("weight_kg") or 0
        if current and peak and weight and weight < peak * NEW_EXERCISE_DROP:
            groups.append(current)
            current, peak = [], 0.0
        current.append((index, s))
        peak = max(peak, weight)

    if current:
        groups.append(current)
    return [_describe(activity, g) for g in groups]


def _describe(activity: dict, sets: list) -> dict:
    return {
        "activity_id": activity.get("activity_id"),
        "name": activity.get("name", ""),
        "date": activity.get("date"),
        "indexes": [i for i, _ in sets],
        "sets": [
            {"reps": s.get("reps"), "weight_kg": s.get("weight_kg")} for _, s in sets
        ],
    }


def label(date: str, block_index: int, exercise: str, category: str,
          store: dict | None = None) -> dict:
    """
    Name one block of unnamed sets, in place.

    Returns the number of sets updated. Validates the exercise first — a label
    that is not a real FIT entry would be written into history and then fail the
    next upload that used it, which is worse than refusing now.
    """
    from . import validation

    errors = validation.validate_workout(
        {"exercises": [{"name": exercise, "category": category}]}
    )
    if errors:
        return {"updated": 0, "error": errors[0]}

    owned = store is None
    store = _store.read_store() if owned else store

    found = blocks(date, store)
    if block_index < 1 or block_index > len(found):
        return {"updated": 0, "error": f"no block {block_index} on {date}"}

    target = found[block_index - 1]
    updated = 0
    for activity in store.get("activities", {}).values():
        if activity.get("activity_id") != target["activity_id"]:
            continue
        for index in target["indexes"]:
            activity["sets"][index]["exercise"] = exercise
            activity["sets"][index]["category"] = category
            activity["sets"][index]["labelled"] = True
            updated += 1

    if owned and updated:
        _store.write_store(store)
    return {"updated": updated, "exercise": exercise, "sets": target["sets"]}
