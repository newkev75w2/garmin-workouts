"""
Tests for shaping raw Garmin data into per-exercise session history, and for
deciding which of it can be trusted.

These pin the guards against manual-entry error. Every case here is taken from
a real 20-session log, not invented — the numbers in the log really do include
a 16kg leg press and a 431kg push-up.
"""

from conftest import a_set, a_store, an_activity, days_ago

from garmin_workouts import store as st


class TestSuspectDetection:
    def test_typo_far_below_median_is_flagged(self, leg_press_with_typo):
        sessions = st.session_summaries(leg_press_with_typo)["LEG_PRESS"]
        by_weight = {s["top_weight"]: s for s in sessions}

        assert by_weight[16.0]["suspect"], "16kg among 120-200kg must be flagged"
        assert not by_weight[140.0]["suspect"]
        assert not by_weight[120.0]["suspect"]

    def test_flagged_session_names_a_reason(self, leg_press_with_typo):
        sessions = st.session_summaries(leg_press_with_typo)["LEG_PRESS"]
        bad = next(s for s in sessions if s["top_weight"] == 16.0)
        assert "16.0kg" in bad["suspect_reason"]

    def test_absolute_ceiling_catches_single_session_nonsense(self):
        """
        A median check cannot catch a bad number when the exercise has only ever
        been logged once — a 431kg push-up sits happily at its own median. The
        absolute ceiling is the backstop.
        """
        store = a_store(
            an_activity(days_ago(3), "Chest",
                        [a_set("BICEPS_PUSH_UP", 10, 431.0, "PUSH_UP")])
        )
        session = st.session_summaries(store)["BICEPS_PUSH_UP"][0]
        assert session["suspect"]
        assert "plausible" in session["suspect_reason"]

    def test_isolation_has_a_lower_ceiling_than_compounds(self):
        """150kg is fine for a squat and absurd for a lateral raise."""
        store = a_store(
            an_activity(days_ago(3), "Mixed", [
                a_set("BARBELL_SQUAT", 5, 150.0, "SQUAT"),
                a_set("DUMBBELL_LATERAL_RAISE", 12, 150.0, "LATERAL_RAISE"),
            ])
        )
        summaries = st.session_summaries(store)
        assert not summaries["BARBELL_SQUAT"][0]["suspect"]
        assert summaries["DUMBBELL_LATERAL_RAISE"][0]["suspect"]

    def test_session_mostly_missing_weight_is_untrusted(self):
        store = a_store(
            an_activity(days_ago(3), "Back", [
                a_set("SEATED_CABLE_ROW", 10, 40.0),
                a_set("SEATED_CABLE_ROW", 10, None),
                a_set("SEATED_CABLE_ROW", 10, None),
            ])
        )
        session = st.session_summaries(store)["SEATED_CABLE_ROW"][0]
        assert session["suspect"]
        assert "without weight" in session["suspect_reason"]


class TestWorkingSets:
    def test_warmup_sets_are_excluded(self):
        """A ramp of 25/32/39kg is one working set at 39, not three."""
        store = a_store(
            an_activity(days_ago(2), "Back", [
                a_set("ALTERNATING_DUMBBELL_ROW", 10, 25.0),
                a_set("ALTERNATING_DUMBBELL_ROW", 10, 32.0),
                a_set("ALTERNATING_DUMBBELL_ROW", 10, 39.0),
            ])
        )
        session = st.session_summaries(store)["ALTERNATING_DUMBBELL_ROW"][0]
        assert session["top_weight"] == 39.0
        assert session["working_reps"] == [10]
        assert session["num_sets"] == 3

    def test_sets_near_the_top_weight_all_count(self):
        store = a_store(
            an_activity(days_ago(2), "Back", [
                a_set("SEATED_CABLE_ROW", 8, 50.0),
                a_set("SEATED_CABLE_ROW", 11, 52.0),
                a_set("SEATED_CABLE_ROW", 11, 52.0),
            ])
        )
        session = st.session_summaries(store)["SEATED_CABLE_ROW"][0]
        assert session["working_reps"] == [8, 11, 11]


class TestUnlabelledWork:
    def test_real_unlabelled_work_is_surfaced(self):
        """
        Sets the watch could not name still happened, and are often the heaviest
        of the day. Dropping them silently made lifts look like they regressed.
        """
        store = a_store(
            an_activity(days_ago(2), "Back and biceps", [
                a_set(None, 6, 80.0),
                a_set(None, 5, 80.0),
                a_set("SEATED_CABLE_ROW", 11, 35.0),
            ])
        )
        found = st.unlabelled_work(store)
        assert len(found) == 1
        assert found[0]["top_weight"] == 80.0
        assert found[0]["sets"] == [(6, 80.0), (5, 80.0)]

    def test_empty_placeholder_sets_are_not_reported(self):
        """reps=0 with no weight is an empty set, not lost work."""
        store = a_store(
            an_activity(days_ago(2), "Legs", [a_set(None, 0, None)])
        )
        assert st.unlabelled_work(store) == []

    def test_unlabelled_sets_never_become_an_exercise(self):
        store = a_store(
            an_activity(days_ago(2), "Back", [a_set(None, 6, 80.0)])
        )
        assert st.session_summaries(store) == {}


class TestTimedExercises:
    def test_a_hold_is_measured_in_seconds_not_reps(self):
        """
        Garmin collects a rep count even for a timed hold. A real 45-second
        plank came back as 5, 7 and 12 "reps" with the duration correct at
        45.0s each — so the duration is the number that means anything.
        """
        sets = [
            {**a_set("_45_DEGREE_PLANK", reps, 73.0, "PLANK"), "duration_s": 45.0}
            for reps in (5, 7, 12)
        ]
        summary = st.session_summaries(
            a_store(an_activity(days_ago(2), "Core", sets))
        )["_45_DEGREE_PLANK"][0]

        assert summary["timed"] is True
        assert summary["unit"] == "s"
        assert summary["working_reps"] == [45, 45, 45]

    def test_a_rep_exercise_is_unaffected(self):
        sets = [
            {**a_set("HANGING_LEG_RAISE", reps, None, "LEG_RAISE"), "duration_s": 30.0}
            for reps in (7, 7, 5)
        ]
        summary = st.session_summaries(
            a_store(an_activity(days_ago(2), "Core", sets))
        )["HANGING_LEG_RAISE"][0]

        assert summary["timed"] is False
        assert summary["working_reps"] == [7, 7, 5]

    def test_a_set_with_no_rep_count_still_counts(self):
        """Previously dropped entirely, taking real work out of the analysis."""
        sets = [{**a_set("PLANK", None, None, "PLANK"), "duration_s": 60.0}]
        summary = st.session_summaries(
            a_store(an_activity(days_ago(2), "Core", sets))
        )["PLANK"][0]
        assert summary["working_reps"] == [60]
