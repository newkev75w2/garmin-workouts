"""
Running sessions, and how hard they actually were.

Strength is judged on load; running is judged on where the effort landed. The
distinction that matters for aerobic development is not pace but heart rate
relative to maximum, because the adaptations come from time spent in specific
zones rather than from distance covered.

The failure mode this exists to expose is the "grey zone": running everything at
a moderately-hard effort. It feels productive and is the worst of both worlds —
too hard to accumulate the easy volume that builds an aerobic base, too easy to
drive the peak adaptations that raise VO2max. Polarised training (roughly 80%
genuinely easy, 20% genuinely hard, little in between) is the well-supported
alternative, so this reports the split rather than just totalling kilometres.

Max heart rate is taken from the highest value actually observed, not from
220-age, which is a population average with a standard deviation of about 10
beats and is wrong for most individuals. Override it if a lab test says
otherwise.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

from .paths import data_home

RUNS_PATH = data_home() / "runs.json"

# Percentage of max heart rate. Boundaries follow the common five-zone model.
ZONES = [
    ("Z1 recovery", 0.00, 0.68),
    ("Z2 easy", 0.68, 0.78),
    ("Z3 moderate", 0.78, 0.87),
    ("Z4 threshold", 0.87, 0.92),
    ("Z5 vo2max", 0.92, 2.00),
]

# What a polarised week aims for: mostly easy, a real minority hard, little between.
POLARISED_EASY = 0.75
POLARISED_GREY_MAX = 0.20


def _load() -> dict:
    if not RUNS_PATH.exists():
        return {"runs": {}, "vo2max": {}}
    return json.loads(RUNS_PATH.read_text(encoding="utf-8"))


def _save(data: dict) -> None:
    RUNS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def zone_for(avg_hr: float | None, max_hr: float | None) -> str | None:
    if not avg_hr or not max_hr:
        return None
    fraction = avg_hr / max_hr
    for name, low, high in ZONES:
        if low <= fraction < high:
            return name
    return ZONES[-1][0]


def observed_max_hr(runs: dict) -> float | None:
    """Highest heart rate ever recorded, across every run on file."""
    values = [r["max_hr"] for r in runs.values() if r.get("max_hr")]
    return max(values) if values else None


def sync_runs(limit: int = 200, client=None) -> dict:
    """Pull running activities and the VO2max series that goes with them."""
    from .client import get_client

    client = client or get_client()
    data = _load()

    activities = client.get_activities(0, limit)
    runs = [
        a for a in activities
        if a.get("activityType", {}).get("typeKey") == "running"
    ]

    added = 0
    for a in runs:
        key = str(a["activityId"])
        if key in data["runs"]:
            continue
        distance_km = round((a.get("distance") or 0) / 1000, 2)
        minutes = round((a.get("duration") or 0) / 60, 1)
        data["runs"][key] = {
            "date": (a.get("startTimeLocal") or "")[:10],
            "name": a.get("activityName", ""),
            "km": distance_km,
            "minutes": minutes,
            "avg_hr": a.get("averageHR"),
            "max_hr": a.get("maxHR"),
            "pace_min_per_km": round(minutes / distance_km, 2) if distance_km else None,
        }
        added += 1

    # VO2max is the outcome the training is aiming at, so keep the series next
    # to the sessions that produced it. Garmin only recomputes it on days with a
    # qualifying run, so sampling a regular calendar interval mostly returns
    # nothing — ask on the run dates themselves.
    for day in sorted({r["date"] for r in data["runs"].values()} | {date.today().isoformat()}):
        if day in data["vo2max"]:
            continue
        try:
            payload = client.get_max_metrics(day)
        except Exception:
            continue
        if isinstance(payload, list) and payload:
            generic = payload[0].get("generic") or {}
            value = generic.get("vo2MaxPreciseValue") or generic.get("vo2MaxValue")
            if value:
                data["vo2max"][generic.get("calendarDate", day)] = value

    _save(data)
    return {"added": added, "total": len(data["runs"]), "data": data}


SUGGESTED_ENDPOINT = "/workout-service/workout/suggested/{sport}"


def garmin_suggested(sport: str = "RUNNING", client=None) -> list:
    """
    Garmin's own daily suggested workouts, if it has any.

    Garmin generates these from training status and recent training load. It
    returns an empty list rather than an error when it has nothing to offer —
    which is the normal case for anyone training too infrequently for it to
    establish a load trend, so an empty result is not a failure and must not be
    reported as one.
    """
    from .client import get_client

    client = client or get_client()
    try:
        result = client.connectapi(SUGGESTED_ENDPOINT.format(sport=sport))
    except Exception:
        return []
    return result if isinstance(result, list) else []


def summarise_suggested(item: dict) -> dict:
    """Flatten one of Garmin's suggestions into the shape the planner uses."""
    segments = item.get("workoutSegments") or [{}]
    steps = segments[0].get("workoutSteps") or []
    seconds = sum(
        s.get("endConditionValue") or 0
        for s in steps
        if (s.get("endCondition") or {}).get("conditionTypeKey") == "time"
    )
    return {
        "name": item.get("workoutName") or "Garmin suggested run",
        "description": item.get("description") or "",
        "minutes": round(seconds / 60) if seconds else None,
        "steps": len(steps),
        "workout_id": item.get("workoutId"),
    }


def distribution(days: int = 90, max_hr: float | None = None) -> dict:
    """Where the last `days` of running effort actually landed."""
    data = _load()
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    runs = {k: r for k, r in data["runs"].items() if r["date"] >= cutoff}
    if not runs:
        return {}

    ceiling = max_hr or observed_max_hr(data["runs"])
    buckets = {name: [] for name, _, _ in ZONES}
    unzoned = []

    for run in runs.values():
        zone = zone_for(run.get("avg_hr"), ceiling)
        (buckets[zone] if zone else unzoned).append(run)

    total = sum(len(v) for v in buckets.values())
    easy = sum(len(buckets[z]) for z in ("Z1 recovery", "Z2 easy"))
    grey = len(buckets["Z3 moderate"])
    hard = sum(len(buckets[z]) for z in ("Z4 threshold", "Z5 vo2max"))

    return {
        "max_hr": ceiling,
        "days": days,
        "runs": total,
        "km": round(sum(r["km"] for r in runs.values()), 1),
        "minutes": round(sum(r["minutes"] for r in runs.values())),
        "buckets": {name: len(runs_) for name, runs_ in buckets.items()},
        "easy": easy,
        "grey": grey,
        "hard": hard,
        "easy_share": round(easy / total, 2) if total else 0,
        "grey_share": round(grey / total, 2) if total else 0,
        "unzoned": len(unzoned),
    }


def vo2max_trend() -> list:
    """[(date, value), ...] oldest first."""
    data = _load()
    return sorted(data["vo2max"].items())


def advice(dist: dict | None = None) -> list:
    """
    What the distribution says to change, most important first.

    Deliberately blunt about the grey zone, because it is the most common way to
    train consistently and improve slowly, and it does not feel like a mistake
    while you are doing it.
    """
    dist = distribution() if dist is None else dist
    if not dist or not dist["runs"]:
        return ["No runs on file yet — sync first."]

    notes = []

    if dist["easy_share"] < POLARISED_EASY:
        notes.append(
            f"only {dist['easy']} of {dist['runs']} runs were genuinely easy "
            f"({dist['easy_share']:.0%}; aim for ~{POLARISED_EASY:.0%}) — the easy "
            "ones are what build the aerobic base, and they have to feel too slow"
        )

    if dist["grey_share"] > POLARISED_GREY_MAX:
        notes.append(
            f"{dist['grey']} of {dist['runs']} sat in Z3, the grey zone "
            f"({dist['grey_share']:.0%}) — hard enough to cost recovery, not hard "
            "enough to drive VO2max. Push those either down to Z2 or up to Z4/Z5"
        )

    if dist["hard"] == 0:
        notes.append(
            "no Z4/Z5 work at all — VO2max responds to genuine intervals "
            "(e.g. 5x3min at ~93% max HR with equal recovery)"
        )

    weekly_km = dist["km"] / (dist["days"] / 7)
    if weekly_km < 15:
        notes.append(
            f"averaging {weekly_km:.0f}km a week — at this volume consistency "
            "matters more than session design"
        )

    return notes or ["Distribution looks reasonable — keep it there."]
