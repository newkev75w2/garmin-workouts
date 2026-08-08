"""
Tests for noticing when a prescription did not match what happened.

Asking for 15 reps and getting 10 every time is the prescription being wrong,
not the lifter failing — and repeating it just repeats the miss.
"""

from conftest import a_set, a_store, an_activity, days_ago

from garmin_workouts import judging, store as st


def sessions_of(entries, exercise="DUMBBELL_BENCH_PRESS", category="BENCH_PRESS"):
    store = a_store(*[
        an_activity(days_ago(d), "S", [a_set(exercise, r, w, category) for r in reps])
        for d, w, reps in entries
    ])
    return st.session_summaries(store)[exercise]


class TestPrescriptionAdvice:
    def test_consistently_missing_the_target_lowers_it(self):
        sessions = sessions_of([(9, 30.0, [6, 6]), (2, 30.0, [5, 5])])
        note = judging.prescription_advice(sessions, target=10, unit="")
        assert note and "prescribe 6" in note and "not 10" in note

    def test_consistently_beating_the_target_raises_it(self):
        sessions = sessions_of([(9, 30.0, [15, 15]), (2, 30.0, [16, 16])])
        note = judging.prescription_advice(sessions, target=10, unit="")
        assert note and "too soft" in note

    def test_hitting_the_target_says_nothing(self):
        sessions = sessions_of([(9, 30.0, [10, 10]), (2, 30.0, [10, 9])])
        assert judging.prescription_advice(sessions, target=10, unit="") is None

    def test_one_bad_session_does_not_rewrite_the_programme(self):
        """A single miss is a bad day; two agreeing sessions are a pattern."""
        sessions = sessions_of([(9, 30.0, [10, 10]), (2, 30.0, [5, 5])])
        assert judging.prescription_advice(sessions, target=10, unit="") is None

    def test_a_single_session_is_not_enough_to_judge(self):
        sessions = sessions_of([(2, 30.0, [5, 5])])
        assert judging.prescription_advice(sessions, target=10, unit="") is None

    def test_no_target_means_no_advice(self):
        sessions = sessions_of([(9, 30.0, [6]), (2, 30.0, [6])])
        assert judging.prescription_advice(sessions, target=None, unit="") is None
