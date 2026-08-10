# Chest & Triceps 2 — Mon 10 Aug 2026
# Run: garmin upload workouts/chest_triceps_2.py
#
# Targets: Bench 75kg (+5, progressing) · Incline Smith 54.5kg (+2.5, ready)
#          DB Bench 30kg (hold, reps first) · Cable Crossover 17kg (+2, ready)
#          Overhead cable ext 19kg (+2, ready) · Rope pressdown 19kg (hold)

WORKOUT = {
    "name": "Chest & Triceps 2",
    "description": "Barbell-led press day. Bench to 75kg, incline Smith to 54.5kg, cable+rope triceps finish. ~47 min.",
    "exercises": [
        {"name": "BARBELL_BENCH_PRESS",              "category": "BENCH_PRESS",        "sets": 4, "reps": 6,  "rest_seconds": 90},
        {"name": "INCLINE_SMITH_MACHINE_BENCH_PRESS", "category": "BENCH_PRESS",       "sets": 3, "reps": 8,  "rest_seconds": 75},
        {"name": "DUMBBELL_BENCH_PRESS",             "category": "BENCH_PRESS",        "sets": 3, "reps": 8,  "rest_seconds": 75},
        {"name": "CABLE_CROSSOVER",                  "category": "FLYE",               "sets": 3, "reps": 15, "rest_seconds": 60},
        {"name": "CLOSE_GRIP_BARBELL_BENCH_PRESS",   "category": "BENCH_PRESS",        "sets": 3, "reps": 8,  "rest_seconds": 75},
        {"name": "CABLE_OVERHEAD_TRICEPS_EXTENSION", "category": "TRICEPS_EXTENSION",  "sets": 3, "reps": 10, "rest_seconds": 60},
        {"name": "ROPE_PRESSDOWN",                   "category": "TRICEPS_EXTENSION",  "sets": 3, "reps": 12, "rest_seconds": 60},
        {"name": "REVERSE_GRIP_TRICEPS_PRESSDOWN",   "category": "TRICEPS_EXTENSION",  "sets": 3, "reps": 15, "rest_seconds": 45},
    ],
}
