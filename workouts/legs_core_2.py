# Legs & Core 2 — Thu 13 Aug 2026
# Run: garmin upload workouts/legs_core_2.py
#
# Targets: Back squat 105kg (+5, progressing) · Leg press 140kg (HOLD, rebuild from 200)
#          Bulgarian split squat 18kg (+2, ready) · Hip thrust 40kg (baseline, repeat)
#          Leg curl 38.5kg (+2.5) · Seated calf 39kg x14 (adherence-corrected from 20)
#          Cable crunch 52.5kg (+2.5) · Hanging leg raise x7 (adherence-corrected from 10)
# NOTE: Romanian deadlift dropped — stalled at 60kg for 8 sessions. Hamstrings covered by
#       hip thrust + leg curl instead; RDL comes back as a lower-rep sumo/DB variant next block.

WORKOUT = {
    "name": "Legs & Core 2",
    "description": "Squat-led. RDL swapped out after an 8-session stall; leg press holds at 140kg to rebuild. Core deficit addressed. ~47 min.",
    "exercises": [
        {"name": "BARBELL_BACK_SQUAT",             "category": "SQUAT",     "sets": 4, "reps": 6,  "rest_seconds": 90},
        {"name": "LEG_PRESS",                      "category": "SQUAT",     "sets": 3, "reps": 12, "rest_seconds": 75},
        {"name": "DUMBBELL_BULGARIAN_SPLIT_SQUAT", "category": "LUNGE",     "sets": 3, "reps": 10, "rest_seconds": 75},
        {"name": "BARBELL_HIP_THRUST_WITH_BENCH",  "category": "HIP_RAISE", "sets": 3, "reps": 10, "rest_seconds": 75},
        {"name": "LEG_CURL",                       "category": "LEG_CURL",  "sets": 3, "reps": 8,  "rest_seconds": 60},
        {"name": "SEATED_CALF_RAISE",              "category": "CALF_RAISE","sets": 3, "reps": 14, "rest_seconds": 45},
        {"name": "CABLE_CRUNCH",                   "category": "CRUNCH",    "sets": 3, "reps": 12, "rest_seconds": 60},
        {"name": "HANGING_LEG_RAISE",              "category": "LEG_RAISE", "sets": 3, "reps": 7,  "rest_seconds": 45},
    ],
}
