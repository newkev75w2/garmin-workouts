#!/usr/bin/env python3
"""
Push a workout to Garmin Connect.

First time ever:
    pip install -r requirements.txt --break-system-packages
    python login.py                       # one-time interactive login, caches a session

Every time after:
    python upload.py workouts/chest_shoulders_1.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from garmin_workouts import history, validation, workout as wk
from garmin_workouts.client import get_client


def describe(w: dict) -> None:
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload a workout to Garmin Connect.")
    parser.add_argument("workout_file", help="e.g. workouts/chest_shoulders_1.py")
    parser.add_argument("--dry-run", action="store_true",
                        help="validate and show the workout without uploading")
    args = parser.parse_args()

    path = Path(args.workout_file)
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    w = wk.load_workout(str(path))

    errors = validation.validate_workout(w)
    if errors:
        print(f"Validation FAILED for '{w['name']}' — nothing was uploaded:")
        for e in errors:
            print(f"  x {e}")
        sys.exit(1)

    describe(w)

    if args.dry_run:
        print("Dry run — validated only, nothing uploaded.")
        return

    client = get_client()
    print(f"Connected as: {client.get_full_name()}")

    print(f"Uploading '{w['name']}'...")
    result = client.connectapi(
        "/workout-service/workout", method="POST", json=wk.build_payload(w)
    )
    workout_id = result.get("workoutId") if isinstance(result, dict) else result
    print(f"Done! Workout ID: {workout_id}")
    print("Garmin Connect -> Training -> Workouts -> sync to watch.")

    history.log_session(str(path), w)


if __name__ == "__main__":
    main()
