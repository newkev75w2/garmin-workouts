"""
The `garmin` command.

    garmin suggest --as-of 2026-08-10 --planned core shoulders
    garmin coach --muscles chest shoulders
    garmin sync
    garmin validate workouts/chest_shoulders_1.py
    garmin upload workouts/chest_shoulders_1.py --dry-run
    garmin login

The root-level scripts (coach.py, sync.py, ...) still work and route here, so
existing commands and anything written against them keep running.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

from . import judging, report


def _add_planning_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--as-of", metavar="YYYY-MM-DD", dest="as_of",
                        help="plan for a future day, e.g. --as-of 2026-08-10")
    parser.add_argument("--planned", nargs="+", metavar="GROUP",
                        help="groups you intend to train before then but haven't yet")
    parser.add_argument("--planned-date", metavar="YYYY-MM-DD", dest="planned_date",
                        help="when that planned session happens (defaults to tomorrow)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="garmin",
        description="Build Garmin strength workouts from your own training history.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    suggest = sub.add_parser("suggest", help="which muscle groups to train next, and why")
    _add_planning_flags(suggest)

    coach = sub.add_parser("coach", help="per-exercise verdicts and next steps")
    coach.add_argument("--brief", action="store_true",
                       help="one line per exercise (what the skill reads)")
    coach.add_argument("--muscles", nargs="+", metavar="GROUP",
                       help="limit to these muscle groups")
    coach.add_argument("--stale", action="store_true",
                       help="include exercises untrained for 21+ days")
    coach.add_argument("--prescribed", nargs="?", const="", metavar="EXERCISE",
                       help="show what was programmed over time instead of performed")

    plan_cmd = sub.add_parser("plan", help="a week of strength and running together")
    plan_cmd.add_argument("--goal", default="vo2max",
                          choices=["vo2max", "endurance", "strength", "balanced"],
                          help="what the week is built around (default vo2max)")
    plan_cmd.add_argument("--weekdays", metavar="mon-fri",
                          help="days you can train, e.g. mon-fri or mon,wed,fri")
    plan_cmd.add_argument("--no-sync", action="store_true",
                          help="plan from local data without refreshing first")
    plan_cmd.add_argument("--strength", type=int, metavar="N",
                          help="strength sessions this week (default: recommended)")
    plan_cmd.add_argument("--runs", type=int, metavar="N",
                          help="runs this week (default: recommended)")
    plan_cmd.add_argument("--start", metavar="YYYY-MM-DD|today|tomorrow",
                          help="first day (default: the coming Monday)")

    dist_cmd = sub.add_parser("distance", help="how far a run of N minutes should be")
    dist_cmd.add_argument("minutes", type=float)
    dist_cmd.add_argument("--pace", type=float, metavar="MIN_PER_KM",
                          help="override; otherwise uses your own logged pace")
    dist_cmd.add_argument("--zone", default="easy", choices=["easy", "moderate", "hard"])

    lib_cmd = sub.add_parser("workouts", help="local workout files and whether they were used")
    lib_cmd.add_argument("--check-garmin", action="store_true",
                         help="also ask Garmin about files with no upload stamp")
    lib_cmd.add_argument("--watch", action="store_true",
                         help="how full the watch is, and what is safe to remove")
    lib_cmd.add_argument("--cleanup", action="store_true",
                         help="delete the safest workouts to free watch slots (asks first)")
    lib_cmd.add_argument("--keep-free", type=int, default=5, metavar="N",
                         help="how many spare slots to aim for (default 5)")
    lib_cmd.add_argument("--yes", action="store_true",
                         help="skip the confirmation prompt")
    lib_cmd.add_argument("--backfill", action="store_true",
                         help="stamp files uploaded before stamping existed")

    run_cmd = sub.add_parser("run", help="running intensity distribution and VO2max")
    run_cmd.add_argument("--days", type=int, default=90,
                         help="how far back to look (default 90)")

    sync_cmd = sub.add_parser("sync", help="pull completed sessions from Garmin Connect")
    sync_cmd.add_argument("limit", nargs="?", type=int, default=30,
                          help="how many recent activities to scan (default 30)")
    sync_cmd.add_argument("--no-recovery", action="store_true",
                          help="skip refreshing sleep/readiness metrics")

    validate = sub.add_parser("validate", help="check a workout against the Garmin FIT SDK")
    validate.add_argument("workout_file")

    upload = sub.add_parser("upload", help="validate then push a workout to Garmin Connect")
    upload.add_argument("workout_file")
    upload.add_argument("--dry-run", action="store_true",
                        help="validate and show the workout without uploading")

    sub.add_parser("login", help="one-time interactive login, caches a session")
    return parser


def _run_suggest(args) -> None:
    as_of = date.fromisoformat(args.as_of) if args.as_of else None
    planned_date = (
        date.fromisoformat(args.planned_date)
        if args.planned_date
        else (date.today() + timedelta(days=1) if args.planned else None)
    )
    report.print_suggestion(as_of, args.planned, planned_date)


def _run_coach(args) -> None:
    if args.prescribed is not None:
        report.print_prescribed(args.prescribed or None)
        return

    results = judging.analyze(args.muscles)
    if not results:
        print("Nothing matched. Try `garmin coach` with no filter.")
        return

    if args.brief:
        report.print_brief(results, args.stale)
        return

    report.print_report(results, args.muscles, args.stale)
    if not args.muscles:
        report.print_unlabelled()


def _require_file(path_str: str) -> Path:
    path = Path(path_str)
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)
    return path


def _run_validate(args) -> None:
    from . import validation, workout as wk

    w = wk.load_workout(str(_require_file(args.workout_file)))
    errors = validation.validate_workout(w)
    if errors:
        print(f"Validation FAILED for '{w['name']}':")
        for e in errors:
            print(f"  x {e}")
        sys.exit(1)
    print(
        f"All {len(w['exercises'])} exercises in '{w['name']}' "
        "are valid Garmin FIT SDK entries."
    )

    # Anything they have never done deserves a form video before they load it.
    from . import store as _store

    names = [e["name"] for e in w["exercises"]]
    try:
        new = _store.never_done(names)
    except Exception:
        new = []
    if new:
        print(f"\n  {len(new)} exercise(s) you've never logged — check the form first:")
        for n in new:
            print(f"    {n.replace('_', ' ').title()}")
            print(f"      {_store.demo_url(n)}")

    # Valid but awkward: walking back to a station you already left usually means
    # losing it to someone else.
    from . import stations

    revisits = stations.revisits(w["exercises"])
    if revisits:
        print(f"\n  {len(revisits)} station revisit(s) — you'd walk back to:")
        for r in revisits:
            print(f"    {r['station']:<10} for {r['exercise'].replace('_', ' ').title()}")
        print("  Suggested order:")
        for e in stations.group_by_station(w["exercises"]):
            print(f"    {e['name'].replace('_', ' ').title()}  ({stations.station_of(e['name'])})")


def _run_upload(args) -> None:
    from . import history, validation, workout as wk
    from .client import get_client

    path = _require_file(args.workout_file)
    w = wk.load_workout(str(path))

    errors = validation.validate_workout(w)
    if errors:
        print(f"Validation FAILED for '{w['name']}' — nothing was uploaded:")
        for e in errors:
            print(f"  x {e}")
        sys.exit(1)

    report.print_workout(w)

    if args.dry_run:
        print("Dry run — validated only, nothing uploaded.")
        return

    client = get_client()
    print(f"Connected as: {client.get_full_name()}")

    # Check before consuming a slot, not after the watch refuses one.
    from . import library

    state = library.crowding(library.remote_workouts(client))
    if state["count"] and (state["crowded"] or state["over"]):
        print(
            f"  Note: {state['count']}/{state['limit']} workouts on the watch"
            f"{' — over the limit' if state['over'] else ''}. "
            "Run `garmin workouts --cleanup` to free some."
        )

    print(f"Uploading '{w['name']}'...")
    result = client.connectapi(
        "/workout-service/workout", method="POST", json=wk.build_payload(w)
    )
    workout_id = result.get("workoutId") if isinstance(result, dict) else result
    print(f"Done! Workout ID: {workout_id}")
    print("Garmin Connect -> Training -> Workouts -> sync to watch.")

    history.log_session(str(path), w)

    # Record it on the file too, so a later run knows this is no longer a draft
    # without having to ask Garmin.
    from . import library

    library.mark_uploaded(path)


def _run_plan(args) -> None:
    from .plan import staleness, week_start

    # Plan from current data by default. Asking the athlete to sync first is a
    # step they should never have to think about, and planning off stale data
    # quietly produces last week's advice.
    if not args.no_sync:
        stale = staleness()
        if stale:
            print(f"Local data is behind ({stale}) — syncing first...")
            try:
                from . import recovery, running
                from .sync import sync

                sync(50)
                running.sync_runs()
                recovery.fetch()
                print()
            except Exception as exc:
                print(f"  could not refresh: {exc}\n")

    if args.start in ("today", "tomorrow"):
        start = week_start(when=args.start)
    elif args.start:
        start = date.fromisoformat(args.start)
    else:
        start = None
    report.print_plan(args.goal, start, args.strength, args.runs, args.weekdays)


def _run_distance(args) -> None:
    report.print_distance(args.minutes, args.pace, args.zone)


def _run_library(args) -> None:
    from . import library

    if args.cleanup:
        report.run_cleanup(args.keep_free, args.yes)
        return

    if args.watch:
        report.print_crowding()
        return

    if args.backfill:
        count = library.backfill()
        print(f"Stamped {count} previously-uploaded file(s).\n")
    report.print_library(check_remote=args.check_garmin or args.backfill)


def _run_running(args) -> None:
    report.print_running(args.days)


def _run_sync(args) -> None:
    from . import recovery, running
    from .sync import sync

    sync(args.limit)

    print("\nPulling runs and VO2max...")
    try:
        result = running.sync_runs(args.limit)
        print(f"  {result['added']} new run(s), {result['total']} total.")
    except Exception as exc:
        print(f"  could not read running data: {exc}")

    if not args.no_recovery:
        print("\nRefreshing recovery metrics (sleep, readiness, body battery)...")
        try:
            recovery.fetch()
            note = recovery.advice()
            print(f"  {note}" if note else "  nothing notable in the last few days.")
        except Exception as exc:
            # Optional data on undocumented endpoints; never fail the sync for it.
            print(f"  could not read recovery metrics: {exc}")


def _run_login(_args) -> None:
    from .client import interactive_login

    interactive_login()


HANDLERS = {
    "suggest": _run_suggest,
    "run": _run_running,
    "workouts": _run_library,
    "distance": _run_distance,
    "plan": _run_plan,
    "coach": _run_coach,
    "sync": _run_sync,
    "validate": _run_validate,
    "upload": _run_upload,
    "login": _run_login,
}


def main(argv: list | None = None) -> None:
    args = build_parser().parse_args(argv)
    HANDLERS[args.command](args)


if __name__ == "__main__":
    main()
