#!/usr/bin/env python3
"""
Build a browsable page showing a workout with demonstration images.

    python demos_refresh.py            # (first run) cache the wger index
    python preview.py workouts/back_biceps_1.py
    python preview.py workouts/back_biceps_1.py --no-open

Images are loaded from wger.de when the page is viewed — nothing is copied into
this repo. Each card states how confident the name match is, because Garmin's
exercise names and wger's do not line up cleanly; see garmin_workouts/demos.py.
Treat anything not marked "verified" as a hint, not an instruction.
"""

from __future__ import annotations

import argparse
import html
import subprocess
import sys
from pathlib import Path

from garmin_workouts import demos, workout as wk

OUT_DIR = Path(__file__).resolve().parent / "previews"

BADGE = {
    "verified": ("verified", "#0f7b3f", "Checked by hand against the wger entry."),
    "likely": ("likely match", "#8a6100",
               "Names and muscle group agree — glance at it before trusting it."),
    "uncertain": ("unverified guess", "#a33",
                  "May be the wrong movement. Use the search link to confirm."),
    "none": ("no image", "#555", "Nothing plausible in the library."),
}

PAGE = """<!doctype html>
<meta charset="utf-8">
<title>{title}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font: 16px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         margin: 0 auto; padding: 2rem 1.25rem 4rem; max-width: 60rem; }}
  h1 {{ margin: 0 0 .25rem; font-size: 1.5rem; }}
  .sub {{ opacity: .7; margin: 0 0 1.5rem; }}
  .warn {{ border-left: 3px solid #a33; padding: .75rem 1rem; margin: 0 0 2rem;
          background: rgba(170,51,51,.07); font-size: .93rem; }}
  .grid {{ display: grid; gap: 1.25rem;
          grid-template-columns: repeat(auto-fill, minmax(15rem, 1fr)); }}
  .card {{ border: 1px solid rgba(128,128,128,.3); border-radius: 10px;
          overflow: hidden; display: flex; flex-direction: column; }}
  .thumb {{ background: rgba(128,128,128,.09); aspect-ratio: 4/3;
           display: flex; align-items: center; justify-content: center; }}
  .thumb img {{ width: 100%; height: 100%; object-fit: contain; }}
  .thumb .none {{ opacity: .45; font-size: .85rem; }}
  .body {{ padding: .8rem .9rem 1rem; display: flex; flex-direction: column; gap: .4rem; }}
  .name {{ font-weight: 600; }}
  .prescr {{ font-size: .88rem; opacity: .75; }}
  .badge {{ align-self: flex-start; font-size: .72rem; letter-spacing: .03em;
           text-transform: uppercase; color: #fff; padding: .15rem .45rem;
           border-radius: 4px; }}
  .why {{ font-size: .8rem; opacity: .7; }}
  .links {{ font-size: .82rem; display: flex; gap: .75rem; flex-wrap: wrap; }}
  footer {{ margin-top: 3rem; font-size: .82rem; opacity: .7; }}
  a {{ color: inherit; }}
</style>
<h1>{title}</h1>
<p class="sub">{subtitle}</p>
{warning}
<div class="grid">
{cards}
</div>
<footer>
  {attribution}. Images are loaded from wger.de and are not stored in this repo.
  Match confidence is computed by <code>garmin_workouts/demos.py</code>.
</footer>
"""

CARD = """  <div class="card">
    <div class="thumb">{thumb}</div>
    <div class="body">
      <div class="name">{name}</div>
      <div class="prescr">{prescription}</div>
      <span class="badge" style="background:{colour}">{label}</span>
      <div class="why">{why}{matched}</div>
      <div class="links">{links}</div>
    </div>
  </div>"""


def card_for(exercise: dict, index: list) -> str:
    name = exercise["name"]
    result = demos.match(name, exercise.get("category"), index)
    label, colour, why = BADGE[result["confidence"]]

    if result["image"]:
        thumb = f'<img src="{html.escape(result["image"])}" alt="{html.escape(name)}" loading="lazy">'
    else:
        thumb = '<span class="none">no demonstration found</span>'

    reps = exercise.get("reps") or f"{exercise.get('seconds')}s"
    prescription = f"{exercise['sets']}x{reps} · {exercise['rest_seconds']}s rest"

    matched = ""
    if result["match_name"] and result["confidence"] != "verified":
        matched = f' Showing “{html.escape(result["match_name"])}”.'

    links = [f'<a href="{html.escape(result["search"])}" target="_blank">search demos</a>']
    if result["page"]:
        links.insert(0, f'<a href="{html.escape(result["page"])}" target="_blank">wger entry</a>')

    return CARD.format(
        thumb=thumb,
        name=html.escape(name.replace("_", " ").title()),
        prescription=html.escape(prescription),
        colour=colour,
        label=label,
        why=why,
        matched=matched,
        links=" ".join(links),
    )


def build(workout: dict) -> str:
    index = demos.load_index()
    cards = "\n".join(card_for(ex, index) for ex in workout["exercises"])

    counts = {}
    for ex in workout["exercises"]:
        c = demos.match(ex["name"], ex.get("category"), index)["confidence"]
        counts[c] = counts.get(c, 0) + 1
    unsure = counts.get("uncertain", 0) + counts.get("none", 0)

    warning = ""
    if unsure:
        warning = (
            f'<p class="warn"><strong>{unsure} of {len(workout["exercises"])} '
            "exercises could not be matched confidently.</strong> Garmin and wger "
            "use different exercise names, so anything below marked "
            "<em>unverified guess</em> may show the wrong movement — check it "
            "against the search link before copying the form.</p>"
        )

    return PAGE.format(
        title=html.escape(workout["name"]),
        subtitle=html.escape(workout.get("description", "")),
        warning=warning,
        cards=cards,
        attribution=html.escape(demos.ATTRIBUTION),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render a workout with demonstration images as a local page."
    )
    parser.add_argument("workout_file", help="e.g. workouts/back_biceps_1.py")
    parser.add_argument("--no-open", action="store_true",
                        help="write the page but do not open a browser")
    args = parser.parse_args()

    path = Path(args.workout_file)
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    if not demos.load_index():
        print(
            "No exercise index cached yet. Run this once first:\n"
            "    python -c \"from garmin_workouts import demos; demos.refresh_index()\""
        )
        sys.exit(1)

    w = wk.load_workout(str(path))
    OUT_DIR.mkdir(exist_ok=True)
    out = OUT_DIR / f"{path.stem}.html"
    out.write_text(build(w), encoding="utf-8")

    print(f"Wrote {out}")
    if not args.no_open:
        subprocess.run(["open", str(out)], check=False)


if __name__ == "__main__":
    main()
