"""
Every tuned threshold and lookup table, in one place.

These numbers are not arbitrary. They were fitted against a real 20-session
log in which manual entry on the watch produced a 16kg leg press between
120-200kg sessions, a 431kg push-up, and dips recorded as bodyweight one
session and added load the next. Loosening them makes the analysis
confident and wrong -- tests/ pins the behaviour they produce.
"""

from __future__ import annotations



WORKING_SET_THRESHOLD = 0.90  # sets within 10% of the top weight count as working
STALL_SESSIONS = 3

# Manual logging on the watch is error-prone, so a session's top weight has to
# land inside this band around the exercise's own median to be trusted. Outside
# it, the number is treated as a typo rather than as real strength change.
OUTLIER_LOW = 0.60
OUTLIER_HIGH = 1.80
MEANINGFUL_DROP = 0.10  # below this, a dip is session-to-session noise
STALE_DAYS = 21

# The median check can't catch a bad number when an exercise has only ever been
# logged once (a 431kg push-up sits happily at its own median), so absolute
# plausibility ceilings backstop it. Isolation work gets a much lower bar.
WEIGHT_CEILING = 300.0
ISOLATION_CEILING = 100.0
ISOLATION_CATEGORIES = {
    "CURL", "LATERAL_RAISE", "FLYE", "PUSH_UP", "TRICEPS_EXTENSION",
    "CRUNCH", "CALF_RAISE", "SHRUG",
}

# For --suggest, each category maps to exactly one group. MUSCLE_CATEGORIES
# below deliberately overlaps (a shrug is both back and shoulders work), which
# is fine for filtering but would double-count volume when comparing groups.
CATEGORY_PRIMARY_GROUP = {
    "BENCH_PRESS": "chest", "FLYE": "chest", "PUSH_UP": "chest",
    "ROW": "back", "PULL_UP": "back", "PULLDOWN": "back", "SHRUG": "back",
    "SHOULDER_PRESS": "shoulders", "LATERAL_RAISE": "shoulders",
    "CURL": "biceps",
    "TRICEPS_EXTENSION": "triceps",
    "SQUAT": "legs", "DEADLIFT": "legs", "LUNGE": "legs",
    "LEG_CURL": "legs", "CALF_RAISE": "legs", "HIP_RAISE": "legs",
    "CORE": "core", "CRUNCH": "core", "PLANK": "core", "LEG_RAISE": "core",
}

# Muscles need roughly 48h before being trained hard again, so anything
# trained more recently than this is not offered as a target.
MIN_RECOVERY_DAYS = 2

# Which groups pair sensibly in one session, best partner first.
GROUP_AFFINITY = {
    "chest": ["triceps", "shoulders"],
    "back": ["biceps", "core"],
    "shoulders": ["triceps", "chest", "core"],
    "biceps": ["back", "core"],
    "triceps": ["chest", "shoulders"],
    "legs": ["core"],
    "core": ["back", "shoulders"],
}

# Used by --muscles so the skill can ask "what have I been doing for chest?"
MUSCLE_CATEGORIES = {
    "chest": {"BENCH_PRESS", "FLYE", "PUSH_UP"},
    "shoulders": {"SHOULDER_PRESS", "LATERAL_RAISE", "SHRUG"},
    "back": {"ROW", "PULL_UP", "PULLDOWN", "SHRUG"},
    "biceps": {"CURL"},
    "triceps": {"TRICEPS_EXTENSION"},
    "legs": {"SQUAT", "DEADLIFT", "LUNGE", "LEG_CURL", "LEG_RAISE", "CALF_RAISE", "HIP_RAISE"},
    "quads": {"SQUAT", "LUNGE"},
    "hamstrings": {"DEADLIFT", "LEG_CURL"},
    "glutes": {"HIP_RAISE", "LUNGE", "SQUAT"},
    "core": {"CORE", "CRUNCH", "PLANK", "LEG_RAISE"},
}
