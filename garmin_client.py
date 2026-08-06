"""
Shared Garmin Connect client setup.

Both upload.py (push workouts) and sync.py (pull completed sessions) need an
authenticated client, so the cached-session handling lives here rather than
being duplicated in each script.
"""

from __future__ import annotations

import inspect
import os
import sys
from pathlib import Path

from garminconnect import Garmin

TOKENSTORE = str(Path(__file__).parent / ".garmin_session")


def _make_client(email=None, password=None) -> Garmin:
    """
    Build a Garmin client, passing prompt_mfa only if the installed
    garminconnect version actually supports it (0.2.x does not).
    """
    if "prompt_mfa" in inspect.signature(Garmin.__init__).parameters:
        return Garmin(email, password, prompt_mfa=lambda: input("MFA code: "))
    return Garmin(email, password)


def get_client() -> Garmin:
    """
    Reuses the cached session written by login.py. Never prompts when running
    headlessly — it just tells you to run `python login.py` first.
    """
    client = _make_client(os.getenv("GARMIN_EMAIL"), os.getenv("GARMIN_PASSWORD"))
    try:
        client.login(TOKENSTORE)
        return client
    except Exception as exc:
        print(f"Could not use cached session at {TOKENSTORE}: {exc}")

    print(
        "\nNo valid cached Garmin session found.\n"
        "Run `python login.py` once yourself, then re-run this."
    )
    sys.exit(1)
