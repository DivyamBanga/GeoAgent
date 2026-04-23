"""Load road data from OpenStreetMap via the Overpass API into SQLite.

Downloads road segments for the Kitchener-Waterloo bounding box,
maps OSM highway types to our road_class scheme, and inserts into SQLite.

Usage:
    python load_roads.py
"""

import json
import sqlite3
import os
import urllib.request
import urllib.parse

DB_PATH = os.path.join(os.path.dirname(__file__), "geoagent.db")

# KW bounding box: south, west, north, east
KW_BBOX = "43.35,-80.60,43.55,-80.30"

# Map OSM highway tag values to our road_class
HIGHWAY_CLASS_MAP = {
    "motorway": "highway",
    "motorway_link": "highway",
    "trunk": "highway",
    "trunk_link": "highway",
    "primary": "arterial",
    "primary_link": "arterial",
    "secondary": "arterial",
    "secondary_link": "arterial",
    "tertiary": "collector",
    "tertiary_link": "collector",
    "residential": "residential",
    "unclassified": "residential",
    "living_street": "residential",
}

# Default speed limits (km/h) when OSM doesn't have one tagged
DEFAULT_SPEED = {
    "highway": 100,
    "arterial": 60,
    "collector": 50,
    "residential": 40,
}


def download_roads() -> list[dict]:
    """Query the Overpass API for roads in the KW area."""
    overpass_url = "https://overpass-api.de/api/interpreter"

    # Query for named roads with highway tags we care about
    query = f"""
    [out:json][timeout:90];
    way["highway"~"^(motorway|trunk|primary|secondary|tertiary|residential|unclassified|living_street)(_link)?$"]({KW_BBOX});
    out center tags;
    """

    print("Downloading road data from Overpass API...")
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    req = urllib.request.Request(overpass_url, data=data)
    req.add_header("User-Agent", "GeoAgent/1.0 (student project)")

    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    elements = result.get("elements", [])
    print(f"  Received {len(elements)} road segments")
    return elements


def parse_speed_limit(tags: dict) -> int | None:
    """Extract speed limit from OSM tags."""
    maxspeed = tags.get("maxspeed", "")
    if not maxspeed:
        return None
    # Handle common formats: "50", "60 km/h", "50;60"
    clean = maxspeed.split(";")[0].split(" ")[0]
    try:
        return int(clean)
    except ValueError:
        return None


def load_roads():
    """Download roads from Overpass API and insert into SQLite."""
    elements = download_roads()

    conn = sqlite3.connect(DB_PATH)

    # Clear existing road data before loading
    conn.execute("DELETE FROM roads")

    inserted = 0
    skipped = 0

    for el in elements:
        if el.get("type") != "way":
            continue

        tags = el.get("tags", {})
        center = el.get("center")
        if not center:
            skipped += 1
            continue

        highway_type = tags.get("highway", "")
        road_class = HIGHWAY_CLASS_MAP.get(highway_type)
        if not road_class:
            skipped += 1
            continue

        road_name = tags.get("name", "Unnamed Road")
        speed_limit = parse_speed_limit(tags) or DEFAULT_SPEED.get(road_class, 50)
        lat = center["lat"]
        lng = center["lon"]

        conn.execute(
            "INSERT INTO roads (road_name, road_class, speed_limit, lat, lng) VALUES (?, ?, ?, ?, ?)",
            (road_name, road_class, speed_limit, lat, lng),
        )
        inserted += 1

    conn.commit()
    conn.close()
    print(f"  Loaded {inserted} roads ({skipped} skipped)")

    # Print summary by class
    conn = sqlite3.connect(DB_PATH)
    print("\n  Road class breakdown:")
    for row in conn.execute(
        "SELECT road_class, COUNT(*) FROM roads GROUP BY road_class ORDER BY COUNT(*) DESC"
    ).fetchall():
        print(f"    {row[0]}: {row[1]}")
    conn.close()


if __name__ == "__main__":
    load_roads()
