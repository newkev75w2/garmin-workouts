"""
Which local workout files have actually been used, and which are drafts.

Testing generates a lot of files. Most are never uploaded, and numbering every
one leaves a directory where nothing indicates which sessions were real. A file
that was never uploaded is a draft and can be rewritten in place.

How a file is known to be used, cheapest first:

  1. An UPLOADED stamp written into the file at upload time. Self-contained,
     works offline, and cannot drift from the file it describes.
  2. history.json, for files uploaded before stamping existed.
  3. Garmin Connect itself, only when asked. This is the backstop for files
     this tool never saw uploaded — a real log had "Chest & Shoulders 1" saved
     in Garmin with no local record of it at all.

Getting this wrong means overwriting a real session, so when Garmin cannot be
reached the answer for an unstamped file is "unknown" rather than "draft". The
safe direction is to leave it alone.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path

from . import history, workout as wk
from .paths import data_home

WORKOUTS_DIR = data_home() / "workouts"

# Watches cap how many workouts they will hold, and the cap is the device's, not
# the account's — everything synced to the watch counts, however it got there.
# fenix 6 and 7 are documented at 25; the fenix 8 figure is not something I could
# confirm, so the default stays at the conservative known number. Override with
# GARMIN_WORKOUT_LIMIT once the watch tells you the real one.
WATCH_LIMIT = int(os.getenv("GARMIN_WORKOUT_LIMIT", "25"))
CROWDED = 0.8  # warn once this fraction of the limit is used
STAMP = re.compile(r'^UPLOADED\s*=\s*["\']([^"\']+)["\']', re.M)


def stamp_of(path: Path) -> str | None:
    """The upload timestamp written into a workout file, if it has one."""
    try:
        found = STAMP.search(path.read_text(encoding="utf-8"))
    except OSError:
        return None
    return found.group(1) if found else None


def mark_uploaded(path: Path, when: str | None = None) -> None:
    """
    Record on the file itself that it reached Garmin.

    Written as a module-level constant rather than a comment so it survives
    reformatting and can be read without parsing prose.
    """
    path = Path(path)
    when = when or datetime.now(timezone.utc).isoformat(timespec="seconds")
    text = path.read_text(encoding="utf-8")

    if STAMP.search(text):
        text = STAMP.sub(f'UPLOADED = "{when}"', text, count=1)
    else:
        marker = f'\n# Uploaded to Garmin Connect — this file is no longer a draft.\nUPLOADED = "{when}"\n'
        text = text.rstrip() + "\n" + marker
    path.write_text(text, encoding="utf-8")


def remote_names(client=None) -> set | None:
    """
    Workout names saved in Garmin Connect, or None if it could not be asked.

    None and empty mean different things: empty is "Garmin has none", None is
    "we don't know", and only the first is safe to act on.
    """
    from .client import get_client

    try:
        client = client or get_client()
        saved = client.connectapi("/workout-service/workouts?start=0&limit=100")
    except Exception:
        return None
    if not isinstance(saved, list):
        return None
    return {w.get("workoutName", "").strip() for w in saved if w.get("workoutName")}


def local_workouts(check_remote: bool = False, client=None) -> list:
    """
    Every workout file with whether it was uploaded.

    Garmin is only consulted when asked, since the stamp answers it for anything
    uploaded through this tool.
    """
    logged = {Path(e["file"]).name for e in history.load()}
    remote = None
    entries = []

    for path in sorted(WORKOUTS_DIR.glob("*.py")):
        try:
            name = wk.load_workout(str(path))["name"].strip()
        except Exception:
            name = ""

        stamped = stamp_of(path)
        in_history = path.name in logged

        if stamped or in_history:
            status, in_garmin = "uploaded", False
        else:
            if check_remote and remote is None:
                remote = remote_names(client)
            in_garmin = bool(remote and name in remote)
            if in_garmin:
                status = "uploaded"
            elif check_remote and remote is None:
                status = "unknown"  # asked, but Garmin was unreachable
            else:
                status = "draft"

        entries.append(
            {
                "path": path,
                "file": path.name,
                "name": name,
                "status": status,
                "stamped": stamped,
                "in_history": in_history,
                "in_garmin": in_garmin,
            }
        )
    return entries


def slug_of(filename: str) -> str:
    """chest_shoulders_2.py -> chest_shoulders"""
    return Path(filename).stem.rsplit("_", 1)[0]


def _number(filename: str) -> int:
    tail = Path(filename).stem.rsplit("_", 1)[-1]
    return int(tail) if tail.isdigit() else 0


def target_path(slug: str, entries: list | None = None) -> tuple:
    """
    Where the next workout for `slug` should be written.

    Returns (path, reused). The highest-numbered file for this slug is reused if
    it is still a draft, so drafts do not pile up. Anything uploaded — or
    anything whose status could not be established — is left alone and a fresh
    number is taken.
    """
    entries = local_workouts() if entries is None else entries
    mine = [e for e in entries if slug_of(e["file"]) == slug]

    if mine:
        latest = max(mine, key=lambda e: _number(e["file"]))
        if latest["status"] == "draft":
            return latest["path"], True

    used = {_number(e["file"]) for e in mine}
    number = 1
    while number in used:
        number += 1
    return WORKOUTS_DIR / f"{slug}_{number}.py", False


def backfill(client=None) -> int:
    """
    Stamp files that were uploaded before stamping existed.

    One-off reconciliation against history.json and Garmin, so the fast path
    covers everything from then on. Returns how many files were stamped.
    """
    entries = local_workouts(check_remote=True, client=client)
    stamped = 0
    for entry in entries:
        if entry["status"] == "uploaded" and not entry["stamped"]:
            mark_uploaded(entry["path"])
            stamped += 1
    return stamped


def remote_workouts(client=None) -> list:
    """
    Workouts saved in Garmin Connect, with whether each was ever completed.

    "Completed" is judged by matching the workout name against activity history.
    It is a name match, so a renamed workout reads as unused — which is why
    nothing here deletes anything on its own.
    """
    from .client import get_client

    try:
        client = client or get_client()
        saved = client.connectapi("/workout-service/workouts?start=0&limit=100")
        activities = {
            (a.get("activityName") or "").strip()
            for a in client.get_activities(0, 200)
        }
    except Exception:
        return []
    if not isinstance(saved, list):
        return []

    seen: dict = {}
    out = []
    for w in saved:
        name = (w.get("workoutName") or "").strip()
        entry = {
            "id": w.get("workoutId"),
            "name": name,
            "updated": (w.get("updateDate") or "")[:10],
            "completed": name in activities,
            "duplicate": name in seen,
        }
        seen[name] = True
        out.append(entry)
    return out


def crowding(entries: list | None = None, limit: int | None = None) -> dict:
    """
    How close the watch is to its workout cap, and what could go.

    Candidates are ordered by how safe they are to lose: exact duplicates first,
    then never-completed workouts, then the oldest. Nothing is deleted here —
    removing a workout is irreversible and belongs to the athlete.
    """
    entries = remote_workouts() if entries is None else entries
    limit = limit or WATCH_LIMIT

    duplicates = [e for e in entries if e["duplicate"]]
    unused = [e for e in entries if not e["completed"] and not e["duplicate"]]
    rest = sorted(
        (e for e in entries if not e["duplicate"] and e["completed"]),
        key=lambda e: e["updated"],
    )

    return {
        "count": len(entries),
        "limit": limit,
        "crowded": len(entries) >= limit * CROWDED,
        "over": len(entries) > limit,
        "candidates": duplicates + unused + rest,
        "duplicates": duplicates,
        "unused": unused,
    }


def delete_workout(workout_id: int, client=None) -> bool:
    """
    Remove one workout from Garmin Connect. Irreversible.

    Callers must have confirmed with the athlete first — there is no undo, and
    the evidence this tool has for "unused" is a name match, which is not proof.
    """
    from .client import get_client

    try:
        client = client or get_client()
        client.connectapi(f"/workout-service/workout/{workout_id}", method="DELETE")
        return True
    except Exception:
        return False


def cleanup(keep_free: int = 5, confirm=None, client=None) -> dict:
    """
    Free up slots by removing the safest workouts, once confirmed.

    `confirm` is called with the list about to be removed and must return True;
    without it nothing is deleted. Only ever removes as many as are needed to
    leave `keep_free` slots, starting with exact duplicates — deleting more than
    necessary is not tidying, it is losing sessions.
    """
    entries = remote_workouts(client)
    state = crowding(entries)

    needed = state["count"] - (state["limit"] - keep_free)
    if needed <= 0:
        return {"needed": 0, "deleted": [], "failed": [], "state": state}

    # Only ever touch things with a positive reason to go.
    safe = state["duplicates"] + state["unused"]
    doomed = safe[:needed]

    if not doomed:
        return {"needed": needed, "deleted": [], "failed": [], "state": state,
                "note": "nothing safe to remove — every workout has been used"}

    if confirm is None or not confirm(doomed):
        return {"needed": needed, "deleted": [], "failed": [], "state": state,
                "note": "cancelled"}

    deleted, failed = [], []
    for entry in doomed:
        (deleted if delete_workout(entry["id"], client) else failed).append(entry)
    return {"needed": needed, "deleted": deleted, "failed": failed, "state": state}
