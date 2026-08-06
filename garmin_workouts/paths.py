"""
Where this tool keeps its data.

Everything used to resolve as "next to the package", which is correct when the
project is run from a checkout and wrong the moment it is pip-installed —
`__file__` then points into site-packages, so performance.json, history.json and
the Garmin session token would be written there. Session tokens especially have
no business in site-packages.

Resolution order:

  1. $GARMIN_WORKOUTS_HOME, if set — explicit wins.
  2. The checkout, when the package sits inside one (a sibling .git or
     pyproject.toml). This covers `pip install -e .` and plain `python coach.py`,
     so an existing clone keeps using the files already beside it.
  3. ~/.garmin-workouts, for a real installation.

The directory is created on demand, so a fresh install works with no setup.
"""

from __future__ import annotations

import os
from pathlib import Path

FALLBACK = Path.home() / ".garmin-workouts"


def data_home() -> Path:
    override = os.getenv("GARMIN_WORKOUTS_HOME")
    if override:
        home = Path(override).expanduser()
    else:
        checkout = Path(__file__).resolve().parent.parent
        is_checkout = (checkout / ".git").exists() or (checkout / "pyproject.toml").exists()
        home = checkout if is_checkout else FALLBACK

    home.mkdir(parents=True, exist_ok=True)
    return home


def performance_path() -> Path:
    return data_home() / "performance.json"


def history_path() -> Path:
    return data_home() / "history.json"


def token_store() -> Path:
    return data_home() / ".garmin_session"
