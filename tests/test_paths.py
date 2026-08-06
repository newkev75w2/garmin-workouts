"""
Tests for where the tool keeps its data.

The bug these guard against is quiet and bad: resolving data paths relative to
the package meant a pip-installed copy would write performance.json, history.json
and the Garmin session token into site-packages.
"""

import importlib

from garmin_workouts import paths


class TestDataHome:
    def test_env_var_wins(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GARMIN_WORKOUTS_HOME", str(tmp_path / "elsewhere"))
        importlib.reload(paths)
        assert paths.data_home() == tmp_path / "elsewhere"

    def test_a_checkout_keeps_using_the_files_beside_it(self, monkeypatch):
        """An existing clone must not suddenly look somewhere new for its data."""
        monkeypatch.delenv("GARMIN_WORKOUTS_HOME", raising=False)
        importlib.reload(paths)
        home = paths.data_home()
        assert (home / ".git").exists() or (home / "pyproject.toml").exists()

    def test_the_directory_is_created_on_demand(self, tmp_path, monkeypatch):
        target = tmp_path / "fresh" / "nested"
        monkeypatch.setenv("GARMIN_WORKOUTS_HOME", str(target))
        importlib.reload(paths)
        assert paths.data_home().is_dir()

    def test_every_data_file_sits_under_one_home(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GARMIN_WORKOUTS_HOME", str(tmp_path))
        importlib.reload(paths)
        for path in (paths.performance_path(), paths.history_path(), paths.token_store()):
            assert path.parent == tmp_path
