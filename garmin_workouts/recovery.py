"""
Sleep, HRV and Garmin's own training-readiness, as an input to planning.

Muscle recovery ("48h since you trained chest") is only half the picture. Two
nights of five hours' sleep with readiness in the 30s is a reason to train
lighter regardless of which muscles are fresh, and the watch already tracks all
of it.

This is deliberately advisory. It never blocks a session — it reports what the
numbers say and lets the caller weigh it, because a single bad night is normal
and the failure mode of a tool that refuses to programme is that you stop using
it. Garmin's own readiness score is preferred when present, since it already
folds in sleep, HRV, stress and recent load.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

from .paths import data_home

CACHE_PATH = data_home() / "recovery.json"

# Below this, Garmin considers you under-recovered. Its scale is 0-100.
READINESS_LOW = 40
READINESS_GOOD = 70
SLEEP_SHORT_HOURS = 6.0


def _cache() -> dict:
    if not CACHE_PATH.exists():
        return {"days": {}}
    return json.loads(CACHE_PATH.read_text(encoding="utf-8"))


def _save(data: dict) -> None:
    CACHE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _first_number(payload, *keys):
    """
    Find the first numeric value under any of `keys`, at any depth.

    Garmin nests these differently per endpoint — sleep duration lives at
    dailySleepDTO.sleepTimeSeconds, readiness at the top level — so the search
    has to descend through every dict, not only ones whose key already matched.
    """
    if isinstance(payload, list):
        payload = payload[0] if payload else {}
    if not isinstance(payload, dict):
        return None

    for key in keys:
        value = payload.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value

    for value in payload.values():
        if isinstance(value, (dict, list)):
            found = _first_number(value, *keys)
            if found is not None:
                return found
    return None


def fetch(days: int = 7, client=None) -> dict:
    """
    Pull the last `days` of recovery metrics and cache them.

    Every field is optional — these endpoints are undocumented and vary by
    device and library version, so a missing metric is normal and must not take
    the whole thing down.
    """
    from .client import get_client

    client = client or get_client()
    data = _cache()

    for offset in range(days):
        day = (date.today() - timedelta(days=offset)).isoformat()
        entry = data["days"].get(day, {})

        for field, call, keys in [
            ("readiness", client.get_training_readiness, ("score", "level")),
            ("sleep_hours", client.get_sleep_data, ("sleepTimeSeconds",)),
            ("body_battery", client.get_body_battery, ("charged", "bodyBatteryValue")),
            ("stress", client.get_all_day_stress, ("avgStressLevel", "overallStressLevel")),
        ]:
            if field in entry:
                continue
            try:
                value = _first_number(call(day), *keys)
            except Exception:
                value = None
            if field == "sleep_hours" and value:
                value = round(value / 3600, 1)
            if value is not None:
                entry[field] = value

        if entry:
            data["days"][day] = entry

    _save(data)
    return data


def recent(days: int = 3) -> dict:
    """Averages over the last few days, from whatever has been cached."""
    data = _cache()
    wanted = [(date.today() - timedelta(days=n)).isoformat() for n in range(days)]
    entries = [data["days"][d] for d in wanted if d in data["days"]]
    if not entries:
        return {}

    summary = {"days_seen": len(entries)}
    for field in ("readiness", "sleep_hours", "body_battery", "stress"):
        values = [e[field] for e in entries if field in e]
        if values:
            summary[field] = round(sum(values) / len(values), 1)
    return summary


def advice(summary: dict | None = None) -> str | None:
    """
    One line on whether the body is ready, or None when nothing stands out.

    Only speaks up when a number is genuinely off — an advisory that fires every
    day gets ignored, which is worse than not having it.
    """
    summary = recent() if summary is None else summary
    if not summary:
        return None

    readiness = summary.get("readiness")
    sleep = summary.get("sleep_hours")
    notes = []

    if readiness is not None and readiness < READINESS_LOW:
        notes.append(f"training readiness {readiness:g}/100")
    if sleep is not None and sleep < SLEEP_SHORT_HOURS:
        notes.append(f"averaging {sleep:g}h sleep")

    if not notes:
        if readiness is not None and readiness >= READINESS_GOOD:
            return f"recovery looks good (readiness {readiness:g}/100) — train as planned"
        return None

    return (
        f"{' and '.join(notes)} over the last {summary['days_seen']} day(s) — "
        "consider trimming a set or holding load rather than progressing today"
    )
