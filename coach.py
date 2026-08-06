#!/usr/bin/env python3
"""
Judge performance and say what to do next: python coach.py --suggest, --brief, --muscles.

Kept so existing commands and docs keep working; `garmin coach` does the same
thing. The implementation lives in garmin_workouts/cli.py.
"""

import sys

from garmin_workouts.cli import main

if __name__ == "__main__":
    argv = sys.argv[1:]
    # --suggest was a flag on coach.py; it is its own subcommand now.
    if "--suggest" in argv:
        argv = [a for a in argv if a != "--suggest"]
        main(["suggest"] + argv)
    else:
        main(["coach"] + argv)
