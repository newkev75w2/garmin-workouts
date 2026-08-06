#!/usr/bin/env python3
"""
Garmin Connect workout uploader.

First time ever:
    pip install -r requirements.txt --break-system-packages
    python login.py                       # one-time interactive login, caches a session

Every time after:
    python upload.py workouts/chest_shoulders_1.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import history
import validate
from garmin_client import get_client


def load_workout(path: str) -> dict:
    spec = importlib.util.spec_from_file_location("workout", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.WORKOUT


def rest_step(seconds: int, step_order: int = 2) -> dict:
    return {
        "type": "ExecutableStepDTO",
        "stepOrder": step_order,
        "stepType": {"stepTypeId": 5, "stepTypeKey": "rest"},
        "endCondition": {"conditionTypeId": 2, "conditionTypeKey": "time"},
        "endConditionValue": seconds,
        "targetType": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target"},
        "targetValueOne": None,
        "targetValueTwo": None,
    }


def exercise_block(step_order: int, ex: dict) -> dict:
    use_time = "seconds" in ex
    rest_secs = ex["rest_seconds"]
    return {
        "type": "RepeatGroupDTO",
        "stepOrder": step_order,
        "stepType": {"stepTypeId": 6, "stepTypeKey": "repeat"},
        "endCondition": {"conditionTypeId": 7, "conditionTypeKey": "iterations"},
        "endConditionValue": ex["sets"],
        "numberOfIterations": ex["sets"],
        "workoutSteps": [
            {
                "type": "ExecutableStepDTO",
                "stepOrder": 1,
                "stepType": {"stepTypeId": 3, "stepTypeKey": "interval"},
                "endCondition": (
                    {"conditionTypeId": 2, "conditionTypeKey": "time"}
                    if use_time
                    else {"conditionTypeId": 10, "conditionTypeKey": "reps"}
                ),
                "endConditionValue": ex.get("seconds") if use_time else ex["reps"],
                "targetType": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target"},
                "targetValueOne": None,
                "targetValueTwo": None,
                "category": ex["category"],
                "exerciseName": ex["name"],
            },
            rest_step(rest_secs),
        ],
    }


def build_payload(workout: dict) -> dict:
    steps = [exercise_block(i + 1, ex) for i, ex in enumerate(workout["exercises"])]
    return {
        "sportType": {"sportTypeId": 5, "sportTypeKey": "strength_training"},
        "workoutName": workout["name"],
        "description": workout.get("description", ""),
        "workoutSegments": [
            {
                "segmentOrder": 1,
                "sportType": {"sportTypeId": 5, "sportTypeKey": "strength_training"},
                "workoutSteps": steps,
            }
        ],
    }


def estimate_duration(workout: dict) -> int:
    """Estimate total workout duration in minutes."""
    total_seconds = 0
    for ex in workout["exercises"]:
        work_secs = ex.get("seconds", 45)  # ~45s to complete a set of reps
        total_seconds += ex["sets"] * (work_secs + ex["rest_seconds"])
    return round(total_seconds / 60)


def main():
    if len(sys.argv) < 2:
        print("Usage: python upload.py workouts/<workout_file>.py")
        sys.exit(1)

    workout_path = Path(sys.argv[1])
    if not workout_path.exists():
        print(f"File not found: {workout_path}")
        sys.exit(1)

    workout = load_workout(str(workout_path))

    errors = validate.validate_workout(workout)
    if errors:
        print(f"Validation FAILED for '{workout['name']}' — nothing was uploaded:")
        for e in errors:
            print(f"  x {e}")
        sys.exit(1)

    est_mins = estimate_duration(workout)
    print(f"  Workout  : {workout['name']}")
    if workout.get("description"):
        print(f"  Focus    : {workout['description']}")
    print(f"  Duration : ~{est_mins} min")
    print(f"  Exercises ({len(workout['exercises'])}):")
    for ex in workout["exercises"]:
        effort = f"{ex['sets']}x{ex.get('reps') or str(ex.get('seconds')) + 's'}"
        rest = f"{ex['rest_seconds']}s rest"
        print(f"    - {ex['name'].replace('_', ' ').title():<38} {effort:<8} {rest}")
    print()

    client = get_client()
    print(f"Connected as: {client.get_full_name()}")

    print(f"Uploading '{workout['name']}'...")
    payload = build_payload(workout)
    result = client.connectapi("/workout-service/workout", method="POST", json=payload)

    workout_id = result.get("workoutId") if isinstance(result, dict) else result
    print(f"Done! Workout ID: {workout_id}")
    print("Garmin Connect -> Training -> Workouts -> sync to watch.")

    history.log_session(str(workout_path), workout)


if __name__ == "__main__":
    main()
