# Shoulders & Triceps 2 — Fri 14 Aug 2026  [Option B, rebalanced 4 shoulders / 4 triceps]
# Run: garmin upload workouts/shoulders_triceps_2.py
#
# Targets: Arnold press ~16-18kg (new movement, start below your 18kg seated DB press)
#          Overhead DB press 18kg (hold, chase all sets to 9)
#          DB lateral raise 11kg (+1, ready)
#          Cable overhead triceps ext 19kg (+2, ready)
#          Reverse-grip pressdown / lying EZ ext — judge by feel, no clean history
#
# NOTE: seated rear lateral raise logged 39kg vs your usual 12kg — use ~12kg, not the log.
# NOTE: no barbell overhead press this session, so the 38kg seated BB press holds another week.
# NOTE: triceps work deliberately avoids Monday's movements (seated DB overhead ext, cable
#       lying ext, pressdown, rope pressdown).
# NOTE: close-grip bench replaces weighted dip at the user's request. It sits after Arnold press,
#       so front delts are already fatigued — start conservatively, this is a triceps movement
#       here, not a bench PR attempt. No history for it, so treat this session as a baseline.
# NOTE: DUMBBELL_LATERAL_RAISE is Garmin's STANDING entry (SEATED_LATERAL_RAISE is separate).
#       Kept standing because all 8 sessions of history and the +1kg verdict sit on this entry.

WORKOUT = {
    "name": "Shoulders & Triceps 2",
    "description": "Even 4/4 split. Arnold press leads, laterals progress to 11kg, dips and EZ-bar triceps. ~47 min.",
    "exercises": [
        # --- Shoulders ---
        {"name": "ARNOLD_PRESS",                        "category": "SHOULDER_PRESS",    "sets": 4, "reps": 10, "rest_seconds": 75},
        {"name": "OVERHEAD_DUMBBELL_PRESS",             "category": "SHOULDER_PRESS",    "sets": 3, "reps": 10, "rest_seconds": 75},
        {"name": "DUMBBELL_LATERAL_RAISE",              "category": "LATERAL_RAISE",     "sets": 4, "reps": 12, "rest_seconds": 60},
        {"name": "SEATED_REAR_LATERAL_RAISE",           "category": "LATERAL_RAISE",     "sets": 3, "reps": 12, "rest_seconds": 45},
        # --- Triceps ---
        {"name": "CLOSE_GRIP_BARBELL_BENCH_PRESS",      "category": "BENCH_PRESS",       "sets": 3, "reps": 8,  "rest_seconds": 90},
        {"name": "CABLE_OVERHEAD_TRICEPS_EXTENSION",    "category": "TRICEPS_EXTENSION", "sets": 3, "reps": 10, "rest_seconds": 60},
        {"name": "LYING_EZ_BAR_TRICEPS_EXTENSION",      "category": "TRICEPS_EXTENSION", "sets": 3, "reps": 10, "rest_seconds": 60},
        {"name": "REVERSE_GRIP_TRICEPS_PRESSDOWN",      "category": "TRICEPS_EXTENSION", "sets": 3, "reps": 15, "rest_seconds": 45},
    ],
}

# Uploaded to Garmin Connect — this file is no longer a draft.
UPLOADED = "2026-08-13T08:08:24+00:00"
