"""
Turning one exercise's session history into a verdict and a next step.
"""

from __future__ import annotations

from .constants import (
    MEANINGFUL_DROP,
    MUSCLE_CATEGORIES,
    STALE_DAYS,
    STALL_SESSIONS,
)
from .store import days_since, load_store, prescribed_reps, session_summaries

ADHERENCE_GAP = 3  # reps of slack before a prescription counts as mis-set


def load_increment(weight: float | None) -> float:
    """Next sensible jump. Bigger lifts tolerate bigger steps."""
    if not weight:
        return 0.0
    if weight >= 60:
        return 5.0
    if weight >= 30:
        return 2.5
    if weight >= 12:
        return 2.0
    return 1.0


def prescription_advice(sessions: list, target: int | None, unit: str) -> str | None:
    """
    Whether the number we asked for matched what actually happened.

    Prescribing 15 and getting 10 every time is not the lifter failing, it is
    the prescription being wrong — and repeating it just repeats the miss. The
    same applies upwards: consistently beating the target means the target is
    too soft. Only fires on a gap wide enough not to be noise, and only when
    two sessions agree, so one bad day does not rewrite the programme.
    """
    if not target:
        return None

    recent = [s for s in sessions[-2:] if s["working_reps"]]
    if len(recent) < 2:
        return None

    achieved = [min(s["working_reps"]) for s in recent]
    if all(a <= target - ADHERENCE_GAP for a in achieved):
        realistic = max(achieved)
        return (
            f"asked for {target}{unit}, got {'/'.join(str(a) for a in achieved)} "
            f"twice — prescribe {realistic}{unit} next time, not {target}"
        )
    if all(a >= target + ADHERENCE_GAP for a in achieved):
        return (
            f"asked for {target}{unit}, got {'/'.join(str(a) for a in achieved)} "
            f"twice — the target is too soft, raise it or add load"
        )
    return None


def judge(name: str, sessions: list, targets: dict) -> dict:
    """Verdict + concrete next prescription for one exercise."""
    latest = sessions[-1]
    # Comparisons run against clean sessions only; suspect ones stay in the
    # record (and get surfaced) but never drive a verdict.
    clean = [s for s in sessions if not s["suspect"]]
    reps_only = name.startswith("BODY_WEIGHT")

    target = targets.get(name) or (
        max(latest["working_reps"]) if latest["working_reps"] else None
    )
    hit_target = bool(
        target and latest["working_reps"] and min(latest["working_reps"]) >= target
    )
    stale = days_since(latest["date"]) >= STALE_DAYS

    basis = clean[-1] if clean else None
    prior = clean[-2] if len(clean) > 1 else None

    # How many consecutive clean sessions sat at this exact top weight?
    same_weight_run = 0
    if basis:
        for s in reversed(clean):
            if s["top_weight"] == basis["top_weight"]:
                same_weight_run += 1
            else:
                break

    if latest["suspect"]:
        verdict = "check-data"
    elif stale:
        verdict = "stale"
    elif reps_only:
        # Garmin logs bodyweight movements inconsistently (sometimes bodyweight,
        # sometimes added or assist load), so load comparisons are meaningless.
        if prior and latest["total_reps"] > prior["total_reps"]:
            verdict = "progressing"
        elif hit_target:
            verdict = "ready"
        else:
            verdict = "holding"
    elif prior is None or basis is None:
        verdict = "baseline"
    elif basis["top_weight"] and prior["top_weight"]:
        drop_kg = prior["top_weight"] - basis["top_weight"]
        drop_pct = drop_kg / prior["top_weight"]
        # A drop only counts if it clears both a percentage floor and one load
        # increment — otherwise a single pin on a cable stack reads as decline.
        real_drop = drop_pct > MEANINGFUL_DROP and drop_kg > load_increment(
            prior["top_weight"]
        )
        if basis["top_weight"] > prior["top_weight"]:
            verdict = "progressing"
        elif real_drop:
            verdict = "regressed"
        elif basis["total_reps"] > prior["total_reps"]:
            verdict = "progressing"
        elif same_weight_run >= STALL_SESSIONS and not hit_target:
            verdict = "stalled"
        elif hit_target:
            verdict = "ready"
        else:
            verdict = "holding"
    else:
        verdict = "ready" if hit_target else "holding"

    w = f"{latest['top_weight']}kg" if latest["top_weight"] else "bodyweight"

    if verdict == "check-data":
        suggestion = (
            f"logged figure looks off ({latest['suspect_reason']}) — "
            "confirm what you actually lifted before changing anything"
        )
    elif verdict == "stale":
        suggestion = (
            f"not trained in {days_since(latest['date'])} days — "
            f"restart around {w} and rebuild from there"
        )
    elif verdict in ("ready", "progressing") and hit_target:
        if reps_only or not latest["top_weight"]:
            suggestion = f"add reps -> aim {target + 2}"
        else:
            bump = load_increment(latest["top_weight"])
            suggestion = (
                f"add {bump}kg -> {round(latest['top_weight'] + bump, 1)}kg x {target}"
            )
    elif verdict == "stalled":
        suggestion = (
            f"stuck at {basis['top_weight']}kg for {same_weight_run} sessions — "
            "swap the variation or drop to a lower rep range"
        )
    elif verdict == "regressed":
        suggestion = (
            f"down from {prior['top_weight']}kg to {basis['top_weight']}kg — "
            "hold here and rebuild, or check the log was right"
        )
    elif verdict == "baseline":
        suggestion = f"only one clean session — repeat {w} to establish a baseline"
    elif verdict == "progressing":
        # Reps are trending up but not every set is at target yet, so the load
        # stays put — say that without it reading as a contradiction.
        suggestion = f"reps trending up — stay at {w} until all sets reach {target}"
    else:
        suggestion = f"hold {w}, complete all sets at {target} reps first"

    unit = latest.get("unit", "reps")
    return {
        "exercise": name,
        "category": latest["category"],
        "unit": unit,
        "unit_suffix": "s" if unit == "s" else "",
        "timed": latest.get("timed", False),
        "adherence": prescription_advice(sessions, target, "s" if unit == "s" else ""),
        "verdict": verdict,
        "target_reps": target,
        "hit_target": hit_target,
        "last_date": latest["date"],
        "last_weight": latest["top_weight"],
        "last_reps": latest["working_reps"],
        "sessions": len(sessions),
        "clean_sessions": len(clean),
        "suspect_reason": latest["suspect_reason"],
        "days_ago": days_since(latest["date"]),
        "suggestion": suggestion,
    }


def analyze(muscles: list | None = None) -> list:
    """Public entry point — also what the skill calls to inform new workouts."""
    store = load_store()
    targets = prescribed_reps()
    results = [
        judge(name, sessions, targets)
        for name, sessions in session_summaries(store).items()
    ]

    if muscles:
        wanted = set()
        for m in muscles:
            wanted |= MUSCLE_CATEGORIES.get(m.lower(), set())
        results = [r for r in results if r["category"] in wanted]

    order = {"stalled": 0, "regressed": 1, "ready": 2, "progressing": 3,
             "holding": 4, "baseline": 5, "stale": 6, "check-data": 7}
    results.sort(key=lambda r: (order.get(r["verdict"], 9), r["exercise"]))
    return results
