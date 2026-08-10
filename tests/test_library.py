"""
Tests for telling real workouts from drafts.

Getting this wrong overwrites a session the athlete actually did, so the tests
lean on the failure direction: an unstamped file whose status cannot be
established must never be treated as disposable.
"""

import pytest

from garmin_workouts import library


@pytest.fixture
def workouts(tmp_path, monkeypatch):
    monkeypatch.setattr(library, "WORKOUTS_DIR", tmp_path)
    monkeypatch.setattr(library.history, "load", lambda: [])

    def write(stem, name):
        path = tmp_path / f"{stem}.py"
        path.write_text(f'WORKOUT = {{"name": "{name}", "exercises": []}}\n')
        return path

    return write


class TestStamping:
    def test_a_stamp_survives_a_round_trip(self, workouts):
        path = workouts("chest_abs_1", "Chest & Abs 1")
        assert library.stamp_of(path) is None
        library.mark_uploaded(path, "2026-08-10T09:00:00+00:00")
        assert library.stamp_of(path) == "2026-08-10T09:00:00+00:00"

    def test_stamping_twice_does_not_duplicate_it(self, workouts):
        path = workouts("legs_1", "Legs 1")
        library.mark_uploaded(path, "2026-08-01T00:00:00+00:00")
        library.mark_uploaded(path, "2026-08-10T00:00:00+00:00")
        assert path.read_text().count("UPLOADED") == 1
        assert library.stamp_of(path) == "2026-08-10T00:00:00+00:00"

    def test_the_workout_still_loads_after_stamping(self, workouts):
        from garmin_workouts import workout as wk

        path = workouts("legs_2", "Legs 2")
        library.mark_uploaded(path)
        assert wk.load_workout(str(path))["name"] == "Legs 2"


class TestStatus:
    def test_a_stamped_file_is_uploaded(self, workouts):
        path = workouts("legs_1", "Legs 1")
        library.mark_uploaded(path)
        assert library.local_workouts()[0]["status"] == "uploaded"

    def test_an_unstamped_file_is_a_draft(self, workouts):
        workouts("legs_1", "Legs 1")
        assert library.local_workouts()[0]["status"] == "draft"

    def test_the_upload_log_still_counts_for_older_files(self, workouts, monkeypatch):
        workouts("legs_1", "Legs 1")
        monkeypatch.setattr(library.history, "load",
                            lambda: [{"file": "workouts/legs_1.py"}])
        assert library.local_workouts()[0]["status"] == "uploaded"

    def test_garmin_is_the_backstop_for_files_this_tool_never_saw(self, workouts, monkeypatch):
        """
        A real log had "Chest & Shoulders 1" saved in Garmin with no local
        record at all — treating it as a draft would have overwritten it.
        """
        workouts("chest_shoulders_1", "Chest & Shoulders 1")
        monkeypatch.setattr(library, "remote_names", lambda client=None: {"Chest & Shoulders 1"})
        assert library.local_workouts(check_remote=True)[0]["status"] == "uploaded"

    def test_an_unreachable_garmin_yields_unknown_not_draft(self, workouts, monkeypatch):
        """When the alternative is destroying work, don't guess."""
        workouts("legs_1", "Legs 1")
        monkeypatch.setattr(library, "remote_names", lambda client=None: None)
        assert library.local_workouts(check_remote=True)[0]["status"] == "unknown"


class TestTargetPath:
    def test_a_draft_is_reused_rather_than_numbered_again(self, workouts):
        workouts("legs_1", "Legs 1")
        path, reused = library.target_path("legs")
        assert reused is True
        assert path.name == "legs_1.py"

    def test_an_uploaded_file_is_never_overwritten(self, workouts):
        library.mark_uploaded(workouts("legs_1", "Legs 1"))
        path, reused = library.target_path("legs")
        assert reused is False
        assert path.name == "legs_2.py"

    def test_an_unknown_file_is_left_alone_too(self, workouts, monkeypatch):
        workouts("legs_1", "Legs 1")
        entries = [{"file": "legs_1.py", "status": "unknown", "path": None}]
        path, reused = library.target_path("legs", entries)
        assert reused is False

    def test_a_new_pairing_starts_at_one(self, workouts):
        library.mark_uploaded(workouts("legs_1", "Legs 1"))
        path, reused = library.target_path("chest_shoulders")
        assert path.name == "chest_shoulders_1.py"
        assert reused is False
