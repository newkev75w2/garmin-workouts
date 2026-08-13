"""
Which piece of kit each exercise needs, and whether the order makes sense in a gym.

A workout that reads fine on paper can be miserable to run. Going bench, bench,
cable, bench means walking away from a bench mid-session and finding it taken —
and in a busy gym that is the difference between the session you planned and the
one you get.

The fix is not to reorder freely: heaviest compounds still belong first, while
the lifter is fresh. So exercises are grouped by station *within* their effort
tier, which keeps the training logic intact and removes the walking.

Station is inferred from the exercise name because Garmin's FIT categories
describe the movement, not the equipment: BENCH_PRESS covers both a barbell on a
flat bench and a dumbbell press, which are the same category and different
stations.
"""

from __future__ import annotations

# Checked in order — the first match wins, so more specific patterns come first.
STATION_RULES = [
    ("cable", ("CABLE", "PULLDOWN", "PUSHDOWN", "FACE_PULL", "CROSSOVER", "PRESSDOWN")),
    ("machine", ("MACHINE", "LEG_PRESS", "PEC_DECK", "LEG_CURL", "LEG_EXTENSION",
                 "SMITH", "HACK_SQUAT")),
    ("rack", ("BARBELL_SQUAT", "BACK_SQUAT", "FRONT_SQUAT", "OVERHEAD_BARBELL",
              "BARBELL_SHOULDER_PRESS")),
    ("bench", ("BENCH_PRESS", "FLYE", "SEATED_DUMBBELL", "INCLINE_DUMBBELL",
               "PREACHER", "SEATED_REAR", "CONCENTRATION")),
    ("bar", ("PULL_UP", "CHIN_UP", "HANGING", "DIP")),
    ("barbell", ("BARBELL", "DEADLIFT", "CLEAN", "SHRUG", "EZ_BAR")),
    ("floor", ("PLANK", "CRUNCH", "SIT_UP", "BRIDGE", "STRETCH", "PUSH_UP")),
    ("dumbbell", ("DUMBBELL", "KETTLEBELL", "LUNGE", "CARRY", "RAISE")),
]


def station_of(exercise: str) -> str:
    """Best guess at the kit an exercise needs."""
    name = exercise.upper()
    for station, patterns in STATION_RULES:
        if any(p in name for p in patterns):
            return station
    return "free"


def revisits(exercises: list) -> list:
    """
    Stations left and later returned to.

    Only a *return* counts. Moving through stations once is unavoidable and
    fine; coming back to one you already abandoned is the thing that costs a
    bench, and is what the athlete actually notices.
    """
    seen_order = [station_of(e["name"]) for e in exercises]
    found, visited, previous = [], set(), None

    for index, station in enumerate(seen_order):
        if station != previous:
            if station in visited:
                found.append(
                    {
                        "station": station,
                        "index": index,
                        "exercise": exercises[index]["name"],
                    }
                )
            visited.add(station)
            previous = station
    return found


def group_by_station(exercises: list) -> list:
    """
    Reorder so each station is visited once, without disturbing the training order.

    Exercises keep their relative order, and the stations themselves appear in
    the order they were first needed — so the heavy compound that opened the
    session still opens it, and everything else on that station follows it
    rather than being scattered through the workout.
    """
    order, buckets = [], {}
    for exercise in exercises:
        station = station_of(exercise["name"])
        if station not in buckets:
            buckets[station] = []
            order.append(station)
        buckets[station].append(exercise)

    return [exercise for station in order for exercise in buckets[station]]
