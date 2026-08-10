"""
Turning a start, a turnaround and a target duration into a drawn route.

Uses OpenStreetMap services that need no API key: Nominatim to turn place names
into coordinates, and OSRM's foot profile to follow actual paths. The foot
profile matters — it uses towpaths, park paths and footbridges that a driving
route ignores, which for canal-side running is the difference between the route
you run and a zigzag through the streets beside it.

The distance that comes back is measured along the real path, so it replaces
guesswork rather than dressing it up: ask for a turnaround, find out what it
actually costs, move it if that is wrong.

Both services are free public endpoints run on donated capacity. Nominatim asks
for one request per second and a real User-Agent, which this honours. Anything
heavier than occasional personal use should run its own instance.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request

NOMINATIM = "https://nominatim.openstreetmap.org/search"
OSRM = "https://router.project-osrm.org/route/v1/foot"
USER_AGENT = "garmin-workouts (personal running route planner)"
_last_call = [0.0]


def _get(url: str) -> dict | list:
    # Nominatim's usage policy is one request per second; be a good citizen.
    wait = 1.0 - (time.monotonic() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    _last_call[0] = time.monotonic()

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def geocode(place: str) -> tuple | None:
    """(lat, lon) for a place name, or None if it can't be found."""
    url = f"{NOMINATIM}?" + urllib.parse.urlencode(
        {"q": place, "format": "json", "limit": 1}
    )
    try:
        results = _get(url)
    except Exception:
        return None
    if not results:
        return None
    return float(results[0]["lat"]), float(results[0]["lon"])


def foot_route(points: list) -> dict | None:
    """
    Walk a path through `points` [(lat, lon), ...], following real paths.

    Returns the distance in km and the line to draw, or None if routing failed —
    never a straight-line fallback, because a straight line across a canal is
    not a route and would report a distance nobody can run.
    """
    if len(points) < 2:
        return None

    coords = ";".join(f"{lon},{lat}" for lat, lon in points)
    url = f"{OSRM}/{coords}?overview=full&geometries=geojson"
    try:
        payload = _get(url)
    except Exception:
        return None

    routes = payload.get("routes") or []
    if not routes:
        return None

    route = routes[0]
    line = [(lat, lon) for lon, lat in route["geometry"]["coordinates"]]
    return {
        "km": round(route["distance"] / 1000, 2),
        "minutes": round(route["duration"] / 60, 1),
        "line": line,
    }


OVERPASS = "https://overpass-api.de/api/interpreter"

# Named paths worth routing along rather than beside. A foot router asked to go
# from A to B takes the shortest walkable line, and beside a canal that is
# usually the road — right distance, wrong run.
PATH_QUERY = """
[out:json][timeout:25];
way(around:{radius},{lat},{lon})["highway"~"footway|path|cycleway|track"]["name"~"{pattern}",i];
out geom {limit};
"""


def path_points(near: tuple, pattern: str = "towpath|canal|riverside|greenway",
                radius: int = 1200, limit: int = 12) -> list:
    """
    Coordinates on named paths near a point, from OpenStreetMap.

    Used to pull a route onto the towpath instead of the road beside it. Place
    names geocode to street-level coordinates, so routing between them takes
    roads; a single point on the path itself is usually enough to fix that.
    """
    import urllib.request

    query = PATH_QUERY.format(
        radius=radius, lat=near[0], lon=near[1], pattern=pattern, limit=limit
    )
    request = urllib.request.Request(
        OVERPASS,
        data=urllib.parse.urlencode({"data": query}).encode(),
        headers={"User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.load(response)
    except Exception:
        return []

    found = []
    for way in payload.get("elements", []):
        geometry = way.get("geometry") or []
        if geometry:
            middle = geometry[len(geometry) // 2]
            found.append(
                {
                    "name": (way.get("tags") or {}).get("name", "path"),
                    "point": (middle["lat"], middle["lon"]),
                }
            )
    return found


def out_and_back(start: str, turnaround: str, via: list | None = None,
                 follow: str | None = None) -> dict | None:
    """
    A there-and-back route, measured along real paths.

    The return leg retraces the outward one rather than being routed separately,
    which is what actually happens on the ground and avoids OSRM returning a
    different way home that changes the total.
    """
    places = [start] + list(via or []) + [turnaround]
    located = []
    for place in places:
        point = geocode(place)
        if point is None:
            return None
        located.append((place, point))

    points = [p for _, p in located]
    snapped = []

    if follow:
        # Pull the line onto the named path near each end, so the route runs
        # along it rather than on the parallel road.
        for _, point in located:
            candidates = path_points(point, pattern=follow)
            if candidates:
                nearest = min(
                    candidates,
                    key=lambda c: (c["point"][0] - point[0]) ** 2
                    + (c["point"][1] - point[1]) ** 2,
                )
                snapped.append(nearest)
        if snapped:
            points = (
                [points[0]] + [s["point"] for s in snapped] + [points[-1]]
            )

    leg = foot_route(points)
    if leg is None:
        return None

    return {
        "places": located,
        "followed": [s["name"] for s in snapped],
        "leg_km": leg["km"],
        "total_km": round(leg["km"] * 2, 2),
        "line": leg["line"],
    }
