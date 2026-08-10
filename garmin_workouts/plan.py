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

# Starting weekly mix per goal: (quality runs, easy runs, strength sessions).
# recommend_mix() adjusts these against what the athlete is actually doing —
# a target nobody reaches is worse than a smaller one they hit every week.
GOALS = {
    "vo2max": (1, 2, 3),
    "endurance": (1, 3, 2),
    "strength": (0, 2, 4),
    "balanced": (1, 2, 3),
}

# Never ask for more than this many extra runs per week than they currently do.
# Aerobic fitness responds to consistency; injury and abandonment respond to
# jumping volume, and a plan nobody follows improves nothing.
MAX_RUN_RAMP = 1.5

# A VO2max series flat across this many weeks means the current stimulus has
# stopped working, and more of the same will not restart it.
PLATEAU_WEEKS = 4
LONG_RUN_MINUTES = 50

# Two clear days a week. When the session count would leave fewer, easy runs get
# stacked onto upper-body days rather than eating every rest day — a hard week
# with no recovery in it produces fatigue, not adaptation.
MIN_REST_DAYS = 2

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


def recommend_mix(goal: str = "vo2max", store: dict | None = None) -> dict:
    """
    What this week's split should actually be, given what they have been doing.

    The goal sets an ideal; the athlete's own history sets what is reachable
    from here. Three adjustments, in order of how often they matter:

      - Ramp. Running frequency is the main lever on VO2max, but asking someone
        running 0.7 times a week for four runs produces a week they abandon.
        Increases are capped relative to current frequency.
      - Plateau. If VO2max has been flat for a month, adding easy volume will
        not restart it — the missing stimulus is intensity, so a quality session
        is added ahead of more easy running.
      - Recovery. Poor sleep or low readiness removes a session rather than
        pretending the week is free.
    """
    quality, easy, strength = GOALS.get(goal, GOALS["balanced"])
    notes = []

    dist = running.distribution()
    current_runs = (dist["runs"] / (dist["days"] / 7)) if dist and dist.get("runs") else 0

    ceiling = int(round(current_runs + MAX_RUN_RAMP))
    if current_runs and (quality + easy) > max(ceiling, 2):
        target = max(ceiling, 2)
        while (quality + easy) > target and easy > 1:
            easy -= 1
        notes.append(
            f"currently running {current_runs:.1f}x a week, so this asks for "
            f"{quality + easy} rather than {GOALS[goal][0] + GOALS[goal][1]} — "
            "build the habit before the volume"
        )

    trend = running.vo2max_trend()
    if len(trend) >= 2:
        recent = trend[-1][1] - trend[max(0, len(trend) - PLATEAU_WEEKS)][1]
        if recent <= 0.1 and quality < 2:
            quality += 1
            easy = max(1, easy - 1)
            notes.append(
                f"VO2max flat at {trend[-1][1]:g} across the last "
                f"{min(len(trend), PLATEAU_WEEKS)} readings — swapping an easy run "
                "for a second quality session, since more easy volume will not "
                "restart a stalled adaptation"
            )
        else:
            notes.append(
                f"VO2max moving ({trend[0][1]:g} -> {trend[-1][1]:g}) — "
                "the current stimulus is working, so this keeps its shape"
            )

    if recovery.advice() and "train as planned" not in (recovery.advice() or ""):
        if strength > 2:
            strength -= 1
            notes.append("recovery is down, so one strength session comes out")

    return {
        "quality": quality,
        "easy": easy,
        "strength": strength,
        "notes": notes,
        "current_runs_per_week": round(current_runs, 1),
    }


def week_start(reference: date | None = None, when: str | None = None) -> date:
    """
    Which day the plan should begin.

    A training week is a calendar week, so the default is the coming Monday —
    starting "tomorrow" produced plans running Wednesday to Tuesday, which is
    awkward to follow and impossible to compare week to week. Monday itself
    plans the week you are standing in rather than pushing it a week out.
    """
    today = reference or date.today()
    if when in ("today", None) and today.weekday() == 0:
        return today
    if when == "today":
        return today
    if when == "tomorrow":
        return today + timedelta(days=1)
    days_ahead = (7 - today.weekday()) % 7 or 7
    return today + timedelta(days=days_ahead)


def _leg_day(focus: list) -> bool:
    return any(g in LEG_GROUPS for g in focus)


def build_week(
    start: date | None = None,
    goal: str = "vo2max",
    store: dict | None = None,
    strength_days: int | None = None,
    runs: int | None = None,
) -> dict:
    """
    A seven-day template starting from `start` (default tomorrow).

    Strength focus for each day is resolved in order, feeding the days already
    scheduled back in as `planned`, so the same muscle group is not prescribed
    twice in a week just because it started out the most neglected.
    """
    start = start or week_start()

    mix = recommend_mix(goal, store)
    quality_runs, easy_runs = mix["quality"], mix["easy"]
    recommended_strength = mix["strength"]
    strength_days = recommended_strength if strength_days is None else strength_days

    if runs is not None:
        # Keep at least one quality session when the goal is aerobic; extra runs
        # beyond that are easy, since that is where volume belongs.
        quality_runs = min(quality_runs, runs) or (1 if goal != "strength" and runs else 0)
        easy_runs = max(0, runs - quality_runs)

    days = [
        {
            "date": start + timedelta(days=n),
            "sessions": [],
            "notes": [],
        }
        for n in range(7)
    ]

    # 1. The quality run anchors the week when the goal is aerobic. Mid-week
    #    keeps it clear of the weekend and leaves room either side.
    quality_slots = [2, 5][:quality_runs]
    for slot in quality_slots:
        days[slot]["sessions"].append(
            {
                "type": "run",
                "intensity": "quality",
                "minutes": QUALITY_RUN_MINUTES,
                "detail": "5x3min at ~93% max HR, equal easy recovery",
                "when": "am",
            }
        )
        days[slot]["notes"].append("anchor session — keep the day around it light")

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

    # The longest easy run goes on a day with nothing else, so it can actually be
    # long. Stacking it behind a lifting session just makes it a tired short run.
    # Guarantee rest days by stacking rather than spreading. Six sessions across
    # seven days leaves one clear day; pairing an easy run onto an upper-body
    # session buys back a second without dropping any work.
    training_days = {i for i in range(7) if days[i]["sessions"]} | set(run_slots)
    over_budget = len(training_days) - (7 - MIN_REST_DAYS)
    if over_budget > 0:
        movable = [i for i in sorted(run_slots) if not days[i]["sessions"]]
        hosts = [
            i for i in range(7)
            if days[i]["sessions"] and can_take_a_run(i) and i not in run_slots
        ]
        for _ in range(min(over_budget, len(movable), len(hosts))):
            run_slots.remove(movable.pop(0))
            run_slots.append(hosts.pop(0))

    solo_slots = [i for i in sorted(run_slots) if not days[i]["sessions"]]
    # With only one easy run in the week it is the volume session by definition.
    long_slot = solo_slots[-1] if solo_slots and easy_runs >= 1 else None

    for index in sorted(run_slots):
        day = days[index]
        strength = next((s for s in day["sessions"] if s["type"] == "strength"), None)
        is_long = index == long_slot
        day["sessions"].append(
            {
                "type": "run",
                "intensity": "long" if is_long else "easy",
                "minutes": LONG_RUN_MINUTES if is_long else EASY_RUN_MINUTES,
                "detail": (
                    "steady aerobic, below ~78% max HR — the week's volume session"
                    if is_long else "conversational pace, below ~78% max HR"
                ),
                "when": "pm" if strength else "am",
            }
        )
        if strength:
            day["notes"].append("leave 6+ hours between the two; lift first")

    # Time of day only constrains anything when a day holds two sessions. Saying
    # "am" for a lone session implies a rule that isn't there.
    for day in days:
        if len(day["sessions"]) == 1:
            day["sessions"][0]["when"] = "any"
        if not day["sessions"]:
            day["notes"].append("full rest")

    return {
        "goal": goal,
        "start": start,
        "days": days,
        "mix_notes": mix["notes"],
        "overridden": strength_days != recommended_strength or runs is not None,
        "recommended_strength": recommended_strength,
        "rationale": _rationale(goal, quality_runs, easy_runs, strength_days),
    }


def _rationale(goal: str, quality: int, easy: int, strength: int) -> list:
    notes = [
        f"goal '{goal}': {quality} quality run(s), {easy} easy run(s), "
        f"{strength} strength session(s)"
    ]

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
