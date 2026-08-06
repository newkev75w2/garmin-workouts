# Chest & Shoulders — Machine + free weight mix (session 1)
# Run: python upload.py workouts/chest_shoulders_1.py
#
# Rest guide: max 90s. Compounds 90s, moderate 75s, isolation 60s.
# Every exercise/category pair below is verified against the real Garmin FIT SDK
# exercise enum (run `python validate.py workouts/chest_shoulders_1.py` to re-check).
# Notes on substitutions where no literal Garmin entry exists:
#  - "Chest Press Machine" -> DUMBBELL_BENCH_PRESS (no machine-specific entry exists)
#  - "Pec Deck" -> DUMBBELL_FLYE (Garmin has no PEC_DECK/PECK_DECK entry at all)
#  - "Rear Delt Fly Machine" -> KNEELING_REAR_FLYE (category FLYE)
#  - "Face Pull" -> FACE_PULL (category ROW, not LATERAL_RAISE)
#  - plain "Lateral Raise" isn't valid on its own -> DUMBBELL_LATERAL_RAISE

WORKOUT = {
    "name": "Chest & Shoulders 1",
    "description": "Machine + free weight mix, chest-led with shoulder finisher. ~46 min.",
    "exercises": [
        {"name": "DUMBBELL_BENCH_PRESS",          "category": "BENCH_PRESS",     "sets": 4, "reps": 10, "rest_seconds": 75},
        {"name": "INCLINE_DUMBBELL_BENCH_PRESS",  "category": "BENCH_PRESS",     "sets": 3, "reps": 10, "rest_seconds": 75},
        {"name": "DUMBBELL_FLYE",                 "category": "FLYE",            "sets": 3, "reps": 12, "rest_seconds": 60},
        {"name": "CABLE_CROSSOVER",               "category": "FLYE",            "sets": 3, "reps": 15, "rest_seconds": 60},
        {"name": "SEATED_DUMBBELL_SHOULDER_PRESS","category": "SHOULDER_PRESS",  "sets": 4, "reps": 10, "rest_seconds": 75},
        {"name": "DUMBBELL_LATERAL_RAISE",        "category": "LATERAL_RAISE",   "sets": 3, "reps": 15, "rest_seconds": 45},
        {"name": "KNEELING_REAR_FLYE",            "category": "FLYE",            "sets": 3, "reps": 12, "rest_seconds": 45},
        {"name": "FACE_PULL",                     "category": "ROW",             "sets": 3, "reps": 15, "rest_seconds": 45},
    ],
}
