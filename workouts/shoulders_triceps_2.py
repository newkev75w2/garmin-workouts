# Shoulders & Triceps 2 — Fri 14 Aug 2026
# Run: garmin upload workouts/shoulders_triceps_2.py
#
# Targets: Seated BB press 38kg (HOLD until all 4 sets reach 8) · Seated DB press 18kg (hold, chase 9s)
#          DB lateral raise 11kg (+1, ready) · Kneeling rear flye 39kg (baseline, repeat)
#          Face pull ~15kg (last log read 39kg — treat as bad data, use your usual)
#          Dips / lying EZ ext / reverse-grip pressdown — different triceps angles to Monday.

WORKOUT = {
    "name": "Shoulders & Triceps 2",
    "description": "Presses hold, laterals progress to 11kg. Triceps hit from angles Monday didn't use. ~48 min.",
    "exercises": [
        {"name": "SEATED_BARBELL_SHOULDER_PRESS",   "category": "SHOULDER_PRESS",    "sets": 4, "reps": 8,  "rest_seconds": 90},
        {"name": "SEATED_DUMBBELL_SHOULDER_PRESS",  "category": "SHOULDER_PRESS",    "sets": 3, "reps": 9,  "rest_seconds": 75},
        {"name": "DUMBBELL_LATERAL_RAISE",          "category": "LATERAL_RAISE",     "sets": 4, "reps": 12, "rest_seconds": 60},
        {"name": "KNEELING_REAR_FLYE",              "category": "FLYE",              "sets": 3, "reps": 12, "rest_seconds": 60},
        {"name": "FACE_PULL",                       "category": "ROW",               "sets": 3, "reps": 15, "rest_seconds": 45},
        {"name": "WEIGHTED_DIP",                    "category": "TRICEPS_EXTENSION", "sets": 3, "reps": 8,  "rest_seconds": 75},
        {"name": "LYING_EZ_BAR_TRICEPS_EXTENSION",  "category": "TRICEPS_EXTENSION", "sets": 3, "reps": 10, "rest_seconds": 60},
        {"name": "REVERSE_GRIP_TRICEPS_PRESSDOWN",  "category": "TRICEPS_EXTENSION", "sets": 3, "reps": 15, "rest_seconds": 45},
    ],
}
