# Back & Biceps 3 — Tue 11 Aug 2026
# Run: garmin upload workouts/back_biceps_3.py
#
# Rebuild session for the two regressed rows.
# Targets: Reverse-grip row 60kg (HOLD, rebuild from 70) · Seated cable row 35kg (HOLD, rebuild from 52)
#          30-deg pulldown 52kg (hold until all sets hit 9) · Alt DB row 41.5kg (+2.5, progressing)
#          Shrug 75kg (+5, ready) · Incline curl 20kg (hold) · Hammer 12kg (hold) · Reverse EZ 37.5kg (+2.5)
# NOTE: barbell biceps curl deliberately omitted — last log reads 19kg vs your usual 35kg (check-data).

WORKOUT = {
    "name": "Back & Biceps 3",
    "description": "Row rebuild — hold 60kg reverse-grip and 35kg cable row, chase reps not load. Curls progress. ~47 min.",
    "exercises": [
        {"name": "REVERSE_GRIP_BARBELL_ROW",   "category": "ROW",     "sets": 4, "reps": 8,  "rest_seconds": 90},
        {"name": "30_DEGREE_LAT_PULLDOWN",     "category": "PULL_UP", "sets": 3, "reps": 9,  "rest_seconds": 75},
        {"name": "SEATED_CABLE_ROW",           "category": "ROW",     "sets": 3, "reps": 10, "rest_seconds": 75},
        {"name": "ALTERNATING_DUMBBELL_ROW",   "category": "ROW",     "sets": 3, "reps": 10, "rest_seconds": 75},
        {"name": "BARBELL_SHRUG",              "category": "SHRUG",   "sets": 3, "reps": 10, "rest_seconds": 60},
        {"name": "INCLINE_DUMBBELL_BICEPS_CURL", "category": "CURL",  "sets": 3, "reps": 10, "rest_seconds": 60},
        {"name": "DUMBBELL_HAMMER_CURL",       "category": "CURL",    "sets": 3, "reps": 12, "rest_seconds": 60},
        {"name": "REVERSE_EZ_BAR_CURL",        "category": "CURL",    "sets": 3, "reps": 12, "rest_seconds": 45},
    ],
}
