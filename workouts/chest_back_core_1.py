# Chest, Back & Core — antagonist pump day (Fri 2026-08-14)
# Run: workouts/chest_back_core_1.py

WORKOUT = {
    "name": "Chest Back & Core 1",
    "description": "Paired push/pull volume day, shorter rests. DB bench 30kg, crossover 17kg, cable crunch 52.5kg.",
    "exercises": [
        {"name": "DUMBBELL_BENCH_PRESS",      "category": "BENCH_PRESS", "sets": 4, "reps": 8,  "rest_seconds": 75},
        {"name": "CHEST_SUPPORTED_DUMBBELL_ROW","category": "ROW",       "sets": 4, "reps": 10, "rest_seconds": 75},
        {"name": "INCLINE_DUMBBELL_FLYE",     "category": "FLYE",        "sets": 3, "reps": 12, "rest_seconds": 60},
        {"name": "WIDE_GRIP_LAT_PULLDOWN",    "category": "PULL_UP",     "sets": 3, "reps": 10, "rest_seconds": 60},
        {"name": "CABLE_CROSSOVER",           "category": "FLYE",        "sets": 3, "reps": 15, "rest_seconds": 45},
        {"name": "CABLE_ROW_STANDING",        "category": "ROW",         "sets": 3, "reps": 12, "rest_seconds": 60},
        {"name": "CABLE_CRUNCH",              "category": "CRUNCH",      "sets": 3, "reps": 12, "rest_seconds": 45},
        {"name": "RUSSIAN_TWIST",             "category": "CORE",        "sets": 3, "reps": 20, "rest_seconds": 45},
        {"name": "PLANK",                     "category": "PLANK",       "sets": 3, "seconds": 45, "rest_seconds": 45},
    ],
}
