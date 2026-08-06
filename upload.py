#!/usr/bin/env python3
"""
Validate a workout and push it to Garmin Connect.

Kept so existing commands and docs keep working; `garmin upload` does the same
thing. The implementation lives in garmin_workouts/cli.py.
"""

import sys

from garmin_workouts.cli import main

if __name__ == "__main__":
    main(["upload"] + sys.argv[1:])
