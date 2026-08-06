#!/usr/bin/env python3
"""
Check a workout's exercises against Garmin's official FIT SDK exercise list.

    python validate.py workouts/chest_shoulders_1.py

upload.py runs this automatically before pushing anything, so a bad exercise
name or category is caught before upload rather than as a 400 afterwards. Worth
running directly when hand-editing a workout file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from garmin_workouts import validation, workout as wk


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a workout file against the Garmin FIT SDK."
    )
    parser.add_argument("workout_file", help="e.g. workouts/chest_shoulders_1.py")
    args = parser.parse_args()

    path = Path(args.workout_file)
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    w = wk.load_workout(str(path))
    errors = validation.validate_workout(w)

    if errors:
        print(f"Validation FAILED for '{w['name']}':")
        for e in errors:
            print(f"  x {e}")
        sys.exit(1)

    print(
        f"All {len(w['exercises'])} exercises in '{w['name']}' "
        "are valid Garmin FIT SDK entries."
    )


if __name__ == "__main__":
    main()
