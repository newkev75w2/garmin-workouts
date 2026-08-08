# Legs & Core — hypertrophy (Wed 2026-08-12)
# Run: garmin upload workouts/legs_core_1.py

WORKOUT = {
    "name": "Legs & Core 1",
    "description": "Squat 105kg x6. RDL swapped to sumo deadlift (RDL stalled 8 sessions at 60kg). Leg press hold 140kg. Calves 39kg x14.",
    "exercises": [
        {"name": "BARBELL_BACK_SQUAT",            "category": "SQUAT",      "sets": 4, "reps": 6,  "rest_seconds": 90},
        {"name": "SUMO_DEADLIFT",                 "category": "DEADLIFT",   "sets": 4, "reps": 6,  "rest_seconds": 90},
        {"name": "LEG_PRESS",                     "category": "SQUAT",      "sets": 3, "reps": 12, "rest_seconds": 75},
        {"name": "DUMBBELL_BULGARIAN_SPLIT_SQUAT","category": "LUNGE",      "sets": 3, "reps": 10, "rest_seconds": 75},
        {"name": "HIP_RAISE",                     "category": "HIP_RAISE",  "sets": 3, "reps": 12, "rest_seconds": 45},
        {"name": "SEATED_CALF_RAISE",             "category": "CALF_RAISE", "sets": 3, "reps": 14, "rest_seconds": 45},
        {"name": "CABLE_CRUNCH",                  "category": "CRUNCH",     "sets": 3, "reps": 12, "rest_seconds": 60},
        {"name": "HANGING_LEG_RAISE",             "category": "LEG_RAISE",  "sets": 3, "reps": 7,  "rest_seconds": 60},
    ],
}
