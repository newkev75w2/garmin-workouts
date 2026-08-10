"""
Drawing a route onto a real map, as a local page.

Written to disk and opened in a browser rather than shown inline: map tiles come
from openstreetmap.org, and the sandboxes that render inline content block every
external host, so an inline version would be a page of empty grey squares.
"""

from __future__ import annotations

import html
import json
import webbrowser
from pathlib import Path

from .paths import data_home

OUT_DIR = data_home() / "routes"

PAGE = """<!doctype html>
<meta charset="utf-8">
<title>{title}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
  body {{ font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         margin: 0; }}
  header {{ padding: .9rem 1.1rem; border-bottom: 1px solid #ddd; }}
  h1 {{ font-size: 1.05rem; margin: 0 0 .2rem; }}
  .sub {{ color: #555; font-size: .9rem; }}
  #map {{ height: calc(100vh - 5.2rem); }}
</style>
<header>
  <h1>{title}</h1>
  <div class="sub">{subtitle}</div>
</header>
<div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
  const line = {line};
  const map = L.map('map');
  L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    maxZoom: 19, attribution: '&copy; OpenStreetMap contributors'
  }}).addTo(map);
  const path = L.polyline(line, {{ weight: 5, opacity: .85 }}).addTo(map);
  map.fitBounds(path.getBounds(), {{ padding: [30, 30] }});
  {markers}
</script>
"""


def draw(route: dict, title: str, subtitle: str, open_browser: bool = True) -> Path:
    """Write the route to a local page and open it."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    markers = []
    for name, (lat, lon) in route["places"]:
        label = html.escape(name).replace("'", "\\'")
        markers.append(
            f"L.marker([{lat}, {lon}]).addTo(map).bindPopup('{label}');"
        )

    out = OUT_DIR / "route.html"
    out.write_text(
        PAGE.format(
            title=html.escape(title),
            subtitle=html.escape(subtitle),
            line=json.dumps(route["line"]),
            markers="\n  ".join(markers),
        ),
        encoding="utf-8",
    )
    if open_browser:
        webbrowser.open(out.as_uri())
    return out
