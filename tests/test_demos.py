"""
Tests for matching Garmin exercise names to wger demonstration images.

The risk this guards is specific: showing a confident image of the WRONG
movement. Measured against a real exercise list, naive matching paired a
dumbbell row with a hammer curl and a biceps curl with a wrist curl. These
tests pin the three defences — blocking known-bad pairs, requiring the muscle
group to agree before calling a match "likely", and never labelling a guess as
anything better than "uncertain".
"""

import pytest

from garmin_workouts import demos


@pytest.fixture
def index():
    """A small stand-in for wger's data, including its naming quirks."""
    def entry(name, category, key=None):
        return {
            "name": name,
            "key": key or demos.normalise(name),
            "category": category,
            "image": f"https://wger.de/media/{demos.normalise(name)}.png",
            "author": "someone",
            "licence": "CC BY-SA 3.0",
            "page": "https://wger.de/en/exercise/1/view/",
        }

    return [
        entry("Seated Cable Row", "Back"),
        entry("Shrugs, Barbells", "Back"),
        entry("Barbell Wrist Curl", "Arms"),
        entry("Biceps Curls With Barbell", "Arms"),
        entry("Alternating dumbbell hammer curl", "Arms"),
        entry("Leg Press", "Legs"),
        entry("Cable Cross-over", "Chest"),
    ]


class TestConfidence:
    def test_curated_pairs_are_verified(self, index):
        result = demos.match("SEATED_CABLE_ROW", "ROW", index)
        assert result["confidence"] == "verified"
        assert result["match_name"] == "Seated Cable Row"

    def test_unmatchable_exercise_reports_none_with_a_search_link(self, index):
        result = demos.match("ZERCHER_CARRY", "SQUAT", index)
        assert result["confidence"] == "none"
        assert result["image"] is None
        assert result["search"].startswith("http")

    def test_a_guess_is_never_labelled_better_than_uncertain(self, index):
        """
        BARBELL_DEADLIFT has no true entry here. Whatever it lands on must not
        be dressed up as verified or likely.
        """
        result = demos.match("BARBELL_DEADLIFT", "DEADLIFT", index)
        assert result["confidence"] in ("uncertain", "none")


class TestWrongMatchDefences:
    def test_known_bad_pairing_is_blocked(self, index):
        """A row must never be illustrated with a hammer curl."""
        result = demos.match("ALTERNATING_DUMBBELL_ROW", "ROW", index)
        assert result["match_name"] != "Alternating dumbbell hammer curl"

    def test_blocked_candidate_does_not_beat_the_correct_one(self, index):
        """
        A wrist curl and a biceps curl are both "Arms", so the category gate
        cannot separate them — the block list has to.
        """
        result = demos.match("BARBELL_BICEPS_CURL", "CURL", index)
        assert result["match_name"] == "Biceps Curls With Barbell"

    def test_muscle_group_must_agree_for_a_likely_match(self, index):
        """A chest movement must not be satisfied by a leg exercise."""
        result = demos.match("MACHINE_CHEST_PRESS", "BENCH_PRESS", index)
        assert result["confidence"] != "likely" or result["match_name"] == "Cable Cross-over"


class TestNameHandling:
    def test_inverted_pluralised_names_still_match(self):
        """
        wger writes "Shrugs, Barbells" where Garmin writes BARBELL_SHRUG.
        Sequence similarity alone scores that pair far too low.
        """
        assert demos.similarity(
            demos.normalise("BARBELL_SHRUG"), demos.normalise("Shrugs, Barbells")
        ) >= demos.STRONG_MATCH

    def test_leading_digits_are_stripped(self):
        assert demos.normalise("_30_DEGREE_LAT_PULLDOWN") == "degree lat pulldown"

    def test_setup_words_do_not_carry_meaning(self):
        assert "machine" not in demos.tokens("Machine chest fly")
