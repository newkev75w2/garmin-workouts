#!/usr/bin/env python3
"""
Pull completed strength sessions down from Garmin Connect into performance.json.

    python sync.py            # last 30 activities
    python sync.py 100        # look further back

Re-running is safe — sessions already pulled are skipped. The work itself lives
in garmin_workouts/sync.py.
"""

from __future__ import annotations

import argparse

from garmin_workouts.sync import sync


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pull completed strength sessions from Garmin Connect."
    )
    parser.add_argument(
        "limit", nargs="?", type=int, default=30,
        help="how many recent activities to scan (default 30)",
    )
    sync(parser.parse_args().limit)


if __name__ == "__main__":
    main()
