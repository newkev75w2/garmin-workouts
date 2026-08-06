#!/usr/bin/env python3
"""
Judge performance from synced Garmin session data and suggest what to do next.

    python sync.py              # pull the data down first
    python coach.py             # verdict on every exercise
    python coach.py --muscles chest shoulders
    python coach.py --brief     # compact output, this is what the skill reads

How the judgment works
----------------------
For each exercise, in each session, the heaviest weight used is treated as the
working weight, and any set within 10% of it is a working set — that keeps
ramp-up/warmup sets from dragging the numbers down. Sessions are then compared
oldest-to-newest:

  progressing  top weight went up, or same weight for more total reps
  ready        every working set hit the rep target -> earn the next load jump
  holding      target not hit on every set yet -> stay at this weight
  stalled      same weight, no rep improvement, 3+ sessions -> change something
  regressed    top weight dropped meaningfully (>10%) vs the last clean session
  stale        not trained in 21+ days — judge it fresh rather than progress it
  baseline     only one usable session on record, nothing to compare against

The rep target is whatever upload.py last prescribed for that exercise (read
from history.json); for exercises never prescribed by this tool, it falls back
to the best rep count achieved in the most recent session.

Why this is defensive about the data
------------------------------------
The weight Garmin stores is whatever got entered on the watch, and in practice
that record is messy. Real examples from a 20-session log:

  - LEG_PRESS reads 120, 16, 130, 150, 200, 140 kg. The 16 is a fat-fingered
    entry, not a collapse in strength.
  - BODY_WEIGHT_DIP reads 9, 76, 72, 19 kg — the watch sometimes logs bodyweight
    and sometimes the added/assist load, so the two aren't comparable at all.
  - A session can record sets with no weight against them, leaving one lonely
    working set that isn't representative of the session.

So before judging, sessions whose top weight is wildly off that exercise's own
median (below 60% or above 180%) are marked suspect and excluded from the
comparison — they're reported, but they never trigger a "you regressed" verdict.
BODY_WEIGHT_* movements are judged on reps alone for the same reason. Without
these guards the analysis calls roughly a fifth of all exercises "regressed",
which is noise, and acting on it would mean cutting load that was never lost.

Dumbbell work carries a milder version of the same caveat (per-hand vs total
depends on how you log it), so every comparison here is an exercise against its
own history, never across exercises.
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

STORE_PATH = Path(__file__).parent / "performance.json"
HISTORY_PATH = Path(__file__).parent / "history.json"

WORKING_SET_THRESHOLD = 0.90  # sets within 10% of the top weight count as working
STALL_SESSIONS = 3

# Manual logging on the watch is error-prone, so a session's top weight has to
# land inside this band around the exercise's own median to be trusted. Outside
# it, the number is treated as a typo rather than as real strength change.
OUTLIER_LOW = 0.60
OUTLIER_HIGH = 1.80
MEANINGFUL_DROP = 0.10  # below this, a dip is session-to-session noise
STALE_DAYS = 21

# The median check can't catch a bad number when an exercise has only ever been
# logged once (a 431kg push-up sits happily at its own median), so absolute
# plausibility ceilings backstop it. Isolation work gets a much lower bar.
WEIGHT_CEILING = 300.0
ISOLATION_CEILING = 100.0
ISOLATION_CATEGORIES = {
    "CURL", "LATERAL_RAISE", "FLYE", "PUSH_UP", "TRICEPS_EXTENSION",
    "CRUNCH", "CALF_RAISE", "SHRUG",
}

# For --suggest, each category maps to exactly one group. MUSCLE_CATEGORIES
# below deliberately overlaps (a shrug is both back and shoulders work), which
# is fine for filtering but would double-count volume when comparing groups.
CATEGORY_PRIMARY_GROUP = {
    "BENCH_PRESS": "chest", "FLYE": "chest", "PUSH_UP": "chest",
    "ROW": "back", "PULL_UP": "back", "PULLDOWN": "back", "SHRUG": "back",
    "SHOULDER_PRESS": "shoulders", "LATERAL_RAISE": "shoulders",
    "CURL": "biceps",
    "TRICEPS_EXTENSION": "triceps",
    "SQUAT": "legs", "DEADLIFT": "legs", "LUNGE": "legs",
    "LEG_CURL": "legs", "CALF_RAISE": "legs", "HIP_RAISE": "legs",
    "CORE": "core", "CRUNCH": "core", "PLANK": "core", "LEG_RAISE": "core",
}

# Muscles need roughly 48h before being trained hard again, so anything
# trained more recently than this is not offered as a target.
MIN_RECOVERY_DAYS = 2

# Which groups pair sensibly in one session, best partner first.
GROUP_AFFINITY = {
    "chest": ["triceps", "shoulders"],
    "back": ["biceps", "core"],
    "shoulders": ["triceps", "chest", "core"],
    "biceps": ["back", "core"],
    "triceps": ["chest", "shoulders"],
    "legs": ["core"],
    "core": ["back", "shoulders"],
}

# Used by --muscles so the skill can ask "what have I been doing for chest?"
MUSCLE_CATEGORIES = {
    "chest": {"BENCH_PRESS", "FLYE", "PUSH_UP"},
    "shoulders": {"SHOULDER_PRESS", "LATERAL_RAISE", "SHRUG"},
    "back": {"ROW", "PULL_UP", "PULLDOWN", "SHRUG"},
    "biceps": {"CURL"},
    "triceps": {"TRICEPS_EXTENSION"},
    "legs": {"SQUAT", "DEADLIFT", "LUNGE", "LEG_CURL", "LEG_RAISE", "CALF_RAISE", "HIP_RAISE"},
    "quads": {"SQUAT", "LUNGE"},
    "hamstrings": {"DEADLIFT", "LEG_CURL"},
    "glutes": {"HIP_RAISE", "LUNGE", "SQUAT"},
    "core": {"CORE", "CRUNCH", "PLANK", "LEG_RAISE"},
}


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


def days_since(iso_date: str) -> int:
    try:
        return (date.today() - datetime.strptime(iso_date, "%Y-%m-%d").date()).days
    except ValueError:
        return 0


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

    return {
        "exercise": name,
        "category": latest["category"],
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


def group_load(store: dict) -> dict:
    """Per muscle group: when it was last trained, how often, and how much."""
    stats = defaultdict(lambda: {"last": "", "sets": 0, "sessions": set()})
    for act in store.get("activities", {}).values():
        for s in act.get("sets", []):
            group = CATEGORY_PRIMARY_GROUP.get(s.get("category"))
            if not group:
                continue
            g = stats[group]
            g["sets"] += 1
            g["sessions"].add(act["date"])
            if act["date"] > g["last"]:
                g["last"] = act["date"]

    return {
        name: {
            "last": g["last"],
            "days_ago": days_since(g["last"]) if g["last"] else 999,
            "sets": g["sets"],
            "sessions": len(g["sessions"]),
        }
        for name, g in stats.items()
    }


def suggest_focus(store: dict | None = None) -> dict:
    """
    Recommend which muscle groups to train next.

    Two things decide it: recovery (a group trained inside MIN_RECOVERY_DAYS is
    off the table regardless of how neglected it is) and volume deficit (how
    little that group has had relative to the most-trained one). The pairing
    then comes from GROUP_AFFINITY so the session still makes sense as a
    workout rather than two unrelated halves.
    """
    store = store or load_store()
    loads = group_load(store)
    if not loads:
        return {"primary": None, "partner": None, "reason": "no data yet", "groups": {}}

    busiest = max(g["sets"] for g in loads.values()) or 1
    for name, g in loads.items():
        g["deficit"] = 1 - (g["sets"] / busiest)
        g["recovered"] = g["days_ago"] >= MIN_RECOVERY_DAYS
        # Deficit drives the choice; days rested breaks ties in favour of
        # whatever has been sitting longest.
        g["score"] = round(g["deficit"] + min(g["days_ago"], 14) / 28, 3)

    ready = {n: g for n, g in loads.items() if g["recovered"]}
    if not ready:
        return {
            "primary": None,
            "partner": None,
            "reason": "everything was trained in the last 48h — take a rest day",
            "groups": loads,
        }

    primary = max(ready, key=lambda n: ready[n]["score"])
    partner = next(
        (p for p in GROUP_AFFINITY.get(primary, []) if p in ready and p != primary),
        None,
    )
    if partner is None:
        remaining = {n: g for n, g in ready.items() if n != primary}
        partner = max(remaining, key=lambda n: remaining[n]["score"], default=None)

    p = loads[primary]
    reason = (
        f"{primary} has {p['sets']} sets logged vs {busiest} for your most-trained "
        f"group, and was last hit {p['days_ago']} days ago"
    )

    # Chest/back/legs carry a session. A pairing of only small groups can't fill
    # 45-50 minutes without junk volume, so flag it rather than pretend it's fine.
    major = {"chest", "back", "legs"}
    caveat = None
    if not ({primary, partner} & major):
        # The best major group to wait for is the one most rested and most
        # under-trained — same score used everywhere else, not the one trained
        # most recently.
        candidates = {n: g for n, g in loads.items() if n in major}
        best = max(candidates, key=lambda n: candidates[n]["score"], default=None)
        if best:
            caveat = (
                f"both are small groups — fine as a short accessory session, or "
                f"wait a day and pair {primary} with {best} "
                f"(rested {candidates[best]['days_ago']}d)"
            )

    return {
        "primary": primary,
        "partner": partner,
        "reason": reason,
        "caveat": caveat,
        "groups": loads,
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


def main():
    args = [a for a in sys.argv[1:]]
    brief = "--brief" in args
    if brief:
        args.remove("--brief")

    if "--suggest" in args:
        s = suggest_focus()
        groups = sorted(
            s["groups"].items(), key=lambda kv: kv[1]["days_ago"], reverse=True
        )
        print(f"\n{'group':<11}{'last':<12}{'days':>5}{'sessions':>10}{'sets':>7}  status")
        for name, g in groups:
            status = "recovered" if g["recovered"] else "needs rest"
            print(
                f"{name:<11}{g['last'] or '-':<12}{g['days_ago']:>5}"
                f"{g['sessions']:>10}{g['sets']:>7}  {status}"
            )
        print()
        if s["primary"]:
            pair = f"{s['primary']} + {s['partner']}" if s["partner"] else s["primary"]
            print(f"Suggested next session: {pair}")
            print(f"  why: {s['reason']}")
            if s.get("caveat"):
                print(f"  note: {s['caveat']}")
        else:
            print(s["reason"])
        return

    muscles = None
    if "--muscles" in args:
        i = args.index("--muscles")
        muscles = args[i + 1:]

    results = analyze(muscles)
    if not results:
        print("Nothing matched. Try `python coach.py` with no filter.")
        return

    if brief:
        for r in results:
            reps = "/".join(str(x) for x in r["last_reps"]) or "-"
            w = f"{r['last_weight']}kg" if r["last_weight"] else "bw"
            print(
                f"{r['exercise']}: {w} x{reps} ({r['last_date']}, "
                f"{r['sessions']} sessions) [{r['verdict']}] -> {r['suggestion']}"
            )
        return

    label = f" for {', '.join(muscles)}" if muscles else ""
    print(f"\nPerformance review{label} — {len(results)} exercises\n")
    for r in results:
        reps = ", ".join(str(x) for x in r["last_reps"]) or "-"
        w = f"{r['last_weight']}kg" if r["last_weight"] else "bodyweight"
        dropped = r["sessions"] - r["clean_sessions"]
        print(f"  {r['exercise'].replace('_', ' ').title()}  [{r['verdict'].upper()}]")
        print(
            f"      last: {w} x {reps} reps, {r['days_ago']}d ago "
            f"({r['sessions']} session{'s' if r['sessions'] != 1 else ''} logged"
            + (f", {dropped} not trusted" if dropped else "")
            + (f", target {r['target_reps']} reps" if r["target_reps"] else "")
            + ")"
        )
        print(f"      next: {r['suggestion']}\n")

    suspect = [r for r in results if r["verdict"] == "check-data"]
    if suspect:
        print(
            f"{len(suspect)} exercise(s) flagged check-data — manual entry on the "
            "watch slips, so those figures were left out of the progression maths."
        )

    if not muscles:
        unlabelled = unlabelled_work(load_store())
        if unlabelled:
            total = sum(len(u["sets"]) for u in unlabelled)
            print(
                f"\n{total} set(s) across {len(unlabelled)} session(s) had weight and "
                "reps but no exercise name from the watch, so they belong to no "
                "verdict above. These are often the heaviest sets of the day — if a "
                "lift below looks like it regressed, check here first:"
            )
            for u in unlabelled[:5]:
                detail = ", ".join(f"{r}x{w}kg" for r, w in u["sets"])
                print(f"    {u['date']}  {u['name'][:24]:<26} {detail}")


if __name__ == "__main__":
    main()
