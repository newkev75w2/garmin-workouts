#!/usr/bin/env python3
"""
Show how each exercise's prescribed volume has changed across logged sessions
(pulled from history.json, written automatically by upload.py).

This tracks what was *programmed* each session (sets, reps/seconds, rest) — not
actual weight lifted, since that lives in Garmin Connect's completed-activity
data rather than anything this project controls. If you want true weight-based
progression, that would need to read back your logged activity data from Garmin
Connect, which isn't wired up here yet.

Usage:
    python progress.py                          # every exercise ever logged
    python progress.py "incline dumbbell bench"  # filter by name (substring)
"""

from __future__ import annotations

import sys
from collections import defaultdict

import history


def main():
    entries = history._load()
    if not entries:
        print("No sessions logged yet — history.json is empty. Upload a workout first.")
        return

    filter_term = sys.argv[1].lower().replace(" ", "_") if len(sys.argv) > 1 else None

    by_exercise = defaultdict(list)
    for entry in entries:
        for ex in entry["exercises"]:
            if filter_term and filter_term not in ex["name"].lower():
                continue
            by_exercise[ex["name"]].append((entry["date"], ex))

    if not by_exercise:
        print(f"No logged sessions match '{sys.argv[1]}'.")
        return

    for name, records in sorted(by_exercise.items()):
        print(f"\n{name.replace('_', ' ').title()}")
        for date, ex in records:
            effort = f"{ex['sets']}x{ex.get('reps') or str(ex.get('seconds')) + 's'}"
            print(f"  {date[:10]}  {effort:<10} {ex['rest_seconds']}s rest")


if __name__ == "__main__":
    main()
