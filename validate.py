#!/usr/bin/env python3
"""
Validate a workout file's exercises against Garmin's official FIT SDK exercise list.

Rather than trusting a hand-maintained lookup table (which is how a "Face Pull" /
"Rear Delt Fly" mix-up happened before), this reads the *_exercise_name enums
straight out of the installed garmin_fit_sdk package's source, so it stays correct
as Garmin's exercise list grows.

Usage:
    pip install garmin-fit-sdk
    python validate.py workouts/chest_shoulders_1.py

upload.py calls validate_workout() automatically before pushing anything to Garmin
Connect, so a bad exercise name/category pair is caught before upload rather than
after.
"""

from __future__ import annotations

import ast
import difflib
import importlib.util
import sys
from pathlib import Path


def load_workout(path: str) -> dict:
    spec = importlib.util.spec_from_file_location("workout", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.WORKOUT


def load_exercise_category_map() -> dict:
    """
    Returns {'bench_press_exercise_name': {0: 'barbell_bench_press', ...}, ...}
    parsed straight out of garmin_fit_sdk/profile.py via the AST, so it can't
    drift out of sync with Garmin's actual SDK the way a hand-copied table can.
    """
    try:
        import garmin_fit_sdk.profile as profile_mod
    except ImportError as exc:
        raise SystemExit(
            "garmin-fit-sdk is not installed. Run: pip install garmin-fit-sdk"
        ) from exc

    source = Path(profile_mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    # The "*_exercise_name" enums live nested inside Profile['types'], alongside
    # hundreds of unrelated FIT enums (file, sport, ...) — so rather than hunting
    # for one dict that holds *only* exercise enums, collect every key/value pair
    # anywhere in the file whose key ends in "_exercise_name" and whose value is
    # itself a literal {int: 'name', ...} dict.
    category_map: dict = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key_node, value_node in zip(node.keys, node.values):
            if (
                isinstance(key_node, ast.Constant)
                and isinstance(key_node.value, str)
                and key_node.value.endswith("_exercise_name")
                and isinstance(value_node, ast.Dict)
            ):
                category_map[key_node.value] = ast.literal_eval(value_node)

    if not category_map:
        raise RuntimeError(
            "Could not find any *_exercise_name maps inside garmin_fit_sdk/profile.py — "
            "the installed SDK's internal layout may have changed. Report this if you "
            "hit it; validation can't run until this is fixed."
        )
    return category_map


def validate_exercise(name: str, category: str, category_map: dict) -> tuple[bool, str]:
    key = f"{category.lower()}_exercise_name"
    if key not in category_map:
        all_categories = [k[: -len("_exercise_name")] for k in category_map]
        close = difflib.get_close_matches(category.lower(), all_categories, n=3)
        msg = f"'{category}' isn't a real Garmin exercise category."
        if close:
            msg += f" Did you mean: {', '.join(c.upper() for c in close)}?"
        return False, msg

    valid_names = set(category_map[key].values())
    target = name.lower()
    if target in valid_names:
        return True, ""

    suggestions = difflib.get_close_matches(target, valid_names, n=3, cutoff=0.4)
    msg = f"'{name}' is not a valid Garmin exercise under category '{category}'."
    if suggestions:
        msg += " Did you mean: " + ", ".join(s.upper() for s in suggestions) + "?"
    else:
        msg += " No close match found — double check the category too."
    return False, msg


def validate_workout(workout: dict) -> list[str]:
    """Returns a list of human-readable errors. Empty list = fully valid."""
    category_map = load_exercise_category_map()
    errors = []
    for ex in workout["exercises"]:
        ok, msg = validate_exercise(ex["name"], ex["category"], category_map)
        if not ok:
            errors.append(msg)
    return errors


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate.py workouts/<workout_file>.py")
        sys.exit(1)

    workout_path = Path(sys.argv[1])
    if not workout_path.exists():
        print(f"File not found: {workout_path}")
        sys.exit(1)

    workout = load_workout(str(workout_path))
    errors = validate_workout(workout)

    if errors:
        print(f"Validation FAILED for '{workout['name']}':")
        for e in errors:
            print(f"  x {e}")
        sys.exit(1)

    print(
        f"All {len(workout['exercises'])} exercises in '{workout['name']}' "
        "are valid Garmin FIT SDK entries."
    )


if __name__ == "__main__":
    main()
