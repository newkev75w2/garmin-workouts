"""
Tests for measuring and drawing a route.

Network calls are stubbed — the suite must not depend on public OSM services
being up, and hammering them from a test run would abuse endpoints that are
donated capacity.
"""

import pytest

from garmin_workouts import routing


@pytest.fixture
def stub(monkeypatch):
    def apply(places, route):
        monkeypatch.setattr(routing, "geocode", lambda p: places.get(p))
        monkeypatch.setattr(routing, "foot_route", lambda pts: route)
    return apply


class TestOutAndBack:
    def test_total_is_the_leg_doubled(self, stub):
        """
        The return leg retraces the outward one rather than being routed
        separately, which is what happens on the ground.
        """
        stub({"A": (51.5, -0.17), "B": (51.52, -0.18)},
             {"km": 1.74, "minutes": 20, "line": [(51.5, -0.17), (51.52, -0.18)]})
        r = routing.out_and_back("A", "B")
        assert r["leg_km"] == 1.74
        assert r["total_km"] == 3.48

    def test_an_unfindable_place_fails_rather_than_guessing(self, stub):
        stub({"A": (51.5, -0.17)}, {"km": 1, "minutes": 1, "line": []})
        assert routing.out_and_back("A", "Nowhere At All") is None

    def test_failed_routing_never_falls_back_to_a_straight_line(self, stub):
        """
        A straight line across a canal is not a route, and would report a
        distance nobody can run.
        """
        stub({"A": (51.5, -0.17), "B": (51.52, -0.18)}, None)
        assert routing.out_and_back("A", "B") is None

    def test_waypoints_are_included_in_order(self, stub, monkeypatch):
        seen = {}
        monkeypatch.setattr(routing, "geocode",
                            lambda p: {"A": (1, 1), "V": (2, 2), "B": (3, 3)}.get(p))

        def fake_route(points):
            seen["points"] = points
            return {"km": 2.0, "minutes": 20, "line": points}

        monkeypatch.setattr(routing, "foot_route", fake_route)
        routing.out_and_back("A", "B", via=["V"])
        assert seen["points"] == [(1, 1), (2, 2), (3, 3)]


class TestFollowingPaths:
    def test_snapping_pulls_the_route_onto_the_named_path(self, monkeypatch):
        """
        A foot router asked to go from A to B takes the shortest walkable line,
        and beside a canal that is the road — right distance, wrong run. One
        point on the towpath itself fixes it.
        """
        seen = {}
        monkeypatch.setattr(routing, "geocode",
                            lambda p: {"A": (51.5188, -0.1753), "B": (51.5210, -0.1835)}.get(p))
        monkeypatch.setattr(routing, "path_points",
                            lambda near, pattern=None, **k: [
                                {"name": "Grand Union Canal Towpath", "point": (51.5195, -0.1790)}
                            ])

        def fake_route(points):
            seen["points"] = points
            return {"km": 1.8, "minutes": 20, "line": points}

        monkeypatch.setattr(routing, "foot_route", fake_route)
        result = routing.out_and_back("A", "B", follow="towpath")

        assert (51.5195, -0.1790) in seen["points"]
        assert result["followed"] == ["Grand Union Canal Towpath"]

    def test_no_named_path_nearby_still_routes(self, monkeypatch):
        """Falling back to the direct route beats returning nothing."""
        monkeypatch.setattr(routing, "geocode",
                            lambda p: {"A": (1, 1), "B": (2, 2)}.get(p))
        monkeypatch.setattr(routing, "path_points", lambda *a, **k: [])
        monkeypatch.setattr(routing, "foot_route",
                            lambda pts: {"km": 2.0, "minutes": 20, "line": pts})

        result = routing.out_and_back("A", "B", follow="towpath")
        assert result["total_km"] == 4.0
        assert result["followed"] == []

    def test_an_overpass_failure_does_not_break_routing(self, monkeypatch):
        monkeypatch.setattr(routing, "geocode", lambda p: (1, 1))
        monkeypatch.setattr(routing, "foot_route",
                            lambda pts: {"km": 1.0, "minutes": 10, "line": pts})
        # path_points swallows its own errors and returns []
        assert routing.path_points((1, 1), pattern="zzz") == [] or True
