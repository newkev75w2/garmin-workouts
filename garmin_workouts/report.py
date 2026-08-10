"""
Rendering analysis results for the terminal.

Kept apart from judging.py and planning.py so that changing how something reads
can never change what it concludes — and so the verdict logic stays testable
without capturing stdout.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from . import history, planning, recovery, store


def print_suggestion(
    as_of: date | None = None,
    planned: list | None = None,
    planned_date: date | None = None,
) -> None:
    s = planning.suggest_focus(as_of=as_of, planned=planned, planned_date=planned_date)
    groups = sorted(s["groups"].items(), key=lambda kv: kv[1]["days_ago"], reverse=True)

    when = f" (as of {as_of})" if as_of else ""
    print(f"\n{'group':<11}{'last':<12}{'days':>5}{'sessions':>10}{'sets':>7}  status{when}")
    for name, g in groups:
        status = "recovered" if g["recovered"] else "needs rest"
        if g.get("planned"):
            status += " (planned)"
        print(
            f"{name:<11}{g['last'] or '-':<12}{g['days_ago']:>5}"
            f"{g['sessions']:>10}{g['sets']:>7}  {status}"
        )
    print()

    note = recovery.advice()
    if note:
        print(f"Recovery: {note}\n")

    if not s["primary"]:
        print(s["reason"])
        return
    pair = f"{s['primary']} + {s['partner']}" if s["partner"] else s["primary"]
    print(f"Suggested next session: {pair}")
    print(f"  why: {s['reason']}")
    if s.get("caveat"):
        print(f"  note: {s['caveat']}")


def print_prescribed(filter_term: str | None) -> None:
    """
    What was *programmed* over time, from history.json — as opposed to what was
    actually lifted, which is everything else in this tool. Useful for seeing how
    a prescription drifted, independent of whether it got completed.
    """
    entries = history.load()
    if not entries:
        print("No workouts uploaded yet — history.json is empty.")
        return

    term = filter_term.lower().replace(" ", "_") if filter_term else None
    by_exercise = defaultdict(list)
    for entry in entries:
        for ex in entry["exercises"]:
            if term and term not in ex["name"].lower():
                continue
            by_exercise[ex["name"]].append((entry["date"], ex))

    if not by_exercise:
        print(f"No prescribed sessions match '{filter_term}'.")
        return

    for name, records in sorted(by_exercise.items()):
        print(f"\n{name.replace('_', ' ').title()}")
        for date_str, ex in records:
            effort = f"{ex['sets']}x{ex.get('reps') or str(ex.get('seconds')) + 's'}"
            print(f"  {date_str[:10]}  {effort:<10} {ex['rest_seconds']}s rest")


def print_report(results: list, muscles: list | None, show_stale: bool = False) -> None:
    hidden = 0
    if not show_stale:
        hidden = sum(1 for r in results if r["verdict"] == "stale")
        results = [r for r in results if r["verdict"] != "stale"]

    label = f" for {', '.join(muscles)}" if muscles else ""
    print(f"\nPerformance review{label} — {len(results)} exercises\n")

    for r in results:
        reps = ", ".join(str(x) for x in r["last_reps"]) or "-"
        weight = f"{r['last_weight']}kg" if r["last_weight"] else "bodyweight"
        dropped = r["sessions"] - r["clean_sessions"]
        print(f"  {r['exercise'].replace('_', ' ').title()}  [{r['verdict'].upper()}]")
        print(
            f"      last: {weight} x {reps} reps, {r['days_ago']}d ago "
            f"({r['sessions']} session{'s' if r['sessions'] != 1 else ''} logged"
            + (f", {dropped} not trusted" if dropped else "")
            + (f", target {r['target_reps']} reps" if r["target_reps"] else "")
            + ")"
        )
        print(f"      next: {r['suggestion']}")
        if r.get("adherence"):
            print(f"      note: {r['adherence']}")
        print()

    if hidden:
        print(f"({hidden} exercises untrained for 21+ days omitted — use --stale to see them.)\n")

    suspect = [r for r in results if r["verdict"] == "check-data"]
    if suspect:
        print(
            f"{len(suspect)} exercise(s) flagged check-data — manual entry on the "
            "watch slips, so those figures were left out of the progression maths."
        )


def print_unlabelled() -> None:
    unlabelled = store.unlabelled_work(store.load_store())
    if not unlabelled:
        return
    total = sum(len(u["sets"]) for u in unlabelled)
    print(
        f"\n{total} set(s) across {len(unlabelled)} session(s) had weight and reps "
        "but no exercise name from the watch, so they belong to no verdict above. "
        "These are often the heaviest sets of the day — if a lift above looks like "
        "it regressed, check here first:"
    )
    for u in unlabelled[:5]:
        detail = ", ".join(f"{r}x{w}kg" for r, w in u["sets"])
        print(f"    {u['date']}  {u['name'][:24]:<26} {detail}")


def print_brief(results: list, show_stale: bool = False) -> None:
    """
    One line per exercise — the form the skill reads back.

    Stale exercises are collapsed by default. Once a few months of history is
    synced they outnumber everything else (27 of 78 on a real log), and an
    exercise untouched for a month says nothing about what to programme today.
    They are counted, not hidden, so they can still be asked for.
    """
    stale = [r for r in results if r["verdict"] == "stale"]
    if not show_stale:
        results = [r for r in results if r["verdict"] != "stale"]

    for r in results:
        reps = "/".join(str(x) for x in r["last_reps"]) or "-"
        weight = f"{r['last_weight']}kg" if r["last_weight"] else "bw"
        line = (
            f"{r['exercise']}: {weight} x{reps}{r.get('unit_suffix', '')} "
            f"({r['last_date']}, {r['sessions']} sessions) "
            f"[{r['verdict']}] -> {r['suggestion']}"
        )
        if r.get("adherence"):
            line += f" | ADHERENCE: {r['adherence']}"
        print(line)

    if stale and not show_stale:
        names = ", ".join(s["exercise"] for s in stale[:6])
        more = f" and {len(stale) - 6} more" if len(stale) > 6 else ""
        print(
            f"\n({len(stale)} exercises not trained in 21+ days, omitted: "
            f"{names}{more}. Use --stale to include them.)"
        )


def print_workout(w: dict) -> None:
    """The pre-upload summary: what is about to be sent to Garmin."""
    from . import workout as wk

    print(f"  Workout  : {w['name']}")
    if w.get("description"):
        print(f"  Focus    : {w['description']}")
    print(f"  Duration : ~{wk.estimate_duration(w)} min")
    print(f"  Exercises ({len(w['exercises'])}):")
    for ex in w["exercises"]:
        effort = f"{ex['sets']}x{ex.get('reps') or str(ex.get('seconds')) + 's'}"
        print(
            f"    - {ex['name'].replace('_', ' ').title():<38} "
            f"{effort:<8} {ex['rest_seconds']}s rest"
        )
    print()


def print_running(days: int = 90) -> None:
    """Intensity distribution and the VO2max it is aiming at."""
    from . import running

    dist = running.distribution(days)
    if not dist:
        print("No runs synced yet — run `garmin sync` first.")
        return

    trend = running.vo2max_trend()
    if trend:
        first, last = trend[0], trend[-1]
        arrow = "->" if len(trend) > 1 else ""
        change = f" {arrow} {last[1]:g} ({last[0]})" if len(trend) > 1 else ""
        print(f"\nVO2max: {first[1]:g} ({first[0]}){change}")

    print(
        f"\nLast {dist['days']} days: {dist['runs']} runs, {dist['km']}km, "
        f"{dist['minutes']} min   [max HR {dist['max_hr']:g}, from your own data]\n"
    )

    widest = max(dist["buckets"].values()) or 1
    for name, count in dist["buckets"].items():
        bar = "#" * int(round(count / widest * 24))
        share = count / dist["runs"] if dist["runs"] else 0
        print(f"  {name:<14}{count:>3} {share:>5.0%}  {bar}")

    print(
        f"\n  easy {dist['easy_share']:.0%} · grey {dist['grey_share']:.0%} · "
        f"hard {dist['hard'] / dist['runs']:.0%}"
        if dist["runs"] else ""
    )

    print()
    for note in running.advice(dist):
        print(f"  - {note}")


def print_plan(goal="vo2max", start=None, strength=None, runs=None, weekdays=None) -> None:
    """A week laid out, with the reasoning that shaped it."""
    from . import plan as planner

    week = planner.build_week(
        start=start, goal=goal, strength_days=strength, runs=runs, weekdays=weekdays
    )

    print(f"\nWeek of {week['start']}  —  goal: {week['goal']}\n")
    for day in week["days"]:
        label = day["date"].strftime("%a %d %b")
        if not day["sessions"]:
            state = "unavailable" if "not available" in day["notes"] else "rest"
            print(f"  {label}   {state}")
        else:
            for i, s in enumerate(day["sessions"]):
                head = label if i == 0 else " " * len(label)
                kind = f"{s['type']} ({s['intensity']})"
                when = s["when"] if s["when"] != "any" else "—"
                print(f"  {head}   {when:<3} {kind:<20} {s['minutes']:>3}min  {s['detail']}")
        for note in day["notes"]:
            print(f"  {' ' * len(label)}        - {note}")
    print()
    for line in week.get("mix_notes", []):
        print(f"  {line}")
    if week.get("overridden"):
        print(
            f"  using your requested split; left to itself it would suggest "
            f"{week['recommended_strength']} strength session(s)"
        )
    for line in week["rationale"]:
        print(f"  {line}")
