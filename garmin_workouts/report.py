"""
Rendering analysis results for the terminal.

Kept apart from judging.py and planning.py so that changing how something reads
can never change what it concludes — and so the verdict logic stays testable
without capturing stdout.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from . import history, planning, store


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


def print_report(results: list, muscles: list | None) -> None:
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
        print(f"      next: {r['suggestion']}\n")

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


def print_brief(results: list) -> None:
    """One line per exercise — the form the skill reads back."""
    for r in results:
        reps = "/".join(str(x) for x in r["last_reps"]) or "-"
        weight = f"{r['last_weight']}kg" if r["last_weight"] else "bw"
        print(
            f"{r['exercise']}: {weight} x{reps} ({r['last_date']}, "
            f"{r['sessions']} sessions) [{r['verdict']}] -> {r['suggestion']}"
        )
