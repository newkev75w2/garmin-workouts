#!/usr/bin/env python3
"""
Judge performance from synced Garmin sessions and say what to do next.

    python sync.py                              # pull the data down first
    python coach.py                             # verdict on every exercise
    python coach.py --suggest                   # which muscle groups to train next
    python coach.py --muscles chest shoulders   # filter to one session's groups
    python coach.py --brief                     # compact output, what the skill reads
    python coach.py --prescribed "incline db"   # what was programmed, not performed

Verdicts and the reasoning behind them are documented in
garmin_workouts/judging.py; the thresholds live in garmin_workouts/constants.py.
"""

from __future__ import annotations

import argparse
from collections import defaultdict

from garmin_workouts import history, judging, planning, store


def print_suggestion() -> None:
    s = planning.suggest_focus()
    groups = sorted(s["groups"].items(), key=lambda kv: kv[1]["days_ago"], reverse=True)

    print(f"\n{'group':<11}{'last':<12}{'days':>5}{'sessions':>10}{'sets':>7}  status")
    for name, g in groups:
        status = "recovered" if g["recovered"] else "needs rest"
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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Judge Garmin strength performance and suggest what to do next.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--suggest", action="store_true",
                   help="recommend which muscle groups to train next, and why")
    p.add_argument("--brief", action="store_true",
                   help="one line per exercise (what the skill reads)")
    p.add_argument("--muscles", nargs="+", metavar="GROUP",
                   help="limit to these muscle groups, e.g. --muscles chest shoulders")
    p.add_argument("--prescribed", nargs="?", const="", metavar="EXERCISE",
                   help="show what was programmed over time instead of performed")
    return p


def main() -> None:
    args = build_parser().parse_args()

    if args.suggest:
        print_suggestion()
        return

    if args.prescribed is not None:
        print_prescribed(args.prescribed or None)
        return

    results = judging.analyze(args.muscles)
    if not results:
        print("Nothing matched. Try `python coach.py` with no filter.")
        return

    if args.brief:
        for r in results:
            reps = "/".join(str(x) for x in r["last_reps"]) or "-"
            weight = f"{r['last_weight']}kg" if r["last_weight"] else "bw"
            print(
                f"{r['exercise']}: {weight} x{reps} ({r['last_date']}, "
                f"{r['sessions']} sessions) [{r['verdict']}] -> {r['suggestion']}"
            )
        return

    print_report(results, args.muscles)
    if not args.muscles:
        print_unlabelled()


if __name__ == "__main__":
    main()
