#!/usr/bin/env python3
"""
Check a workout's exercises against the Garmin FIT SDK.

Kept so existing commands and docs keep working; `garmin validate` does the same
thing. The implementation lives in garmin_workouts/cli.py.
"""

import sys

from garmin_workouts.cli import main

if __name__ == "__main__":
    main(["validate"] + sys.argv[1:])
