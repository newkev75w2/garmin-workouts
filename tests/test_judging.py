"""
Tests for the per-exercise verdict.

The thresholds here were tuned against a real log where a naive comparison
called ~20% of exercises "regressed" and would have had the lifter cutting load
they never lost. These tests exist so that tuning cannot silently drift.
"""

from conftest import a_set, a_store, an_activity, days_ago

from garmin_workouts import judging, store as st


def verdict_for(store, exercise, targets=None):
    sessions = st.session_summaries(store)[exercise]
    return judging.judge(exercise, sessions, targets or {})


def sessions_of(exercise, entries, category="ROW"):
    """entries: list of (days_ago, weight, [reps per set])"""
    return a_store(*[
        an_activity(days_ago(d), "S", [a_set(exercise, r, w, category) for r in reps])
        for d, w, reps in entries
    ])


class TestLoadIncrement:
    def test_increment_scales_with_the_lift(self):
        assert judging.load_increment(80.0) == 5.0
        assert judging.load_increment(40.0) == 2.5
        assert judging.load_increment(15.0) == 2.0
        assert judging.load_increment(8.0) == 1.0

    def test_no_weight_means_no_increment(self):
        assert judging.load_increment(None) == 0.0


class TestRegression:
    def test_meaningful_drop_is_flagged(self):
        store = sessions_of("SEATED_CABLE_ROW",
                            [(20, 52.0, [11, 11]), (2, 35.0, [11, 11])])
        assert verdict_for(store, "SEATED_CABLE_ROW")["verdict"] == "regressed"

    def test_one_pin_on_a_cable_stack_is_not_a_regression(self):
        """
        17kg -> 15kg is a 12% drop, which clears the percentage floor, but it is
        also exactly one increment at that load. Calling it a regression would
        have the lifter chasing noise.
        """
        store = sessions_of("CABLE_CROSSOVER",
                            [(20, 17.0, [15, 15]), (2, 15.0, [15, 15])],
                            category="FLYE")
        assert verdict_for(store, "CABLE_CROSSOVER")["verdict"] != "regressed"

    def test_suspect_latest_session_never_reports_regression(self):
        """A mistyped number must not be read as lost strength."""
        store = sessions_of("LEG_PRESS",
                            [(30, 120.0, [12]), (20, 130.0, [12]),
                             (10, 140.0, [12]), (2, 16.0, [12])],
                            category="SQUAT")
        result = verdict_for(store, "LEG_PRESS")
        assert result["verdict"] == "check-data"
        assert "confirm what you actually lifted" in result["suggestion"]


class TestProgression:
    def test_hitting_target_on_every_set_earns_a_jump(self):
        store = sessions_of("ONE_ARM_CONCENTRATION_CURL",
                            [(9, 14.0, [6, 6]), (2, 14.0, [6, 6])],
                            category="CURL")
        result = verdict_for(store, "ONE_ARM_CONCENTRATION_CURL", {"ONE_ARM_CONCENTRATION_CURL": 6})
        assert result["verdict"] == "ready"
        assert "16.0kg" in result["suggestion"]

    def test_missing_target_holds_the_load(self):
        store = sessions_of("DUMBBELL_HAMMER_CURL",
                            [(9, 12.0, [12, 12, 12]), (2, 12.0, [12, 12, 8])],
                            category="CURL")
        result = verdict_for(store, "DUMBBELL_HAMMER_CURL", {"DUMBBELL_HAMMER_CURL": 12})
        assert result["verdict"] in ("holding", "progressing")
        assert "16" not in result["suggestion"], "must not suggest adding load"

    def test_stalled_after_repeated_sessions_at_one_weight(self):
        store = sessions_of("ROMANIAN_DEADLIFT",
                            [(37, 60.0, [8]), (15, 60.0, [8]),
                             (9, 60.0, [8]), (1, 60.0, [6])],
                            category="DEADLIFT")
        result = verdict_for(store, "ROMANIAN_DEADLIFT", {"ROMANIAN_DEADLIFT": 10})
        assert result["verdict"] == "stalled"
        assert "swap" in result["suggestion"]


class TestSpecialCases:
    def test_bodyweight_movements_are_judged_on_reps_not_load(self):
        """
        Garmin logs dips as bodyweight in one session and added/assist load in
        the next (9, 76, 72, 19kg in the real log), so load comparisons are
        meaningless for these.
        """
        store = sessions_of("BODY_WEIGHT_DIP",
                            [(9, 72.0, [10, 10]), (2, 74.0, [12, 12])],
                            category="PUSH_UP")
        result = verdict_for(store, "BODY_WEIGHT_DIP", {"BODY_WEIGHT_DIP": 10})
        assert result["verdict"] != "regressed"
        assert "kg" not in result["suggestion"], "load advice is meaningless here"

    def test_untrained_for_three_weeks_is_stale_not_progressable(self):
        store = sessions_of("CLOSE_GRIP_LAT_PULLDOWN",
                            [(40, 52.0, [12]), (25, 52.0, [12])],
                            category="PULL_UP")
        result = verdict_for(store, "CLOSE_GRIP_LAT_PULLDOWN")
        assert result["verdict"] == "stale"
        assert "25 days" in result["suggestion"]

    def test_single_session_is_a_baseline_not_a_trend(self):
        store = sessions_of("KNEELING_REAR_FLYE", [(2, 39.0, [12])], category="FLYE")
        assert verdict_for(store, "KNEELING_REAR_FLYE")["verdict"] == "baseline"

    def test_progressing_verdict_never_contradicts_its_advice(self):
        """
        A verdict of 'progressing' paired with advice to 'hold' read as a
        contradiction to the user; the wording must agree with the verdict.
        """
        store = sessions_of("DUMBBELL_BENCH_PRESS",
                            [(9, 30.0, [9, 8]), (2, 30.0, [9, 10, 5])],
                            category="BENCH_PRESS")
        result = verdict_for(store, "DUMBBELL_BENCH_PRESS", {"DUMBBELL_BENCH_PRESS": 10})
        if result["verdict"] == "progressing":
            assert not result["suggestion"].startswith("hold ")
