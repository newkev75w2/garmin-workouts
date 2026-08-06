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

from garmin_workouts import judging, report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Judge Garmin strength performance and suggest what to do next.",
    )
    parser.add_argument("--suggest", action="store_true",
                        help="recommend which muscle groups to train next, and why")
    parser.add_argument("--brief", action="store_true",
                        help="one line per exercise (what the skill reads)")
    parser.add_argument("--muscles", nargs="+", metavar="GROUP",
                        help="limit to these muscle groups, e.g. --muscles chest shoulders")
    parser.add_argument("--prescribed", nargs="?", const="", metavar="EXERCISE",
                        help="show what was programmed over time instead of performed")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.suggest:
        report.print_suggestion()
        return

    if args.prescribed is not None:
        report.print_prescribed(args.prescribed or None)
        return

    results = judging.analyze(args.muscles)
    if not results:
        print("Nothing matched. Try `python coach.py` with no filter.")
        return

    if args.brief:
        report.print_brief(results)
        return

    report.print_report(results, args.muscles)
    if not args.muscles:
        report.print_unlabelled()


if __name__ == "__main__":
    main()
