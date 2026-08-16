# Legs & Core 3 — Mon 17 Aug 2026  [Option C: dense, 10 exercises, short rests]
# Run: garmin upload workouts/legs_core_3.py
#
# Legs untrained since 6 Aug (11 days). This option trades load for total volume:
# 30 sets across 10 movements at 45-60s rest, no bar on your back.
#
# Targets: Goblet squat 24kg (baseline, repeat) · Leg press 140kg (HOLD, rebuild from 200)
#          Walking DB lunge — no history, start light and find it
#          Bulgarian split squat 16 -> 18kg (ready) · Leg curl 36 -> 38.5kg (progressing)
#          Weighted hip raise 40kg (baseline, repeat) · Standing calf 50kg (baseline, repeat)
#          Cable crunch 50 -> 52.5kg (progressing)
#
# NOTE: no back squat, so the banked 100 -> 105kg jump waits another week. It has now been
#       20 days since 28 Jul — take it first thing next legs session.
# NOTE: Romanian deadlift omitted — stalled at 60kg for 8 sessions.

WORKOUT = {
    "name": "Legs & Core 3",
    "description": "Dense unilateral/machine legs. 30 sets, 45-60s rests, nothing on your back. ~47 min.",
    "exercises": [
        {"name": "GOBLET_SQUAT",                   "category": "SQUAT",      "sets": 3, "reps": 12, "rest_seconds": 60},
        {"name": "LEG_PRESS",                      "category": "SQUAT",      "sets": 3, "reps": 12, "rest_seconds": 60},
        {"name": "WALKING_DUMBBELL_LUNGE",         "category": "LUNGE",      "sets": 3, "reps": 12, "rest_seconds": 60},
        {"name": "DUMBBELL_BULGARIAN_SPLIT_SQUAT", "category": "LUNGE",      "sets": 3, "reps": 10, "rest_seconds": 45},
        {"name": "WEIGHTED_HIP_RAISE",             "category": "HIP_RAISE",  "sets": 3, "reps": 12, "rest_seconds": 45},
        {"name": "LEG_CURL",                       "category": "LEG_CURL",   "sets": 3, "reps": 8,  "rest_seconds": 45},
        {"name": "STANDING_CALF_RAISE",            "category": "CALF_RAISE", "sets": 3, "reps": 12, "rest_seconds": 45},
        {"name": "CABLE_CRUNCH",                   "category": "CRUNCH",     "sets": 3, "reps": 12, "rest_seconds": 45},
        {"name": "RUSSIAN_TWIST",                  "category": "CORE",       "sets": 3, "reps": 20, "rest_seconds": 45},
        {"name": "PLANK",                          "category": "PLANK",      "sets": 3, "seconds": 45, "rest_seconds": 45},
    ],
}

# Uploaded to Garmin Connect — this file is no longer a draft.
UPLOADED = "2026-08-16T20:48:08+00:00"
