# Back & Biceps (session 1)
# Run: python upload.py workouts/back_biceps_1.py
#
# Built from coach.py verdicts on 2026-08-06. Target loads are notes only —
# Garmin workout steps carry no weight field.
#
#   ALTERNATING_DUMBBELL_ROW      [progressing] -> 41.5kg
#   BARBELL_SHRUG                 [progressing] -> 75kg
#   REVERSE_EZ_BAR_CURL           [progressing] -> 37.5kg
#   ONE_ARM_CONCENTRATION_CURL    [ready]       -> 16kg  (hit 6/6 at 14kg)
#   DUMBBELL_HAMMER_CURL          [progressing] -> hold 12kg until all 3 sets reach 12
#   _30_DEGREE_LAT_PULLDOWN       [holding]     -> hold 52kg
#   REVERSE_GRIP_BARBELL_ROW      [regressed]   -> hold 60kg (see note below)
#   SEATED_CABLE_ROW              [regressed]   -> hold 35kg, rebuild toward 52kg
#
# Note: the 2026-08-04 session also logged 6x80kg and 5x80kg with no exercise
# name attached. If that was the barbell row, it did not regress at all — worth
# confirming before cutting load further.

WORKOUT = {
    "name": "Back & Biceps 1",
    "description": "Rebuild rows at current load, progress dumbbell + curl work. ~48 min.",
    "exercises": [
        {"name": "REVERSE_GRIP_BARBELL_ROW",   "category": "ROW",     "sets": 4, "reps": 8,  "rest_seconds": 90},
        {"name": "30_DEGREE_LAT_PULLDOWN",     "category": "PULL_UP", "sets": 3, "reps": 9,  "rest_seconds": 90},
        {"name": "ALTERNATING_DUMBBELL_ROW",   "category": "ROW",     "sets": 3, "reps": 10, "rest_seconds": 75},
        {"name": "SEATED_CABLE_ROW",           "category": "ROW",     "sets": 3, "reps": 11, "rest_seconds": 75},
        {"name": "BARBELL_SHRUG",              "category": "SHRUG",   "sets": 3, "reps": 10, "rest_seconds": 75},
        {"name": "REVERSE_EZ_BAR_CURL",        "category": "CURL",    "sets": 3, "reps": 12, "rest_seconds": 60},
        {"name": "ONE_ARM_CONCENTRATION_CURL", "category": "CURL",    "sets": 3, "reps": 6,  "rest_seconds": 60},
        {"name": "DUMBBELL_HAMMER_CURL",       "category": "CURL",    "sets": 3, "reps": 12, "rest_seconds": 45},
    ],
}
