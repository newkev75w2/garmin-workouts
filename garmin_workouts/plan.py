"""
Scheduling a week of strength and running together.

The reason this exists rather than two separate planners: the interesting
constraints are the ones *between* the two. Heavy legs the day before a hard run
spoils the run; a hard run the day before heavy legs spoils the session. Neither
a strength planner nor a running planner can see that on its own.

What the research supports, and what is encoded here:

  - Easy running interferes very little with strength. A short Z1-Z2 run and a
    lifting session can share a day, ideally several hours apart.
  - Hard intervals and heavy lower-body work do interfere, in both directions.
    They get separated by a day wherever possible.
  - When two sessions must share a day, the one that serves the goal goes first,
    while the athlete is fresh; the other is kept deliberately easy.
  - Muscle groups still need their own recovery window, so strength focus is
    chosen day by day using the same volume-deficit logic as `garmin suggest`.

The goal decides what anchors the week. With `vo2max`, quality runs are placed
first and strength fits around them — which is the opposite of what a
strength-only planner would do, and the whole point of planning them together.

The plan is a template, not a prescription. It says what shape the week should
have; it does not know about your calendar.
"""

from __future__ import annotations

from datetime import date, timedelta

from . import planning, recovery, running

# Weekly session counts per goal: (quality runs, easy runs, strength sessions).
GOALS = {
    "vo2max": (1, 2, 3),
    "endurance": (1, 3, 2),
    "strength": (0, 2, 4),
    "balanced": (1, 2, 3),
}

LEG_GROUPS = {"legs", "quads", "hamstrings", "glutes"}
EASY_RUN_MINUTES = 30
QUALITY_RUN_MINUTES = 40


def spread(slots: list, count: int) -> list:
    """
    Pick `count` slots spaced as evenly as possible across those available.

    Filling from the front instead produced a week with every session crammed
    into the first four days and three rest days stacked at the end, which is
    both worse training and obviously wrong to look at.
    """
    if count <= 0 or not slots:
        return []
    if count >= len(slots):
        return list(slots)
    step = len(slots) / count
    return sorted({slots[min(int(i * step), len(slots) - 1)] for i in range(count)})


def _leg_day(focus: list) -> bool:
    return any(g in LEG_GROUPS for g in focus)


def build_week(
    start: date | None = None,
    goal: str = "vo2max",
    store: dict | None = None,
) -> dict:
    """
    A seven-day template starting from `start` (default tomorrow).

    Strength focus for each day is resolved in order, feeding the days already
    scheduled back in as `planned`, so the same muscle group is not prescribed
    twice in a week just because it started out the most neglected.
    """
    start = start or date.today() + timedelta(days=1)
    quality_runs, easy_runs, strength_days = GOALS.get(goal, GOALS["balanced"])

    days = [
        {
            "date": start + timedelta(days=n),
            "sessions": [],
            "notes": [],
        }
        for n in range(7)
    ]

    # 1. The quality run anchors the week when the goal is aerobic. Mid-week
    #    keeps it clear of the weekend and leaves room either side. Garmin's own
    #    suggestion is preferred when it has one, since it is computed from
    #    training load this tool cannot see; it usually has none.
    suggested = [running.summarise_suggested(s) for s in running.garmin_suggested()]
    quality_slots = [2, 5][:quality_runs]
    for n, slot in enumerate(quality_slots):
        pick = suggested[n] if n < len(suggested) else None
        days[slot]["sessions"].append(
            {
                "type": "run",
                "intensity": "quality",
                "minutes": (pick and pick["minutes"]) or QUALITY_RUN_MINUTES,
                "detail": pick["name"] if pick else "5x3min at ~93% max HR, equal easy recovery",
                "source": "garmin" if pick else "planner",
                "when": "am",
            }
        )
        days[slot]["notes"].append("anchor session — keep the day around it light")
        if pick:
            days[slot]["notes"].append(f"Garmin's own suggestion: {pick['description'][:80]}")

    # 2. Legs are kept a clear day away from every quality run, in both
    #    directions, since the interference runs both ways.
    blocked_for_legs = set()
    for slot in quality_slots:
        blocked_for_legs.update({slot - 1, slot, slot + 1})

    # 3. Strength days fill the gaps, choosing focus by deficit as we go.
    planned_groups: list = []
    available = [n for n in range(7) if n not in quality_slots]
    # Ask for more candidate days than sessions needed. A day can be skipped
    # when every muscle group is still inside its recovery window, and without
    # slack that skip silently costs a session the goal asked for.
    strength_slots = spread(available, min(len(available), strength_days + 2))
    placed = 0
    for slot in strength_slots:
        if placed >= strength_days:
            break
        day = days[slot]
        suggestion = planning.suggest_focus(
            store=store,
            as_of=day["date"],
            planned=planned_groups or None,
            planned_date=day["date"] - timedelta(days=1),
        )
        focus = [g for g in (suggestion["primary"], suggestion["partner"]) if g]
        if not focus:
            day["notes"].append("everything recently trained — rest or mobility")
            continue

        if _leg_day(focus) and slot in blocked_for_legs:
            day["notes"].append(
                "legs skipped here — too close to a quality run; upper body instead"
            )
            focus = [g for g in focus if g not in LEG_GROUPS] or ["chest"]

        day["sessions"].append(
            {
                "type": "strength",
                "intensity": "normal",
                "minutes": 48,
                "detail": " + ".join(focus),
                "when": "am",
            }
        )
        planned_groups.extend(focus)
        placed += 1

    # 4. Easy runs go anywhere left, and may share a day with upper-body work —
    #    that combination is well tolerated and is how volume gets accumulated
    #    without adding a training day.
    def can_take_a_run(index: int) -> bool:
        day = days[index]
        if any(s["type"] == "run" for s in day["sessions"]):
            return False
        strength = next((s for s in day["sessions"] if s["type"] == "strength"), None)
        # A run on legs that have just been trained is neither easy nor useful.
        return not (strength and _leg_day(strength["detail"].split(" + ")))

    # Prefer days with nothing on them, so easy volume also breaks up the week,
    # and only double up with an upper-body session once those run out.
    empty = [n for n in range(7) if can_take_a_run(n) and not days[n]["sessions"]]
    shared = [n for n in range(7) if can_take_a_run(n) and days[n]["sessions"]]
    run_slots = spread(empty, min(easy_runs, len(empty)))
    run_slots += spread(shared, easy_runs - len(run_slots))

    for index in sorted(run_slots):
        day = days[index]
        strength = next((s for s in day["sessions"] if s["type"] == "strength"), None)
        day["sessions"].append(
            {
                "type": "run",
                "intensity": "easy",
                "minutes": EASY_RUN_MINUTES,
                "detail": "conversational pace, below ~78% max HR",
                "when": "pm" if strength else "am",
            }
        )
        if strength:
            day["notes"].append("leave 6+ hours between the two; lift first")

    for day in days:
        if not day["sessions"]:
            day["notes"].append("full rest")

    return {
        "goal": goal,
        "start": start,
        "days": days,
        "suggested_available": len(suggested),
        "rationale": _rationale(goal, quality_runs, easy_runs, strength_days, len(suggested)),
    }


def _rationale(goal: str, quality: int, easy: int, strength: int,
               suggested: int = 0) -> list:
    notes = [
        f"goal '{goal}': {quality} quality run(s), {easy} easy run(s), "
        f"{strength} strength session(s)"
    ]

    if suggested:
        notes.append(f"using {suggested} of Garmin's own suggested run(s) for the hard days")
    else:
        notes.append(
            "Garmin has no suggested workouts to offer right now — it builds those "
            "from training load, and there isn't enough recent running for it to have "
            "a view. Quality sessions below are this tool's own prescription"
        )

    dist = running.distribution()
    if dist and dist.get("runs"):
        weekly = dist["km"] / (dist["days"] / 7)
        notes.append(
            f"currently averaging {weekly:.0f}km and "
            f"{dist['runs'] / (dist['days'] / 7):.1f} runs a week — "
            f"{easy + quality} is a step up, so ramp into it rather than "
            "hitting it in week one"
        )
        if dist["easy_share"] < running.POLARISED_EASY:
            notes.append(
                f"only {dist['easy_share']:.0%} of recent runs were genuinely easy — "
                "the easy ones here must feel too slow, or this becomes another "
                "grey-zone week"
            )

    note = recovery.advice()
    if note:
        notes.append(note)

    return notes
