"""
Tests for naming sets the watch recorded but could not identify.

Those sets are real work — often the heaviest of the day — and are invisible to
every verdict until named. Getting the grouping wrong merges two exercises into
one, which then produces a history for a lift that was never performed.
"""

import pytest

from conftest import a_set, a_store, an_activity

from garmin_workouts import labelling


def session(*sets):
    return a_store(an_activity("2026-08-18", "Back & Biceps", list(sets)))


def unnamed(reps, weight):
    s = a_set(None, reps, weight)
    return s


class TestBlocks:
    def test_consecutive_unnamed_sets_group_together(self):
        store = session(unnamed(9, 70.0), unnamed(6, 70.0), unnamed(5, 70.0))
        found = labelling.blocks("2026-08-18", store)
        assert len(found) == 1
        assert len(found[0]["sets"]) == 3

    def test_named_sets_break_a_block(self):
        store = session(unnamed(9, 70.0), a_set("SEATED_CABLE_ROW", 10, 39.0),
                        unnamed(12, 41.0))
        assert len(labelling.blocks("2026-08-18", store)) == 2

    def test_a_weight_drop_after_a_ramp_starts_a_new_exercise(self):
        """
        Two exercises done back to back arrive as one run of unnamed sets. The
        giveaway is ramping up then dropping well below the peak.
        """
        store = session(unnamed(10, 52.0), unnamed(12, 62.0), unnamed(12, 62.0),
                        unnamed(12, 41.0), unnamed(11, 45.0), unnamed(13, 45.0))
        found = labelling.blocks("2026-08-18", store)
        assert len(found) == 2
        assert [s["weight_kg"] for s in found[0]["sets"]] == [52.0, 62.0, 62.0]
        assert [s["weight_kg"] for s in found[1]["sets"]] == [41.0, 45.0, 45.0]

    def test_a_normal_ramp_is_not_split(self):
        """Working up in weight is one exercise, not three."""
        store = session(unnamed(10, 40.0), unnamed(8, 50.0), unnamed(6, 60.0))
        assert len(labelling.blocks("2026-08-18", store)) == 1

    def test_another_date_is_untouched(self):
        store = session(unnamed(9, 70.0))
        assert labelling.blocks("2026-01-01", store) == []


class TestLabel:
    def test_labelling_names_every_set_in_the_block(self):
        store = session(unnamed(9, 70.0), unnamed(6, 70.0))
        result = labelling.label("2026-08-18", 1, "CABLE_CRUNCH", "CRUNCH", store)
        assert result["updated"] == 2
        named = [s for a in store["activities"].values() for s in a["sets"]]
        assert all(s["exercise"] == "CABLE_CRUNCH" for s in named)

    def test_an_invalid_exercise_is_refused(self):
        """
        A bad label would be written into history and then fail the next upload
        that used it — refusing now is cheaper than discovering it later.
        """
        store = session(unnamed(9, 70.0))
        result = labelling.label("2026-08-18", 1, "NOT_A_REAL_LIFT", "CRUNCH", store)
        assert result["updated"] == 0 and result["error"]

    def test_a_missing_block_is_reported_rather_than_guessed(self):
        store = session(unnamed(9, 70.0))
        result = labelling.label("2026-08-18", 9, "CABLE_CRUNCH", "CRUNCH", store)
        assert result["updated"] == 0 and "no block" in result["error"]
