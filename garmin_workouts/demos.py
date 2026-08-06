"""
Matching Garmin exercise names to demonstration images from wger.de.

Why this is not a simple lookup
-------------------------------
Garmin uses the FIT SDK's fixed enum (REVERSE_GRIP_BARBELL_ROW); wger uses
community-entered names ("Reverse Grip Barbell Curls"). They are different
taxonomies, and string similarity alone bridges them badly — measured against a
real 58-exercise list it matched ALTERNATING_DUMBBELL_ROW to a hammer curl and
BARBELL_BICEPS_CURL to a wrist curl. Constraining by muscle category removes
some of those but not all (a wrist curl and a biceps curl are both "Arms") while
also rejecting correct pairs.

So every match carries a confidence, and the UI is expected to show it:

  verified   hand-checked pair in CURATED below — trust it
  likely     names agree closely and the muscle group agrees
  uncertain  a candidate exists but could be the wrong movement
  none       nothing plausible; link out to a search instead

Never present an `uncertain` match as though it were the exercise. Showing the
wrong movement is worse than showing nothing, because it gets copied.

Licensing
---------
wger's images are CC BY-SA 3.0 with per-image author metadata, which this module
carries through so the UI can attribute them. Images are referenced by URL and
loaded from wger at view time — nothing is copied into this repo, which keeps
the share-alike obligation off the project.

The other obvious source, yuhonas/free-exercise-db, is deliberately NOT used:
its JSON is public domain but the provenance of its images is unanswered (see
its issues #2 and #13), so redistributing them would be a copyright gamble.
"""

from __future__ import annotations

import difflib
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = ROOT / "wger_index.json"

API = "https://wger.de/api/v2/exerciseinfo/?format=json&limit=100"
ATTRIBUTION = "Exercise images from wger.de, licensed CC BY-SA 3.0"
SEARCH_URL = "https://www.google.com/search?tbm=vid&q={}+exercise+form"

STRONG_MATCH = 0.88   # names this close, with the muscle group agreeing, are "likely"
WEAK_MATCH = 0.72     # below this there is no candidate worth showing at all

# Garmin category -> wger categories that could plausibly hold the same movement.
CATEGORY_GATE = {
    "ROW": {"Back"}, "PULL_UP": {"Back"}, "SHRUG": {"Back", "Shoulders"},
    "BENCH_PRESS": {"Chest"}, "FLYE": {"Chest"}, "PUSH_UP": {"Chest", "Arms"},
    "SHOULDER_PRESS": {"Shoulders"}, "LATERAL_RAISE": {"Shoulders"},
    "CURL": {"Arms"}, "TRICEPS_EXTENSION": {"Arms"},
    "SQUAT": {"Legs"}, "DEADLIFT": {"Legs", "Back"}, "LUNGE": {"Legs"},
    "LEG_CURL": {"Legs"}, "CALF_RAISE": {"Calves", "Legs"}, "HIP_RAISE": {"Legs"},
    "CORE": {"Abs"}, "CRUNCH": {"Abs"}, "PLANK": {"Abs"}, "LEG_RAISE": {"Abs"},
}

# Pairs checked by hand against the wger entry. Additions are welcome but should
# only be made after actually looking at the image, not from name similarity.
CURATED = {
    "CABLE_CROSSOVER": "Cable Cross-over",
    "SEATED_CABLE_ROW": "Seated Cable Row",
    "LEG_PRESS": "Leg Press",
    "LEG_CURL": "Leg Curl",
    "TRICEPS_PRESSDOWN": "Triceps Pushdown",
    "OVERHEAD_BARBELL_PRESS": "Overhead Barbell Press",
    "CLOSE_GRIP_LAT_PULLDOWN": "Close-grip Lat Pull Down",
    "STANDING_CALF_RAISE": "Standing Calf Raises",
    "BARBELL_BENCH_PRESS": "Bench Press",
    # wger inverts and pluralises these, so they only surfaced once word-overlap
    # matching was added; the pairings themselves are unambiguous.
    "BARBELL_SHRUG": "Shrugs, Barbells",
    "DUMBBELL_SHRUG": "Shrugs, Dumbbells",
    "BARBELL_BICEPS_CURL": "Biceps Curls With Barbell",
    "CABLE_BICEPS_CURL": "Biceps Curl With Cable",
    "DUMBBELL_HAMMER_CURL": "Hammer Curls",
}

# Candidates observed to be confidently wrong. Blocking them by name stops the
# fuzzy matcher re-proposing the same mistake as the index changes upstream.
BLOCKED = {
    "BARBELL_BICEPS_CURL": {"Barbell Wrist Curl"},
    "DUMBBELL_BENCH_PRESS": {"Dumbbell Hex Press"},
    "ALTERNATING_DUMBBELL_ROW": {"Alternating dumbbell hammer curl"},
    "DUMBBELL_HAMMER_CURL": {"Alternating dumbbell hammer curl"},
    "REVERSE_GRIP_BARBELL_ROW": {"Reverse Grip Barbell Curls"},
    "BICEPS_PUSH_UP": {"Clap Push-UP"},
    "BARBELL_DEADLIFT": {"Dumbbell sumo deadlift"},
}


def normalise(name: str) -> str:
    """Garmin enum or wger title -> comparable lowercase words."""
    text = name.replace("_", " ").lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return " ".join(text.split()).lstrip("0123456789 ").strip()


# Words that say nothing about which movement it is, only how it is set up.
NOISE_WORDS = {"the", "with", "a", "on", "of", "and", "using", "machine", "exercise"}


def tokens(text: str) -> frozenset:
    """
    Word set with plurals folded together.

    wger writes names inverted and pluralised ("Shrugs, Barbells") where Garmin
    writes BARBELL_SHRUG. Sequence similarity scores that pair very low despite
    them being the same movement, so word overlap is compared as well.
    """
    words = set()
    for word in normalise(text).split():
        if word in NOISE_WORDS:
            continue
        words.add(word[:-1] if len(word) > 3 and word.endswith("s") else word)
    return frozenset(words)


def similarity(query: str, candidate: str) -> float:
    """Best of sequence similarity and word overlap, so neither alone decides."""
    sequence = difflib.SequenceMatcher(None, query, candidate).ratio()
    a, b = tokens(query), tokens(candidate)
    if not a or not b:
        return sequence
    overlap = len(a & b) / len(a | b)
    return max(sequence, overlap)


def refresh_index(path: Path = INDEX_PATH) -> int:
    """Pull wger's exercise metadata (names, image URLs, licence) and cache it."""
    entries, url = [], API
    while url:
        request = urllib.request.Request(
            url, headers={"User-Agent": "garmin-workouts (personal use)"}
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            page = json.load(response)
        entries.extend(page["results"])
        url = page.get("next")

    index = []
    for entry in entries:
        images = entry.get("images") or []
        if not images:
            continue
        main = next((i for i in images if i.get("is_main")), images[0])
        category = (entry.get("category") or {}).get("name")
        for translation in entry.get("translations", []):
            if translation.get("language") == 2 and translation.get("name"):
                index.append(
                    {
                        "name": translation["name"],
                        "key": normalise(translation["name"]),
                        "category": category,
                        "image": main.get("image"),
                        "author": main.get("license_author") or "",
                        "licence": main.get("license_title") or "CC BY-SA 3.0",
                        "page": f"https://wger.de/en/exercise/{entry['id']}/view/",
                    }
                )

    path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    return len(index)


def load_index(path: Path = INDEX_PATH) -> list:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def search_link(exercise: str) -> str:
    return SEARCH_URL.format(urllib.parse.quote_plus(normalise(exercise)))


def match(exercise: str, category: str | None = None, index: list | None = None) -> dict:
    """
    Best demonstration image for one Garmin exercise, with a confidence.

    Returns a dict that always has `confidence` and `search` set, so callers can
    render something useful even when there is no image.
    """
    index = load_index() if index is None else index
    result = {
        "exercise": exercise,
        "confidence": "none",
        "match_name": None,
        "image": None,
        "page": None,
        "author": "",
        "licence": "",
        "search": search_link(exercise),
    }
    if not index:
        return result

    blocked = BLOCKED.get(exercise, set())
    candidates = [e for e in index if e["name"] not in blocked]

    def fill(entry, confidence):
        result.update(
            {
                "confidence": confidence,
                "match_name": entry["name"],
                "image": entry["image"],
                "page": entry["page"],
                "author": entry["author"],
                "licence": entry["licence"],
            }
        )
        return result

    if exercise in CURATED:
        wanted = CURATED[exercise]
        entry = next((e for e in candidates if e["name"] == wanted), None)
        if entry:
            return fill(entry, "verified")

    allowed = CATEGORY_GATE.get(category or "", set())
    in_group = [e for e in candidates if e["category"] in allowed] if allowed else []

    query = normalise(exercise)
    exact = next((e for e in in_group if e["key"] == query), None)
    if exact:
        return fill(exact, "likely")

    def best(pool):
        if not pool:
            return None, 0.0
        scored = max(pool, key=lambda e: similarity(query, e["key"]))
        return scored, similarity(query, scored["key"])

    entry, score = best(in_group)
    if entry and score >= STRONG_MATCH:
        return fill(entry, "likely")

    # Fall back to the whole index — anything found here is a guess, and the
    # muscle group may not even agree, so it is never better than "uncertain".
    loose, loose_score = best(candidates)
    if loose and loose_score >= WEAK_MATCH:
        return fill(loose, "uncertain")
    if entry and score >= WEAK_MATCH:
        return fill(entry, "uncertain")

    return result
