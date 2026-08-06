# Shoulders & Core (session 1)
# Run: python upload.py workouts/shoulders_core_1.py
#
# Built from coach.py verdicts on 2026-08-06, for training on 2026-08-07.
# Target loads are notes only — Garmin workout steps carry no weight field.
#
# Shoulders (50 sets logged, 2 days rested — least-trained recovered group).
# Two pressing movements, not three: seated barbell + push press is enough
# vertical pressing for one session, and the third pushed it past the time budget.
#   BARBELL_SHRUG                 [progressing] -> 75kg  (hit 10/10 at 70kg, earned the jump)
#   SEATED_REAR_LATERAL_RAISE     [progressing] -> 14kg  (hit 12/12 at 12kg)
#   SEATED_BARBELL_SHOULDER_PRESS [progressing] -> hold 35kg until all 3 sets reach 8
#   DUMBBELL_PUSH_PRESS           [progressing] -> hold 52kg until both sets reach 10
#   DUMBBELL_LATERAL_RAISE        [holding]     -> hold 12kg, last session was 8/12
#
# Core (16 sets logged vs 120 for legs, untrained since 27 July):
#   Every core verdict is [stale] or [regressed], and the logged weights are not
#   trustworthy — HANGING_LEG_RAISE and _45_DEGREE_PLANK both read 73kg, which is
#   bodyweight being recorded rather than load. So core is prescribed by reps and
#   deliberately conservative; rebuild the numbers before progressing anything.

WORKOUT = {
    "name": "Shoulders & Core 1",
    "description": "Shoulder volume with two earned load jumps, conservative core rebuild. ~48 min.",
    "exercises": [
        {"name": "SEATED_BARBELL_SHOULDER_PRESS",  "category": "SHOULDER_PRESS", "sets": 4, "reps": 8,  "rest_seconds": 90},
        {"name": "DUMBBELL_PUSH_PRESS",            "category": "SHOULDER_PRESS", "sets": 3, "reps": 10, "rest_seconds": 90},
        {"name": "BARBELL_SHRUG",                  "category": "SHRUG",          "sets": 3, "reps": 10, "rest_seconds": 75},
        {"name": "DUMBBELL_LATERAL_RAISE",         "category": "LATERAL_RAISE",  "sets": 3, "reps": 12, "rest_seconds": 60},
        {"name": "SEATED_REAR_LATERAL_RAISE",      "category": "LATERAL_RAISE",  "sets": 3, "reps": 12, "rest_seconds": 60},
        {"name": "CABLE_CRUNCH",                   "category": "CRUNCH",         "sets": 3, "reps": 12, "rest_seconds": 60},
        {"name": "HANGING_LEG_RAISE",              "category": "LEG_RAISE",      "sets": 3, "reps": 10, "rest_seconds": 60},
        {"name": "PLANK",                          "category": "PLANK",          "sets": 3, "seconds": 45, "rest_seconds": 45},
    ],
}
