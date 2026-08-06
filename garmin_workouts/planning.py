"""
Choosing which muscle groups to train next, from recovery and volume.
"""

from __future__ import annotations

from collections import defaultdict

from .constants import CATEGORY_PRIMARY_GROUP, GROUP_AFFINITY, MIN_RECOVERY_DAYS
from .store import days_since, load_store

def group_load(store: dict) -> dict:
    """Per muscle group: when it was last trained, how often, and how much."""
    stats = defaultdict(lambda: {"last": "", "sets": 0, "sessions": set()})
    for act in store.get("activities", {}).values():
        for s in act.get("sets", []):
            group = CATEGORY_PRIMARY_GROUP.get(s.get("category"))
            if not group:
                continue
            g = stats[group]
            g["sets"] += 1
            g["sessions"].add(act["date"])
            if act["date"] > g["last"]:
                g["last"] = act["date"]

    return {
        name: {
            "last": g["last"],
            "days_ago": days_since(g["last"]) if g["last"] else 999,
            "sets": g["sets"],
            "sessions": len(g["sessions"]),
        }
        for name, g in stats.items()
    }


def suggest_focus(store: dict | None = None) -> dict:
    """
    Recommend which muscle groups to train next.

    Two things decide it: recovery (a group trained inside MIN_RECOVERY_DAYS is
    off the table regardless of how neglected it is) and volume deficit (how
    little that group has had relative to the most-trained one). The pairing
    then comes from GROUP_AFFINITY so the session still makes sense as a
    workout rather than two unrelated halves.
    """
    store = store or load_store()
    loads = group_load(store)
    if not loads:
        return {"primary": None, "partner": None, "reason": "no data yet", "groups": {}}

    busiest = max(g["sets"] for g in loads.values()) or 1
    for name, g in loads.items():
        g["deficit"] = 1 - (g["sets"] / busiest)
        g["recovered"] = g["days_ago"] >= MIN_RECOVERY_DAYS
        # Deficit drives the choice; days rested breaks ties in favour of
        # whatever has been sitting longest.
        g["score"] = round(g["deficit"] + min(g["days_ago"], 14) / 28, 3)

    ready = {n: g for n, g in loads.items() if g["recovered"]}
    if not ready:
        return {
            "primary": None,
            "partner": None,
            "reason": "everything was trained in the last 48h — take a rest day",
            "groups": loads,
        }

    primary = max(ready, key=lambda n: ready[n]["score"])
    # Affinity says which groups pair sensibly; it must not decide which of them
    # to pick. Taking the first entry meant list order silently outranked the
    # data — core paired with back (85 sets) over shoulders (50) purely because
    # "back" was typed first. Rank the plausible partners the same way the
    # primary was ranked, and only fall back outside the affinity list if none
    # of them are recovered.
    partners = [p for p in GROUP_AFFINITY.get(primary, []) if p in ready and p != primary]
    if not partners:
        partners = [n for n in ready if n != primary]
    partner = max(partners, key=lambda n: ready[n]["score"], default=None)

    p = loads[primary]
    reason = (
        f"{primary} has {p['sets']} sets logged vs {busiest} for your most-trained "
        f"group, and was last hit {p['days_ago']} days ago"
    )

    # Chest/back/legs carry a session. A pairing of only small groups can't fill
    # 45-50 minutes without junk volume, so flag it rather than pretend it's fine.
    major = {"chest", "back", "legs"}
    caveat = None
    if not ({primary, partner} & major):
        # The best major group to wait for is the one most rested and most
        # under-trained — same score used everywhere else, not the one trained
        # most recently.
        candidates = {n: g for n, g in loads.items() if n in major}
        best = max(candidates, key=lambda n: candidates[n]["score"], default=None)
        if best:
            caveat = (
                f"both are small groups — fine as a short accessory session, or "
                f"wait a day and pair {primary} with {best} "
                f"(rested {candidates[best]['days_ago']}d)"
            )

    return {
        "primary": primary,
        "partner": partner,
        "reason": reason,
        "caveat": caveat,
        "groups": loads,
    }
