# Chest & Triceps 3 — Tue 18 Aug 2026  [Option A: heavy barbell, 6 exercises]
# Run: garmin upload workouts/chest_triceps_3.py
#
# Barbell bench untrained since 27 Jul — 22 days, with a banked +5kg. Skipped twice
# by choosing dumbbell options. This session takes it, at 5 sets.
#
# Targets: Bench 70 -> 75kg x6 (progressing) — 5 working sets
#          Incline barbell bench — no history, start conservative and find it
#          Close-grip bench 35 -> 37.5kg (ready)
#          Cable crossover 17 -> 19kg (progressing)
#          Cable overhead triceps ext 17 -> 19kg (ready)
#          Triceps pressdown 41 -> 43.5kg (progressing)
#
# NOTE: three barbell presses at 90s rest. This is the most CNS-costly session of the week
#       and it lands on day 2 of 4 — if bar speed drops badly on bench set 4, stop at 4 sets
#       rather than grinding set 5.

WORKOUT = {
    "name": "Chest & Triceps 3",
    "description": "Heavy barbell pressing. Three bar movements at 90s rest, cashes the 22-day-old 75kg bench. ~45 min.",
    "exercises": [
        {"name": "BARBELL_BENCH_PRESS",              "category": "BENCH_PRESS",       "sets": 5, "reps": 6,  "rest_seconds": 90},
        {"name": "INCLINE_BARBELL_BENCH_PRESS",      "category": "BENCH_PRESS",       "sets": 4, "reps": 8,  "rest_seconds": 90},
        {"name": "CLOSE_GRIP_BARBELL_BENCH_PRESS",   "category": "BENCH_PRESS",       "sets": 4, "reps": 8,  "rest_seconds": 90},
        {"name": "CABLE_CROSSOVER",                  "category": "FLYE",              "sets": 3, "reps": 15, "rest_seconds": 60},
        {"name": "CABLE_OVERHEAD_TRICEPS_EXTENSION", "category": "TRICEPS_EXTENSION", "sets": 3, "reps": 10, "rest_seconds": 60},
        {"name": "TRICEPS_PRESSDOWN",                "category": "TRICEPS_EXTENSION", "sets": 3, "reps": 12, "rest_seconds": 60},
    ],
}

# Uploaded to Garmin Connect — this file is no longer a draft.
UPLOADED = "2026-08-16T20:48:14+00:00"
