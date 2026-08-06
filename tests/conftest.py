"""
Shared fixtures.

Everything here is synthetic. The tests must not read performance.json — that
file is gitignored personal training data, so depending on it would make the
suite unrunnable for anyone else and would change meaning every time a workout
is synced.

Dates are built relative to today rather than hardcoded, because the staleness
and recovery rules are measured against the current date.
"""

from datetime import date, timedelta

import pytest


def days_ago(n: int) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


def a_set(exercise, reps, weight, category="ROW", step=None):
    """One ACTIVE set as sync.py stores it."""
    return {
        "exercise": exercise,
        "category": category,
        "confidence": 99.6,
        "reps": reps,
        "weight_kg": weight,
        "duration_s": 45.0,
        "step_index": step,
        "start_time": None,
    }


def an_activity(date_str, name, sets):
    return {"activity_id": abs(hash(date_str + name)) % 10**9,
            "date": date_str, "name": name, "sets": sets}


def a_store(*activities):
    return {"activities": {str(i): act for i, act in enumerate(activities)}}


@pytest.fixture
def leg_press_with_typo():
    """
    The real failure that motivated outlier rejection: a leg press logged at
    16kg in the middle of 120-200kg sessions. Taken at face value it reads as a
    catastrophic strength loss; it is a mistyped entry.
    """
    return a_store(
        *[
            an_activity(days_ago(d), "Legs", [a_set("LEG_PRESS", 12, w, "SQUAT")] * 3)
            for d, w in [(40, 120.0), (34, 16.0), (27, 130.0), (20, 150.0), (6, 140.0)]
        ]
    )
