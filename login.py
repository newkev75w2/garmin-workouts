#!/usr/bin/env python3
"""
One-time interactive Garmin Connect login.

    python login.py

Caches a session to .garmin_session/ so nothing else ever needs credentials.
Credentials are prompted for at run time and never stored — only the resulting
session token is written to disk, and that directory is gitignored.

The auth flow itself lives in garmin_workouts/client.py, which adapts to
whichever garminconnect version is installed.
"""

from __future__ import annotations

import getpass
import os
import sys

import garminconnect

from garmin_workouts.client import (
    TOKENSTORE,
    legacy_login,
    modern_login,
    supports_prompt_mfa,
)


def main() -> None:
    version = getattr(garminconnect, "__version__", "unknown")
    mode = "modern" if supports_prompt_mfa() else "legacy (0.2.x / garth)"
    print(f"garminconnect version: {version}  ->  using {mode} auth flow")
    print(f"python: {sys.version.split()[0]}\n")

    email = os.getenv("GARMIN_EMAIL") or input("Garmin email: ")
    password = os.getenv("GARMIN_PASSWORD") or getpass.getpass("Garmin password: ")

    client = modern_login(email, password) if supports_prompt_mfa() else legacy_login(email, password)

    print(f"\nLogged in as: {client.get_full_name()}")
    print(f"Session cached at {TOKENSTORE} — upload.py will reuse it from now on.")


if __name__ == "__main__":
    main()
