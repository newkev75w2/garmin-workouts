# Shoulders & Core 2 — Thu 20 Aug 2026  [Option A: heavy, 6 exercises, all 4 sets]
# Run: garmin upload workouts/shoulders_core_2.py
#
# Last session before the holiday. Every movement at 4 sets — four of your shoulder lifts
# are being HELD at load until you complete the rep target on all sets, so more sets at the
# same weight is exactly what clears them.
#
# Targets: Seated BB shoulder press 38kg (HOLD until all 4 sets reach 8)
#          Arnold press 16kg (baseline, repeat to establish trend)
#          DB lateral raise 14kg (HOLD until all sets reach 12)
#          Seated rear lateral 14kg (HOLD until all sets reach 12)
#          Cable crunch 50 -> 52.5kg (progressing)
#          Hanging leg raise x7 (adherence-corrected from 10)
#
# NOTE: overhead DB press omitted — regressed 28 -> 18kg; seated barbell press covers the
#       vertical push. Rebuild it next block.
# NOTE: 24 sets over 6 movements. Fewer exercises, more sets each — the shape that actually
#       clears a "hold until all sets hit the target" verdict.

WORKOUT = {
    "name": "Shoulders & Core 2",
    "description": "Six movements, all 4 sets. Built to clear the rep targets you're being held at. ~45 min.",
    "exercises": [
        {"name": "SEATED_BARBELL_SHOULDER_PRESS", "category": "SHOULDER_PRESS", "sets": 4, "reps": 8,  "rest_seconds": 90},
        {"name": "ARNOLD_PRESS",                  "category": "SHOULDER_PRESS", "sets": 4, "reps": 9,  "rest_seconds": 75},
        {"name": "DUMBBELL_LATERAL_RAISE",        "category": "LATERAL_RAISE",  "sets": 4, "reps": 12, "rest_seconds": 60},
        {"name": "SEATED_REAR_LATERAL_RAISE",     "category": "LATERAL_RAISE",  "sets": 4, "reps": 12, "rest_seconds": 60},
        {"name": "CABLE_CRUNCH",                  "category": "CRUNCH",         "sets": 4, "reps": 12, "rest_seconds": 60},
        {"name": "HANGING_LEG_RAISE",             "category": "LEG_RAISE",      "sets": 4, "reps": 7,  "rest_seconds": 60},
    ],
}

# Uploaded to Garmin Connect — this file is no longer a draft.
UPLOADED = "2026-08-16T20:48:17+00:00"
