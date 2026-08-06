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

from .paths import token_store

from garminconnect import Garmin

TOKENSTORE = str(token_store())


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


# --- interactive first-time login -------------------------------------------
#
# Two auth paths because the library changed under us. garminconnect >=0.3
# handles MFA itself via prompt_mfa; 0.2.x is built on the older garth flow and
# has to be driven by hand. Which one is available is detected rather than
# assumed, so this keeps working across either version.


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


def interactive_login():
    """
    Prompt for credentials once and cache the resulting session.

    Credentials are read at run time and never stored — only the session token
    is written, into a gitignored directory.
    """
    import getpass
    import os
    import sys

    import garminconnect

    version = getattr(garminconnect, "__version__", "unknown")
    mode = "modern" if supports_prompt_mfa() else "legacy (0.2.x / garth)"
    print(f"garminconnect version: {version}  ->  using {mode} auth flow")
    print(f"python: {sys.version.split()[0]}\n")

    email = os.getenv("GARMIN_EMAIL") or input("Garmin email: ")
    password = os.getenv("GARMIN_PASSWORD") or getpass.getpass("Garmin password: ")

    client = modern_login(email, password) if supports_prompt_mfa() else legacy_login(email, password)

    print(f"\nLogged in as: {client.get_full_name()}")
    print(f"Session cached at {TOKENSTORE} — nothing else will prompt.")
    return client
