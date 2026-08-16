# Legs & Core 2 — Thu 13 Aug 2026  [Option B: hinge-led]
# Run: garmin upload workouts/legs_core_2.py
#
# This is the coach's literal prescription for the Romanian deadlift stall:
# 8 sessions at 60kg with no rep gain -> swap the variation AND drop the rep range.
# Sumo deadlift is NEW to you. Start ~60-65kg for the first set and work up only if
# 5 reps move cleanly. Establish a baseline this week; progress from the next session.
#
# Targets: Sumo DL ~60-65kg x5 (new, conservative) · Front squat light, first exposure
#          Leg press 140kg (HOLD, rebuild from 200) · Leg curl 38.5kg (+2.5)
#          Standing calf 50kg (baseline, repeat)
# NOTE: no back squat this session, so the 100 -> 105kg jump waits for next legs day.
#       Deadlift is programmed FIRST so you are not pulling on pre-fatigued legs.
# NOTE (14 Aug): core block adjusted for freshly waxed torso/armpits. Hanging knee raise
#       (arms overhead = armpit friction) and plank (torso on floor mat) swapped for
#       Russian twist and cable side bend — both seated/standing, no skin contact with
#       equipment. Revert to hanging knee raise + plank next legs session.

WORKOUT = {
    "name": "Legs & Core 2",
    "description": "Hinge-led. Sumo deadlift replaces the 8-session RDL stall at a lower rep range. Leg press holds 140kg. ~46 min.",
    "exercises": [
        {"name": "SUMO_DEADLIFT",         "category": "DEADLIFT",   "sets": 4, "reps": 5,  "rest_seconds": 90},
        {"name": "BARBELL_FRONT_SQUAT",   "category": "SQUAT",      "sets": 3, "reps": 8,  "rest_seconds": 90},
        {"name": "LEG_PRESS",             "category": "SQUAT",      "sets": 3, "reps": 12, "rest_seconds": 75},
        {"name": "LEG_CURL",              "category": "LEG_CURL",   "sets": 3, "reps": 8,  "rest_seconds": 60},
        {"name": "STANDING_CALF_RAISE",   "category": "CALF_RAISE", "sets": 3, "reps": 12, "rest_seconds": 45},
        {"name": "KNEELING_CABLE_CRUNCH", "category": "CRUNCH",     "sets": 3, "reps": 15, "rest_seconds": 60},
        {"name": "RUSSIAN_TWIST",         "category": "CORE",       "sets": 3, "reps": 20, "rest_seconds": 45},
        {"name": "CABLE_SIDE_BEND",       "category": "CORE",       "sets": 3, "reps": 15, "rest_seconds": 45},
    ],
}
