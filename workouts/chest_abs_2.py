# Chest & Abs — Mixed angles, core-heavy (session 2)
# Run: python upload.py workouts/chest_abs_2.py
#
# Rest guide: max 90s. Compounds 90s, moderate 75s, isolation 60s, finisher 45s.
# All exercise/category pairs verified against the real Garmin FIT SDK enum
# (run `python validate.py workouts/chest_abs_2.py` to re-check).
#
# Target loads (Garmin steps carry no weight field — these live here only):
#   Decline DB Bench   ~26kg   new angle, start conservative
#   Close Grip Bench   ~35kg   unused 35 days, restart at last known
#   Body Weight Dip    bodyweight — log flagged check-data (19kg vs usual 45.5kg)
#   Cable Crossover    17kg    [ready] up from 15kg x15/15
#   Dumbbell Flye      ~12kg
#   Kneeling Cable Crunch ~27kg (Cable Crunch stale 22 days, restart here)

WORKOUT = {
    "name": "Chest & Abs 2",
    "description": "Decline/close-grip chest angles, dips, big core block. 17kg crossovers. ~50 min.",
    "exercises": [
        {"name": "DECLINE_DUMBBELL_BENCH_PRESS",   "category": "BENCH_PRESS", "sets": 3, "reps": 10, "rest_seconds": 75},
        {"name": "CLOSE_GRIP_BARBELL_BENCH_PRESS", "category": "BENCH_PRESS", "sets": 3, "reps": 10, "rest_seconds": 75},
        {"name": "BODY_WEIGHT_DIP",                "category": "TRICEPS_EXTENSION", "sets": 3, "reps": 10, "rest_seconds": 75},
        {"name": "CABLE_CROSSOVER",                "category": "FLYE",        "sets": 4, "reps": 15, "rest_seconds": 60},
        {"name": "DUMBBELL_FLYE",                  "category": "FLYE",        "sets": 3, "reps": 12, "rest_seconds": 60},
        {"name": "HANGING_LEG_RAISE",              "category": "LEG_RAISE",   "sets": 3, "reps": 12, "rest_seconds": 60},
        {"name": "KNEELING_CABLE_CRUNCH",          "category": "CRUNCH",      "sets": 3, "reps": 15, "rest_seconds": 60},
        {"name": "RUSSIAN_TWIST",                  "category": "CORE",        "sets": 3, "reps": 20, "rest_seconds": 45},
        {"name": "PLANK",                          "category": "PLANK",       "sets": 3, "seconds": 45, "rest_seconds": 45},
    ],
}
