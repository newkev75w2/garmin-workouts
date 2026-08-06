#!/usr/bin/env python3
"""
Pull completed strength sessions from Garmin Connect.

Kept so existing commands and docs keep working; `garmin sync` does the same
thing. The implementation lives in garmin_workouts/cli.py.
"""

import sys

from garmin_workouts.cli import main

if __name__ == "__main__":
    main(["sync"] + sys.argv[1:])
