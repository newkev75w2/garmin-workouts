"""
Tests for the recovery advisory.

Two things matter here: reading Garmin's inconsistently-nested payloads, and
staying quiet. An advisory that fires every day gets ignored, which is worse
than not having one.
"""

from garmin_workouts import recovery


class TestPayloadParsing:
    def test_finds_a_value_nested_under_an_unrelated_key(self):
        """
        Sleep duration lives at dailySleepDTO.sleepTimeSeconds while readiness
        sits at the top level, so the search must descend through every dict —
        not only ones whose own key already matched.
        """
        payload = {"dailySleepDTO": {"sleepTimeSeconds": 29040}}
        assert recovery._first_number(payload, "sleepTimeSeconds") == 29040

    def test_reads_the_first_entry_of_a_list_response(self):
        assert recovery._first_number([{"score": 66}], "score") == 66

    def test_booleans_are_not_mistaken_for_numbers(self):
        payload = {"sleepWindowConfirmed": True, "dailySleepDTO": {"sleepTimeSeconds": 100}}
        assert recovery._first_number(payload, "sleepWindowConfirmed") is None

    def test_a_missing_metric_is_not_an_error(self):
        assert recovery._first_number({}, "score") is None


class TestAdvice:
    def test_says_nothing_when_numbers_are_unremarkable(self):
        assert recovery.advice({"days_seen": 3, "readiness": 55, "sleep_hours": 7.5}) is None

    def test_flags_low_readiness(self):
        note = recovery.advice({"days_seen": 3, "readiness": 30, "sleep_hours": 7.5})
        assert note and "readiness" in note

    def test_flags_short_sleep(self):
        note = recovery.advice({"days_seen": 2, "sleep_hours": 5.1})
        assert note and "5.1h" in note

    def test_confirms_when_recovery_is_good(self):
        note = recovery.advice({"days_seen": 3, "readiness": 80})
        assert note and "train as planned" in note

    def test_no_data_means_no_opinion(self):
        assert recovery.advice({}) is None
