"""
Tests for knowing what the gym actually has.

The distinction that matters is between "not there" and "not recorded" —
treating an unrecorded machine as absent is as unhelpful as prescribing one the
gym does not own.
"""

import json

import pytest

from garmin_workouts import equipment


@pytest.fixture(autouse=True)
def temp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(equipment, "EQUIPMENT_PATH", tmp_path / "equipment.json")


class TestAvailability:
    def test_recorded_kit_is_available(self):
        equipment.save({"gym": "X", "has": ["leg extension"], "lacks": [], "notes": ""})
        assert equipment.available("leg extension") is True

    def test_recorded_absence_is_absence(self):
        equipment.save({"gym": "X", "has": [], "lacks": ["sled"], "notes": ""})
        assert equipment.available("sled") is False

    def test_unrecorded_kit_is_unknown_not_absent(self):
        """None is a third answer and must not collapse into False."""
        equipment.save({"gym": "X", "has": ["cable"], "lacks": [], "notes": ""})
        assert equipment.available("hack squat") is None

    def test_matching_ignores_case_and_padding(self):
        equipment.save({"gym": "X", "has": ["  Leg Press "], "lacks": [], "notes": ""})
        assert equipment.available("leg press") is True

    def test_an_empty_file_claims_nothing(self):
        assert equipment.available("anything") is None


class TestUnusedKit:
    def test_kit_not_trained_recently_is_surfaced(self):
        """This is the variety prompt — where a session can change shape."""
        equipment.save({"gym": "X", "has": ["leg extension", "cable"],
                        "lacks": [], "notes": ""})
        store = {"activities": {"1": {"date": "2026-08-18", "sets": [
            {"exercise": "CABLE_CRUNCH"}]}}}
        assert equipment.unused_kit(store) == ["leg extension"]

    def test_nothing_recorded_means_no_suggestions(self):
        assert equipment.unused_kit({"activities": {}}) == []


class TestLimits:
    def test_a_weight_above_the_gyms_heaviest_is_flagged(self):
        """
        52kg on a dumbbell press where the heaviest dumbbell is 50kg is not a
        strong lift, it is the pair total logged as one — and mixed conventions
        corrupt every verdict for that exercise.
        """
        equipment.save({"gym": "X", "has": [], "lacks": [],
                        "limits": {"dumbbell_kg": 50}, "notes": "", "source": ""})
        note = equipment.exceeds_limit("DUMBBELL_PUSH_PRESS", 52.0)
        assert note and "pair total" in note

    def test_a_plausible_weight_passes(self):
        equipment.save({"gym": "X", "has": [], "lacks": [],
                        "limits": {"dumbbell_kg": 50}, "notes": "", "source": ""})
        assert equipment.exceeds_limit("DUMBBELL_BENCH_PRESS", 32.0) is None

    def test_barbell_work_is_not_judged_against_dumbbell_limits(self):
        equipment.save({"gym": "X", "has": [], "lacks": [],
                        "limits": {"dumbbell_kg": 50}, "notes": "", "source": ""})
        assert equipment.exceeds_limit("BARBELL_SQUAT", 120.0) is None

    def test_no_recorded_limit_means_no_opinion(self):
        equipment.save({"gym": "X", "has": [], "lacks": [], "limits": {},
                        "notes": "", "source": ""})
        assert equipment.exceeds_limit("DUMBBELL_PUSH_PRESS", 200.0) is None
