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
