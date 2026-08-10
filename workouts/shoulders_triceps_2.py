# Shoulders & Triceps 2 — Fri 14 Aug 2026  [Option B: dumbbell-led, five delt angles]
# Run: garmin upload workouts/shoulders_triceps_2.py
#
# Targets: Arnold press ~16-18kg (new movement, start below your 18kg seated DB press)
#          Overhead DB press 18kg (hold, chase all sets to 9)
#          Seated lateral raise 11kg (+1, ready) · Triceps pressdown 19kg (hold until all sets reach 12)
# NOTE: seated rear lateral raise logged 39kg vs your usual 12kg — use ~12kg, not the log.
#       No barbell overhead press this session, so the 38kg press holds another week.

WORKOUT = {
    "name": "Shoulders & Triceps 2",
    "description": "Dumbbell & cable delts from five angles, no barbell overhead. Targets the shoulder volume deficit. ~46 min.",
    "exercises": [
        {"name": "ARNOLD_PRESS",                        "category": "SHOULDER_PRESS",    "sets": 4, "reps": 10, "rest_seconds": 75},
        {"name": "OVERHEAD_DUMBBELL_PRESS",             "category": "SHOULDER_PRESS",    "sets": 3, "reps": 10, "rest_seconds": 75},
        {"name": "ONE_ARM_CABLE_LATERAL_RAISE",         "category": "LATERAL_RAISE",     "sets": 4, "reps": 15, "rest_seconds": 60},
        {"name": "SEATED_LATERAL_RAISE",                "category": "LATERAL_RAISE",     "sets": 3, "reps": 12, "rest_seconds": 60},
        {"name": "BENT_OVER_LATERAL_RAISE",             "category": "LATERAL_RAISE",     "sets": 3, "reps": 15, "rest_seconds": 45},
        {"name": "SEATED_REAR_LATERAL_RAISE",           "category": "LATERAL_RAISE",     "sets": 3, "reps": 12, "rest_seconds": 45},
        {"name": "OVERHEAD_DUMBBELL_TRICEPS_EXTENSION", "category": "TRICEPS_EXTENSION", "sets": 3, "reps": 10, "rest_seconds": 60},
        {"name": "TRICEPS_PRESSDOWN",                   "category": "TRICEPS_EXTENSION", "sets": 3, "reps": 12, "rest_seconds": 60},
    ],
}
