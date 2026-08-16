# Back & Biceps 4 — Wed 19 Aug 2026  [Option A: heavy row-led]
# Run: garmin upload workouts/back_biceps_4.py
#
# The two "regressed" rows were mislogs. Holding them light worked — both came back
# well above the old numbers, so ride the momentum.
#
# Targets: Reverse-grip barbell row 80 -> 85kg x8 (progressing)
#          Seated cable row 55 -> 57.5kg x10 (progressing)
#          30-deg pulldown 52kg (HOLD until all sets reach 9)
#          Chest-supported DB row 20kg (baseline, repeat to establish trend)
#          Barbell shrug 60kg (HOLD — regressed from 70, rebuild)
#          Incline DB curl 18 -> 20kg · Hammer curl 12 -> 14kg · Concentration curl 14 -> 16kg
# NOTE: barbell biceps curl still omitted — log has read 19kg vs your usual 35kg for weeks.
# NOTE: reverse EZ-bar curl omitted — regressed 35 -> 20kg, and there is already enough
#       curl volume here. Bring it back light next block.

WORKOUT = {
    "name": "Back & Biceps 4",
    "description": "Heavy row day. Reverse-grip row to 85kg, cable row to 57.5kg — both flying after the rebuild. ~47 min.",
    "exercises": [
        {"name": "REVERSE_GRIP_BARBELL_ROW",     "category": "ROW",     "sets": 4, "reps": 8,  "rest_seconds": 90},
        {"name": "30_DEGREE_LAT_PULLDOWN",       "category": "PULL_UP", "sets": 3, "reps": 9,  "rest_seconds": 75},
        {"name": "SEATED_CABLE_ROW",             "category": "ROW",     "sets": 3, "reps": 10, "rest_seconds": 75},
        {"name": "CHEST_SUPPORTED_DUMBBELL_ROW", "category": "ROW",     "sets": 3, "reps": 10, "rest_seconds": 75},
        {"name": "BARBELL_SHRUG",                "category": "SHRUG",   "sets": 3, "reps": 10, "rest_seconds": 60},
        {"name": "INCLINE_DUMBBELL_BICEPS_CURL", "category": "CURL",    "sets": 3, "reps": 10, "rest_seconds": 60},
        {"name": "DUMBBELL_HAMMER_CURL",         "category": "CURL",    "sets": 3, "reps": 12, "rest_seconds": 45},
        {"name": "ONE_ARM_CONCENTRATION_CURL",   "category": "CURL",    "sets": 3, "reps": 8,  "rest_seconds": 45},
    ],
}

# Uploaded to Garmin Connect — this file is no longer a draft.
UPLOADED = "2026-08-16T20:48:15+00:00"
