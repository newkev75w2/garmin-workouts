#!/usr/bin/env python3
"""
Build the installable .skill package from SKILL.md.

    python package_skill.py

Writes dist/garmin-workout.skill, which is what gets double-clicked and saved
into Claude Desktop. The version is read from the package so the built skill
always states which build it is — see "Verifying which build is loaded" in
SKILL.md, which exists because a running conversation keeps the skill text it
started with and there is otherwise no way to tell.
"""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

from garmin_workouts import __version__

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "SKILL.md"
OUT_DIR = ROOT / "dist"
OUT = OUT_DIR / "garmin-workout.skill"


def split_frontmatter(text: str) -> tuple[list, list]:
    lines = text.split("\n")
    index, front = 1, []
    while index < len(lines):
        if lines[index].strip() == "---":
            index += 1
            break
        front.append(lines[index])
        index += 1
    return front, lines[index:]


def description_from(front: list) -> str:
    """Flatten the folded YAML description into the single line the manifest wants."""
    parts, reading = [], False
    for line in front:
        if line.startswith("description:"):
            value = line.split(":", 1)[1].strip()
            if value and value != ">":
                parts.append(value)
            reading = True
        elif reading and line.startswith("  "):
            parts.append(line.strip())
        elif reading:
            break
    return " ".join(parts)


def stamp_version(text: str) -> str:
    """Keep the version line in SKILL.md in step with the package version."""
    marker = f"**Skill build: v{__version__}**"
    pattern = r"\*\*Skill build: v[0-9]+\.[0-9]+\.[0-9]+\*\*"
    if re.search(pattern, text):
        return re.sub(pattern, marker, text)
    return text.replace(
        "# Garmin Strength Workout Builder\n",
        f"# Garmin Strength Workout Builder\n\n{marker}\n",
        1,
    )


def build() -> Path:
    text = stamp_version(SOURCE.read_text(encoding="utf-8"))
    SOURCE.write_text(text, encoding="utf-8")

    front, body = split_frontmatter(text)
    manifest = {
        "schemaVersion": "1.0",
        "name": "garmin-workout",
        "description": description_from(front),
        "instructions": "\n".join(body).strip(),
    }

    OUT_DIR.mkdir(exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, indent=2))
        archive.writestr("SKILL.md", text)
    return OUT


def main() -> None:
    out = build()
    size = out.stat().st_size
    print(f"Built {out.relative_to(ROOT)}  (v{__version__}, {size:,} bytes)")
    print("Double-click it, choose 'Save skill', then restart Claude Desktop.")


if __name__ == "__main__":
    main()
