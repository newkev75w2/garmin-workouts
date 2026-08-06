# Legs — Machine + free weight circuit, no barbell (session 1)
# Run: python upload.py workouts/legs_1.py
#
# Rest guide: max 90s. Compounds 90s, moderate 75s, isolation 60s, finisher 45s.
# All exercise/category pairs verified against the real Garmin FIT SDK enum
# (run `python validate.py workouts/legs_1.py` to re-check).
#
# Notes:
#  - "Booty builder machine" -> WEIGHTED_HIP_RAISE (category HIP_RAISE). Garmin has no
#    literal "hip thrust machine" entry, same situation as the pec deck - this is the
#    closest real loaded hip-raise/thrust match. Use the machine at the gym as normal.
#  - Lunge reps (DUMBBELL_LUNGE, DUMBBELL_REVERSE_LUNGE) are per leg, e.g. 3x12 = 12 reps
#    each leg per set.
#  - No barbell exercises in this session per request.

WORKOUT = {
    "name": "Legs 1",
    "description": "Machine + free weight circuit, no barbell. Quad/ham/glute/calf balance. ~48 min.",
    "exercises": [
        {"name": "ROMANIAN_DEADLIFT",      "category": "DEADLIFT",  "sets": 3, "reps": 10, "rest_seconds": 75},
        {"name": "LEG_PRESS",              "category": "SQUAT",     "sets": 4, "reps": 12, "rest_seconds": 75},
        {"name": "GOBLET_SQUAT",           "category": "SQUAT",     "sets": 3, "reps": 12, "rest_seconds": 60},
        {"name": "DUMBBELL_LUNGE",         "category": "LUNGE",     "sets": 3, "reps": 12, "rest_seconds": 60},
        {"name": "DUMBBELL_REVERSE_LUNGE", "category": "LUNGE",     "sets": 3, "reps": 10, "rest_seconds": 60},
        {"name": "WEIGHTED_HIP_RAISE",     "category": "HIP_RAISE", "sets": 3, "reps": 12, "rest_seconds": 60},
        {"name": "HIP_RAISE",              "category": "HIP_RAISE", "sets": 3, "reps": 15, "rest_seconds": 45},
        {"name": "STANDING_CALF_RAISE",    "category": "CALF_RAISE","sets": 3, "reps": 20, "rest_seconds": 45},
        {"name": "SEATED_CALF_RAISE",      "category": "CALF_RAISE","sets": 3, "reps": 20, "rest_seconds": 45},
    ],
}
