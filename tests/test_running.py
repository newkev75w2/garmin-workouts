"""
Tests for running intensity classification.

The thing this has to get right is the grey zone: running that is hard enough
to cost recovery but not hard enough to drive VO2max. It is the most common way
to train consistently and improve slowly, and it does not feel like a mistake,
so the analysis has to name it rather than just report kilometres.
"""

from garmin_workouts import running


class TestZones:
    def test_effort_is_relative_to_max_heart_rate(self):
        assert running.zone_for(140, 210) == "Z1 recovery"   # 67%
        assert running.zone_for(159, 210) == "Z2 easy"       # 76%
        assert running.zone_for(175, 210) == "Z3 moderate"   # 83%
        assert running.zone_for(191, 210) == "Z4 threshold"  # 91%
        assert running.zone_for(200, 210) == "Z5 vo2max"     # 95%

    def test_missing_heart_rate_is_unzoned_rather_than_guessed(self):
        assert running.zone_for(None, 210) is None
        assert running.zone_for(159, None) is None

    def test_max_hr_comes_from_observed_data(self):
        """
        220-age is a population average with ~10bpm of spread. The highest value
        actually recorded is a better individual estimate.
        """
        runs = {"a": {"max_hr": 195}, "b": {"max_hr": 211}, "c": {"max_hr": None}}
        assert running.observed_max_hr(runs) == 211

    def test_no_heart_rate_data_at_all_yields_no_ceiling(self):
        assert running.observed_max_hr({"a": {"max_hr": None}}) is None


class TestAdvice:
    def _dist(self, easy, grey, hard, km=60, days=90):
        total = easy + grey + hard
        return {
            "runs": total, "easy": easy, "grey": grey, "hard": hard, "km": km,
            "days": days, "minutes": 300, "max_hr": 210, "unzoned": 0,
            "easy_share": easy / total, "grey_share": grey / total, "buckets": {},
        }

    def test_flags_a_grey_zone_heavy_week(self):
        notes = running.advice(self._dist(easy=1, grey=4, hard=4))
        assert any("grey zone" in n for n in notes)

    def test_flags_too_little_easy_running(self):
        notes = running.advice(self._dist(easy=1, grey=4, hard=4))
        assert any("genuinely easy" in n for n in notes)

    def test_flags_no_hard_work_at_all(self):
        notes = running.advice(self._dist(easy=9, grey=1, hard=0))
        assert any("intervals" in n for n in notes)

    def test_a_polarised_distribution_draws_no_complaint(self):
        notes = running.advice(self._dist(easy=16, grey=1, hard=3, km=300))
        assert notes == ["Distribution looks reasonable — keep it there."]

    def test_low_volume_is_called_out_as_the_real_limit(self):
        notes = running.advice(self._dist(easy=8, grey=1, hard=2, km=30))
        assert any("consistency matters more" in n for n in notes)

    def test_no_runs_means_no_opinion(self):
        assert "sync" in running.advice({})[0].lower()


class TestDistanceFromDuration:
    def test_duration_converts_at_the_given_pace(self):
        d = running.distance_for(27, pace_min_per_km=6.9167)
        assert d["km"] == 3.9

    def test_out_and_back_is_half_the_time(self):
        """
        The point of out-and-back is that it needs no distance at all — run half
        the time out and turn round, which self-corrects if the pace drifts.
        """
        d = running.distance_for(30, pace_min_per_km=7.0)
        assert d["out_and_back_minutes"] == 15
        assert d["out_and_back_km"] == round(30 / 7 / 2, 1)

    def test_no_pace_on_record_yields_no_invented_distance(self, monkeypatch):
        monkeypatch.setattr(running, "pace_for", lambda *a, **k: None)
        assert running.distance_for(30)["km"] is None


class TestRouteLink:
    def test_places_are_url_encoded(self):
        url = running.route_link("Paddington Basin, London", "Little Venice")
        assert "Paddington+Basin%2C+London" in url
        assert "Little+Venice" in url

    def test_walking_mode_is_used(self):
        """
        Driving directions ignore towpaths and footpaths, which is exactly where
        these runs go.
        """
        assert "travelmode=walking" in running.route_link("a", "b")
