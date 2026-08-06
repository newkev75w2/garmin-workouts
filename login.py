#!/usr/bin/env python3
"""
One-time interactive Garmin Connect login.

Kept so existing commands and docs keep working; `garmin login` does the same
thing. The implementation lives in garmin_workouts/cli.py.
"""

import sys

from garmin_workouts.cli import main

if __name__ == "__main__":
    main(["login"] + sys.argv[1:])
