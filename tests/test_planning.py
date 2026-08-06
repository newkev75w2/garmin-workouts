"""
Tests for choosing which muscle groups to train next.
"""

from conftest import a_set, a_store, an_activity, days_ago

from garmin_workouts import planning


def trained(group_sets):
    """group_sets: list of (days_ago, category, count)"""
    return a_store(*[
        an_activity(days_ago(d), "S", [a_set("EX", 10, 40.0, cat)] * n)
        for d, cat, n in group_sets
    ])


class TestRecovery:
    def test_everything_trained_recently_means_rest(self):
        store = trained([(0, "SQUAT", 5), (1, "BENCH_PRESS", 5), (1, "ROW", 5)])
        result = planning.suggest_focus(store)
        assert result["primary"] is None
        assert "rest day" in result["reason"]

    def test_a_group_inside_the_recovery_window_is_not_offered(self):
        store = trained([(0, "SQUAT", 2), (5, "CURL", 20)])
        result = planning.suggest_focus(store)
        assert result["primary"] == "biceps", "legs trained today must not be offered"


class TestVolumeDeficit:
    def test_the_most_neglected_group_wins(self):
        store = trained([
            (10, "CORE", 3),       # barely trained, long ago
            (3, "TRICEPS_EXTENSION", 40),
            (4, "BENCH_PRESS", 60),
        ])
        assert planning.suggest_focus(store)["primary"] == "core"

    def test_reason_cites_the_numbers_behind_the_call(self):
        store = trained([(10, "CORE", 3), (3, "BENCH_PRESS", 60)])
        reason = planning.suggest_focus(store)["reason"]
        assert "3 sets" in reason and "60" in reason


class TestPairing:
    def test_pairing_follows_affinity_when_available(self):
        store = trained([(6, "ROW", 5), (5, "CURL", 6), (0, "SQUAT", 40)])
        result = planning.suggest_focus(store)
        assert {result["primary"], result["partner"]} == {"back", "biceps"}

    def test_two_small_groups_are_flagged_as_a_weak_session(self):
        store = trained([
            (10, "CORE", 3), (4, "TRICEPS_EXTENSION", 8),
            (1, "BENCH_PRESS", 60), (0, "SQUAT", 60), (1, "ROW", 60),
        ])
        result = planning.suggest_focus(store)
        assert result["caveat"] is not None
        assert "small groups" in result["caveat"]

    def test_caveat_suggests_a_rested_major_group_not_a_just_trained_one(self):
        """
        Regression test. This originally picked the major group with the FEWEST
        days of rest — i.e. the one trained that very morning — and advised
        pairing with it.
        """
        store = trained([
            (10, "CORE", 3), (4, "TRICEPS_EXTENSION", 8),
            (0, "SQUAT", 60),        # legs trained today
            (3, "BENCH_PRESS", 20),  # chest rested longer and has less volume
        ])
        caveat = planning.suggest_focus(store)["caveat"]
        assert "legs" not in caveat, "must not propose a group trained today"
        assert "chest" in caveat


class TestVolumeAccounting:
    def test_a_category_counts_toward_exactly_one_group(self):
        """
        MUSCLE_CATEGORIES deliberately overlaps (a shrug is back and shoulder
        work), which is right for filtering but would double-count volume when
        ranking groups against each other.
        """
        store = trained([(5, "SHRUG", 10)])
        loads = planning.group_load(store)
        counted = [g for g, v in loads.items() if v["sets"] > 0]
        assert len(counted) == 1

    def test_unknown_categories_are_ignored_rather_than_guessed(self):
        store = trained([(5, "SOMETHING_NEW", 10)])
        assert planning.group_load(store) == {}


class TestPartnerRanking:
    def test_partner_is_chosen_by_data_not_list_order(self):
        """
        Regression test. Affinity lists which groups pair sensibly; it must not
        decide which of them wins. This originally took the first recovered
        entry, so core paired with back over shoulders purely because "back"
        was typed first — even with back carrying far more volume.
        """
        store = trained([
            (11, "CORE", 3),
            (2, "ROW", 85),             # back: recovered but heavily trained
            (2, "SHOULDER_PRESS", 50),  # shoulders: recovered and less trained
        ])
        result = planning.suggest_focus(store)
        assert result["primary"] == "core"
        assert result["partner"] == "shoulders"

    def test_falls_outside_affinity_only_when_nothing_else_is_ready(self):
        store = trained([(11, "CORE", 3), (0, "ROW", 40), (5, "CURL", 40)])
        result = planning.suggest_focus(store)
        assert result["partner"] == "biceps"


class TestPlanningAhead:
    def test_as_of_lets_a_group_recover_by_the_planned_day(self):
        """
        "What should I train on Monday?" is a different question from "what now" —
        groups inside the recovery window today have cleared it by then.
        """
        from datetime import date, timedelta

        store = trained([(0, "SQUAT", 40), (0, "BENCH_PRESS", 10)])
        today = planning.suggest_focus(store)
        assert today["primary"] is None, "everything trained today means rest"

        later = planning.suggest_focus(store, as_of=date.today() + timedelta(days=3))
        assert later["primary"] == "chest", "three days on, chest has recovered"

    def test_a_planned_session_consumes_recovery(self):
        """
        A session the user intends to do has not reached Garmin yet, but it still
        has to count — otherwise planning Monday around a Friday session happily
        prescribes the same muscles twice.
        """
        from datetime import date

        store = trained([(10, "CORE", 3), (10, "BENCH_PRESS", 40)])
        planned_day = date.today()
        result = planning.suggest_focus(
            store, as_of=planned_day, planned=["core"], planned_date=planned_day
        )
        assert result["groups"]["core"]["days_ago"] == 0
        assert not result["groups"]["core"]["recovered"]
        assert result["primary"] != "core"
