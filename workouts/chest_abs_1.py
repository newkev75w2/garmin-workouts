# Chest & Abs — Dumbbell & cable (session 1)
# Run: python upload.py workouts/chest_abs_1.py
#
# Rest guide: max 90s. Compounds 90s, moderate 75s, isolation 60s, finisher 45s.
# All exercise/category pairs verified against the real Garmin FIT SDK enum
# (run `python validate.py workouts/chest_abs_1.py` to re-check).

WORKOUT = {
    "name": "Chest & Abs 1",
    "description": "Dumbbell & cable chest volume, cable-led core finish. ~45 min.",
    "exercises": [
        {"name": "INCLINE_DUMBBELL_BENCH_PRESS", "category": "BENCH_PRESS", "sets": 4, "reps": 10, "rest_seconds": 75},
        {"name": "DUMBBELL_BENCH_PRESS",         "category": "BENCH_PRESS", "sets": 4, "reps": 10, "rest_seconds": 75},
        {"name": "INCLINE_DUMBBELL_FLYE",        "category": "FLYE",        "sets": 3, "reps": 12, "rest_seconds": 60},
        {"name": "CABLE_CROSSOVER",              "category": "FLYE",        "sets": 3, "reps": 15, "rest_seconds": 60},
        {"name": "KNEELING_CABLE_CRUNCH",        "category": "CRUNCH",      "sets": 3, "reps": 15, "rest_seconds": 60},
        {"name": "HANGING_KNEE_RAISE",           "category": "LEG_RAISE",   "sets": 3, "reps": 15, "rest_seconds": 45},
        {"name": "RUSSIAN_TWIST",                "category": "CORE",        "sets": 3, "reps": 20, "rest_seconds": 45},
        {"name": "SIDE_PLANK",                   "category": "PLANK",       "sets": 3, "seconds": 45, "rest_seconds": 45},
    ],
}
