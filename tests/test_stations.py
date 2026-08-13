"""
Tests for keeping a workout in one place at a time.

A workout that reads fine on paper can be miserable to run: bench, bench, cable,
bench means walking away from a bench mid-session and finding it taken.
"""

from garmin_workouts import stations


def ex(*names):
    return [{"name": n} for n in names]


class TestStationDetection:
    def test_equipment_comes_from_the_name_not_the_category(self):
        """
        Garmin's categories describe the movement, not the kit — BENCH_PRESS
        covers a barbell on a flat bench and a dumbbell press alike.
        """
        assert stations.station_of("CABLE_CROSSOVER") == "cable"
        assert stations.station_of("DUMBBELL_BENCH_PRESS") == "bench"
        assert stations.station_of("BARBELL_SHRUG") == "barbell"
        assert stations.station_of("HANGING_LEG_RAISE") == "bar"
        assert stations.station_of("PLANK") == "floor"

    def test_cable_wins_over_the_movement_pattern(self):
        """A cable pulldown is a cable station, not a pull-up bar."""
        assert stations.station_of("CLOSE_GRIP_LAT_PULLDOWN") == "cable"
        assert stations.station_of("TRICEPS_PRESSDOWN") == "cable"

    def test_an_unknown_exercise_is_not_forced_into_a_station(self):
        assert stations.station_of("SOMETHING_INVENTED") == "free"


class TestRevisits:
    def test_returning_to_a_station_is_flagged(self):
        found = stations.revisits(ex(
            "DUMBBELL_BENCH_PRESS", "CABLE_CROSSOVER", "DUMBBELL_FLYE"
        ))
        assert [f["station"] for f in found] == ["bench"]

    def test_passing_through_each_station_once_is_fine(self):
        """Moving through stations is unavoidable; coming back is the problem."""
        assert stations.revisits(ex(
            "DUMBBELL_BENCH_PRESS", "DUMBBELL_FLYE", "CABLE_CROSSOVER", "PLANK"
        )) == []

    def test_consecutive_exercises_on_one_station_are_not_revisits(self):
        assert stations.revisits(ex(
            "CABLE_CROSSOVER", "CABLE_CROSSOVER", "TRICEPS_PRESSDOWN"
        )) == []


class TestGrouping:
    def test_grouping_removes_the_walking(self):
        grouped = stations.group_by_station(ex(
            "DUMBBELL_BENCH_PRESS", "CABLE_CROSSOVER", "DUMBBELL_FLYE"
        ))
        assert stations.revisits(grouped) == []

    def test_the_opening_exercise_still_opens(self):
        """
        Heaviest compounds belong first, while the lifter is fresh — grouping
        must not reshuffle the training order to save a walk.
        """
        grouped = stations.group_by_station(ex(
            "BARBELL_BENCH_PRESS", "CABLE_CROSSOVER", "DUMBBELL_FLYE"
        ))
        assert grouped[0]["name"] == "BARBELL_BENCH_PRESS"

    def test_nothing_is_lost_or_duplicated(self):
        original = ex("A_CABLE_ROW", "PLANK", "DUMBBELL_BENCH_PRESS", "CABLE_CROSSOVER")
        grouped = stations.group_by_station(original)
        assert sorted(e["name"] for e in grouped) == sorted(e["name"] for e in original)
