#!/usr/bin/env python3
"""
One-time interactive Garmin Connect login.

    python login.py

Caches a session to .garmin_session/ so upload.py never needs credentials again.

This adapts to whichever garminconnect version you have installed rather than
assuming one API:
  - Modern garminconnect (>=0.3): Garmin(email, password, prompt_mfa=...) then
    client.login(tokenstore) — handles MFA itself.
  - Legacy garminconnect 0.2.x (built on the now-deprecated `garth`): drives
    garth's login/resume_login MFA flow directly, then dumps the session.

Note on the legacy path: garth's maintainer has stated Garmin changed their auth
flow and **new logins through garth no longer work** — only previously-saved
sessions keep working until they expire. If you're on 0.2.x and login fails at
the network/auth level (not with a TypeError), that's why, and the fix is to
upgrade garminconnect on a Python version it supports (3.10+).
"""

from __future__ import annotations

import getpass
import inspect
import os
import sys
from pathlib import Path

import garminconnect
from garminconnect import Garmin

TOKENSTORE = str(Path(__file__).parent / ".garmin_session")


def supports_prompt_mfa() -> bool:
    return "prompt_mfa" in inspect.signature(Garmin.__init__).parameters


def modern_login(email: str, password: str):
    client = Garmin(email, password, prompt_mfa=lambda: input("MFA code: "))
    client.login(TOKENSTORE)
    return client


def legacy_login(email: str, password: str):
    """garminconnect 0.2.x — drive garth's MFA flow, then persist the session."""
    client = Garmin(email, password)
    garth_client = client.garth

    login_sig = inspect.signature(garth_client.login)
    supports_mfa_return = (
        "return_on_mfa" in login_sig.parameters
        or any(p.kind == p.VAR_KEYWORD for p in login_sig.parameters.values())
    )

    if supports_mfa_return and hasattr(garth_client, "resume_login"):
        result = garth_client.login(email, password, return_on_mfa=True)
        if isinstance(result, tuple) and result[0] == "needs_mfa":
            mfa_code = input("MFA code: ")
            garth_client.resume_login(result[1], mfa_code)
    else:
        garth_client.login(email, password)

    Path(TOKENSTORE).mkdir(parents=True, exist_ok=True)
    garth_client.dump(TOKENSTORE)

    client.display_name = garth_client.profile["displayName"]
    client.full_name = garth_client.profile["fullName"]
    return client


def main():
    version = getattr(garminconnect, "__version__", "unknown")
    mode = "modern" if supports_prompt_mfa() else "legacy (0.2.x / garth)"
    print(f"garminconnect version: {version}  ->  using {mode} auth flow")
    print(f"python: {sys.version.split()[0]}\n")

    email = os.getenv("GARMIN_EMAIL") or input("Garmin email: ")
    password = os.getenv("GARMIN_PASSWORD") or getpass.getpass("Garmin password: ")

    if supports_prompt_mfa():
        client = modern_login(email, password)
    else:
        client = legacy_login(email, password)

    print(f"\nLogged in as: {client.get_full_name()}")
    print(f"Session cached at {TOKENSTORE} — upload.py will reuse it from now on.")


if __name__ == "__main__":
    main()
