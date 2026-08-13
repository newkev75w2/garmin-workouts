"""
Tests for scheduling strength and running in one week.

The constraints worth protecting are the ones between the two disciplines —
they're the reason this exists rather than two separate planners, and they're
invisible to either one alone.
"""


from conftest import a_set, a_store, an_activity, days_ago

from garmin_workouts import plan


def a_history():
    """
    Enough logged work across enough muscle groups that suggest_focus can fill a
    four-session week. A thinner fixture runs out of fresh groups and skips a
    day, which is correct behaviour but makes the test measure the fixture
    rather than the planner.
    """
    return a_store(*[
        an_activity(days_ago(d), "S", [a_set("EX", 10, 40.0, cat)] * n)
        for d, cat, n in [
            (9, "SQUAT", 40), (8, "BENCH_PRESS", 30), (7, "ROW", 30),
            (6, "SHOULDER_PRESS", 15), (12, "CORE", 4), (5, "CURL", 20),
            (11, "TRICEPS_EXTENSION", 12), (10, "DEADLIFT", 18),
            (13, "CALF_RAISE", 6), (9, "PULL_UP", 14),
        ]
    ])


def sessions_of(week, kind, intensity=None):
    out = []
    for i, day in enumerate(week["days"]):
        for s in day["sessions"]:
            if s["type"] == kind and (intensity is None or s["intensity"] == intensity):
                out.append((i, day, s))
    return out


class TestShape:
    def test_a_week_is_seven_days(self):
        week = plan.build_week(store=a_history())
        assert len(week["days"]) == 7

    def test_sessions_are_spread_not_stacked_at_the_front(self):
        """
        Filling slots in order produced four straight training days and three
        rest days stacked at the end — worse training and obviously wrong.
        """
        week = plan.build_week(store=a_history())
        trained = [i for i, d in enumerate(week["days"]) if d["sessions"]]
        gaps = [b - a for a, b in zip(trained, trained[1:])]
        assert max(gaps) <= 2, f"training days clustered: {trained}"

    def test_the_goal_sets_the_session_mix(self, monkeypatch):
        """
        Total run count can converge between goals once the ramp cap bites — at
        0.7 runs a week everything reduces to "run a bit more". What must still
        differ is the shape: an aerobic goal buys a quality session, a strength
        goal buys a lifting one.
        """
        monkeypatch.setattr(plan.running, "distribution",
                            lambda *a, **k: {"runs": 12, "days": 30, "km": 90,
                                             "easy": 9, "easy_share": 0.75})
        monkeypatch.setattr(plan.running, "vo2max_trend",
                            lambda: [("2026-07-01", 40.0), ("2026-08-01", 42.0)])
        monkeypatch.setattr(plan.recovery, "advice", lambda *a, **k: None)

        vo2 = plan.build_week(goal="vo2max", store=a_history())
        lifting = plan.build_week(goal="strength", store=a_history())

        assert len(sessions_of(vo2, "run", "quality")) > 0
        assert len(sessions_of(lifting, "run", "quality")) == 0
        assert len(sessions_of(lifting, "strength")) > len(sessions_of(vo2, "strength"))

    def test_a_strength_goal_drops_quality_runs_entirely(self):
        week = plan.build_week(goal="strength", store=a_history())
        assert sessions_of(week, "run", "quality") == []


class TestInterference:
    def test_legs_never_land_next_to_a_quality_run(self):
        """The interference runs both ways, so both neighbours are protected."""
        week = plan.build_week(store=a_history())
        quality = [i for i, _, _ in sessions_of(week, "run", "quality")]

        for i, day, s in sessions_of(week, "strength"):
            focus = s["detail"].split(" + ")
            if any(g in plan.LEG_GROUPS for g in focus):
                for q in quality:
                    assert abs(i - q) > 1, f"leg day {i} sits beside quality run {q}"

    def test_an_easy_run_may_share_a_day_with_upper_body_work(self):
        week = plan.build_week(store=a_history())
        for _, day, _ in sessions_of(week, "run", "easy"):
            strength = [s for s in day["sessions"] if s["type"] == "strength"]
            if strength:
                assert any("hours between" in n for n in day["notes"])

    def test_no_run_is_scheduled_onto_freshly_trained_legs(self):
        week = plan.build_week(store=a_history())
        for _, day, _ in sessions_of(week, "run"):
            for s in day["sessions"]:
                if s["type"] == "strength":
                    focus = s["detail"].split(" + ")
                    assert not any(g in plan.LEG_GROUPS for g in focus)

    def test_the_priority_session_is_scheduled_first_on_a_shared_day(self):
        week = plan.build_week(store=a_history())
        for day in week["days"]:
            if len(day["sessions"]) > 1:
                assert day["sessions"][0]["when"] == "am"
                assert day["sessions"][-1]["when"] == "pm"


class TestSpread:
    def test_picks_evenly_across_what_is_available(self):
        assert plan.spread([0, 1, 2, 3, 4, 5, 6], 3) == [0, 2, 4]

    def test_asking_for_more_than_exists_returns_everything(self):
        assert plan.spread([0, 1], 5) == [0, 1]

    def test_asking_for_none_returns_nothing(self):
        assert plan.spread([0, 1, 2], 0) == []


class TestWeekStart:
    def test_defaults_to_the_coming_monday(self):
        """
        A training week is a calendar week. Starting "tomorrow" produced plans
        running Wednesday to Tuesday, which is awkward to follow and impossible
        to compare week against week.
        """
        from datetime import date

        saturday = date(2026, 8, 8)
        assert plan.week_start(saturday) == date(2026, 8, 10)

    def test_monday_plans_the_week_you_are_standing_in(self):
        from datetime import date

        monday = date(2026, 8, 10)
        assert plan.week_start(monday) == monday

    def test_explicit_tomorrow_still_works(self):
        from datetime import date

        assert plan.week_start(date(2026, 8, 8), when="tomorrow") == date(2026, 8, 9)

    def test_the_plan_runs_monday_to_sunday(self):
        from datetime import date

        week = plan.build_week(start=date(2026, 8, 10), store=a_history())
        assert week["days"][0]["date"].strftime("%A") == "Monday"
        assert week["days"][-1]["date"].strftime("%A") == "Sunday"


class TestTimeOfDay:
    def test_a_lone_session_is_not_pinned_to_a_time(self):
        """Saying 'am' for a single session implies a rule that isn't there."""
        week = plan.build_week(store=a_history())
        for day in week["days"]:
            if len(day["sessions"]) == 1:
                assert day["sessions"][0]["when"] == "any"

    def test_a_shared_day_splits_into_am_and_pm(self):
        week = plan.build_week(store=a_history())
        for day in week["days"]:
            if len(day["sessions"]) > 1:
                assert {s["when"] for s in day["sessions"]} == {"am", "pm"}


class TestMixRecommendation:
    def test_running_volume_is_ramped_not_jumped(self, monkeypatch):
        """
        Asking someone who runs 0.7 times a week for four runs produces a week
        they abandon. Aerobic fitness responds to consistency; injury and
        abandonment respond to jumping volume.
        """
        monkeypatch.setattr(plan.running, "distribution",
                            lambda *a, **k: {"runs": 3, "days": 30, "km": 12,
                                             "easy": 1, "easy_share": 0.3})
        monkeypatch.setattr(plan.running, "vo2max_trend", lambda: [])
        monkeypatch.setattr(plan.recovery, "advice", lambda *a, **k: None)

        mix = plan.recommend_mix("vo2max")
        assert mix["quality"] + mix["easy"] <= 3

    def test_a_flat_vo2max_buys_intensity_not_more_easy_volume(self, monkeypatch):
        monkeypatch.setattr(plan.running, "distribution",
                            lambda *a, **k: {"runs": 12, "days": 30, "km": 90,
                                             "easy": 9, "easy_share": 0.75})
        monkeypatch.setattr(plan.running, "vo2max_trend",
                            lambda: [("2026-06-01", 42.0), ("2026-07-01", 42.0),
                                     ("2026-08-01", 42.0)])
        monkeypatch.setattr(plan.recovery, "advice", lambda *a, **k: None)

        mix = plan.recommend_mix("vo2max")
        assert mix["quality"] >= 2
        assert any("flat" in n for n in mix["notes"])

    def test_an_explicit_split_is_honoured(self):
        week = plan.build_week(strength_days=4, runs=2, store=a_history())
        strength = [s for d in week["days"] for s in d["sessions"] if s["type"] == "strength"]
        runs = [s for d in week["days"] for s in d["sessions"] if s["type"] == "run"]
        assert len(strength) == 4
        assert len(runs) == 2
        assert week["overridden"] is True


class TestRestDays:
    def test_a_busy_week_still_keeps_two_clear_days(self):
        """
        Six sessions spread across seven days leaves one rest day. Stacking an
        easy run onto an upper-body session buys back a second without dropping
        any work — a hard week with no recovery produces fatigue, not adaptation.
        """
        week = plan.build_week(strength_days=4, runs=2, store=a_history())
        rest = [d for d in week["days"] if not d["sessions"]]
        assert len(rest) >= plan.MIN_REST_DAYS

    def test_the_long_run_gets_a_day_to_itself(self):
        """Stacking the volume session behind lifting makes it a tired short run."""
        week = plan.build_week(store=a_history())
        for day in week["days"]:
            longs = [s for s in day["sessions"] if s["intensity"] == "long"]
            if longs:
                assert len(day["sessions"]) == 1


class TestAvailability:
    def test_days_ruled_out_stay_empty(self):
        """
        Scheduling onto a day the athlete has said they cannot train reads as
        ignoring them, and was the first thing real use turned up.
        """
        week = plan.build_week(weekdays="mon-fri", strength_days=4, runs=2,
                               store=a_history())
        for day in week["days"][5:]:
            assert day["sessions"] == []

    def test_the_requested_counts_are_not_exceeded(self):
        week = plan.build_week(weekdays="mon-fri", strength_days=4, runs=2,
                               store=a_history())
        assert len(sessions_of(week, "strength")) == 4
        assert len(sessions_of(week, "run")) == 2

    def test_a_list_of_days_works_as_well_as_a_range(self):
        assert plan.parse_weekdays("mon,wed,fri") == {0, 2, 4}
        assert plan.parse_weekdays("mon-fri") == {0, 1, 2, 3, 4}

    def test_no_constraint_means_the_whole_week(self):
        assert plan.parse_weekdays(None) == set(range(7))

    def test_nonsense_falls_back_to_the_whole_week_rather_than_nothing(self):
        assert plan.parse_weekdays("blursday") == set(range(7))

    def test_rest_days_come_out_of_available_days_not_the_calendar(self):
        week = plan.build_week(weekdays="mon-fri", strength_days=3, runs=1,
                               store=a_history())
        working = [d for d in week["days"][:5] if not d["sessions"]]
        assert len(working) >= 1


class TestCapacityWarning:
    def test_a_week_that_will_not_fit_is_flagged(self, monkeypatch, capsys):
        """
        Finding out the watch is full when it refuses the fourth upload is too
        late — the week is planned before anything is built.
        """
        from garmin_workouts import library, report

        monkeypatch.setattr(library, "crowding",
                            lambda *a, **k: {"count": 14, "limit": 16,
                                             "crowded": True, "over": False})
        monkeypatch.setattr(report, "print_suggestion", lambda *a, **k: None)
        report.print_plan("vo2max")
        out = capsys.readouterr().out
        assert "Watch capacity" in out and "cleanup" in out

    def test_capacity_trouble_never_breaks_the_plan(self, monkeypatch, capsys):
        """It is a courtesy; a plan is still useful when Garmin is unreachable."""
        from garmin_workouts import library, report

        def boom(*a, **k):
            raise RuntimeError("garmin unreachable")

        monkeypatch.setattr(library, "crowding", boom)
        report.print_plan("vo2max")
        assert "goal" in capsys.readouterr().out
