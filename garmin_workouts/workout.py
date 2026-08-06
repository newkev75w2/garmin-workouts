"""
Loading a workout file and converting it into Garmin's workout JSON.

The schema here is reverse-engineered from what the Garmin Connect web app
posts -- there is no public workout-creation API. numberOfIterations on the
repeat group is required even though endConditionValue duplicates it; the
API rejects the payload without it.
"""

from __future__ import annotations

import importlib.util


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
