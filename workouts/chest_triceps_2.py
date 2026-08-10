# Chest & Triceps 2 — Mon 10 Aug 2026  [Option B: dumbbell & cable, no barbell]
# Run: garmin upload workouts/chest_triceps_2.py
#
# Targets: Incline DB 26kg x7 (adherence-corrected from 10) · DB Bench 30kg (hold, chase all sets to 10)
#          Cable Crossover 17kg (+2, ready) · Triceps Pressdown 19kg (hold until all sets reach 12)
# NOTE: no barbell bench this session — deliberate, readiness is 35.7/100. The 70 -> 75kg
#       jump is still banked and waiting; take it next chest day.

WORKOUT = {
    "name": "Chest & Triceps 2",
    "description": "Dumbbell & cable pressing, four triceps angles. No barbell — joint-friendly, low-risk while readiness is down. ~47 min.",
    "exercises": [
        {"name": "INCLINE_DUMBBELL_BENCH_PRESS",               "category": "BENCH_PRESS",       "sets": 4, "reps": 7,  "rest_seconds": 75},
        {"name": "DUMBBELL_BENCH_PRESS",                       "category": "BENCH_PRESS",       "sets": 4, "reps": 8,  "rest_seconds": 75},
        {"name": "INCLINE_DUMBBELL_FLYE",                      "category": "FLYE",              "sets": 3, "reps": 12, "rest_seconds": 60},
        {"name": "CABLE_CROSSOVER",                            "category": "FLYE",              "sets": 3, "reps": 15, "rest_seconds": 60},
        {"name": "SEATED_DUMBBELL_OVERHEAD_TRICEPS_EXTENSION", "category": "TRICEPS_EXTENSION", "sets": 3, "reps": 10, "rest_seconds": 60},
        {"name": "CABLE_LYING_TRICEPS_EXTENSION",              "category": "TRICEPS_EXTENSION", "sets": 3, "reps": 12, "rest_seconds": 60},
        {"name": "TRICEPS_PRESSDOWN",                          "category": "TRICEPS_EXTENSION", "sets": 3, "reps": 12, "rest_seconds": 60},
        {"name": "ROPE_PRESSDOWN",                             "category": "TRICEPS_EXTENSION", "sets": 3, "reps": 15, "rest_seconds": 45},
    ],
}

# Uploaded to Garmin Connect — this file is no longer a draft.
UPLOADED = "2026-08-10T10:07:41+00:00"
