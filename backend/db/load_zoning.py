"""Load zoning data from the City of Kitchener Open Data portal into SQLite.

Uses the ArcGIS REST API to query the Zoning By-law feature layer.
Falls back to City of Waterloo if needed.

Usage:
    python load_zoning.py
"""

import json
import sqlite3
import os
import urllib.request
import urllib.parse

DB_PATH = os.path.join(os.path.dirname(__file__), "geoagent.db")

# City of Kitchener ArcGIS feature service endpoints to try
ZONING_ENDPOINTS = [
    # City of Kitchener - Zoning By-law
    "https://services1.arcgis.com/GM6WaPA5o5VaP9Hj/arcgis/rest/services/Zoning/FeatureServer/0/query",
    "https://services1.arcgis.com/GM6WaPA5o5VaP9Hj/arcgis/rest/services/Zoning_By_law/FeatureServer/0/query",
    "https://services1.arcgis.com/GM6WaPA5o5VaP9Hj/arcgis/rest/services/ZoningBylaw/FeatureServer/0/query",
    # Region of Waterloo
    "https://services1.arcgis.com/GM6WaPA5o5VaP9Hj/arcgis/rest/services/Zoning_Bylaw_2019_141/FeatureServer/0/query",
]

# Map common Kitchener zone codes to our zone_type and permitted_uses
ZONE_TYPE_MAP = {
    # Residential
    "RES": ("residential", "single_family,duplex,townhouse"),
    "R-1": ("residential", "single_family"),
    "R-2": ("residential", "single_family,duplex"),
    "R-3": ("residential", "single_family,duplex,townhouse"),
    "R-4": ("residential", "single_family,duplex,townhouse,apartment"),
    "R-5": ("residential", "apartment,townhouse"),
    "R-6": ("residential", "apartment,high_density"),
    "R-7": ("residential", "apartment,high_density"),
    "R-8": ("residential", "apartment,mixed"),
    "R-9": ("residential", "apartment"),
    # Commercial
    "COM": ("commercial", "retail,office,restaurant,coffee_shop,service"),
    "C-1": ("commercial", "retail,office,restaurant,coffee_shop,service,convenience"),
    "C-2": ("commercial", "retail,office,restaurant,coffee_shop,service,entertainment"),
    "C-3": ("commercial", "retail,office,restaurant,coffee_shop,big_box"),
    "C-4": ("commercial", "retail,office,restaurant,coffee_shop,auto_service"),
    "C-5": ("commercial", "retail,office,restaurant,coffee_shop,hotel"),
    "C-6": ("commercial", "retail,office,restaurant,coffee_shop,service"),
    "C-7": ("commercial", "retail,office,service,auto_commercial"),
    "C-9": ("commercial", "office,institutional"),
    # Mixed Use
    "MIX": ("mixed", "retail,office,restaurant,coffee_shop,residential,service"),
    "MU-1": ("mixed", "retail,office,restaurant,coffee_shop,residential"),
    "MU-2": ("mixed", "retail,office,restaurant,coffee_shop,residential,entertainment"),
    "MU-3": ("mixed", "retail,office,restaurant,coffee_shop,residential"),
    "MIX-1": ("mixed", "retail,office,restaurant,coffee_shop,residential"),
    "MIX-2": ("mixed", "retail,office,restaurant,coffee_shop,residential"),
    "MIX-3": ("mixed", "retail,office,restaurant,coffee_shop,residential"),
    # Industrial
    "IND": ("industrial", "manufacturing,warehouse,logistics"),
    "M-1": ("industrial", "light_manufacturing,warehouse"),
    "M-2": ("industrial", "manufacturing,warehouse,logistics"),
    "M-3": ("industrial", "heavy_manufacturing,industrial"),
    "EMP": ("industrial", "employment,office,light_manufacturing"),
    # Institutional
    "INS": ("institutional", "school,hospital,government,community"),
    "I-1": ("institutional", "school,hospital,government,community,worship"),
    "I-2": ("institutional", "hospital,government,major_institutional"),
    # Open Space
    "OS": ("open_space", "park,recreation"),
    "P-1": ("open_space", "park,conservation"),
    "P-2": ("open_space", "park,recreation,community"),
    # Downtown
    "D-1": ("commercial", "retail,office,restaurant,coffee_shop,residential,entertainment,hotel"),
    "D-2": ("mixed", "retail,office,restaurant,coffee_shop,residential,entertainment"),
    "D-3": ("mixed", "retail,office,restaurant,coffee_shop,residential"),
    "D-4": ("mixed", "retail,office,restaurant,coffee_shop,residential,institutional"),
    "D-5": ("mixed", "retail,office,restaurant,coffee_shop,residential"),
    "D-6": ("mixed", "retail,office,restaurant,coffee_shop,residential"),
    # Urban Growth Centre
    "UGC": ("mixed", "retail,office,restaurant,coffee_shop,residential,high_density"),
}


def classify_zone(zone_code: str) -> tuple[str, str]:
    """Classify a zone code into zone_type and permitted_uses."""
    code_upper = zone_code.upper().strip()

    # Direct match
    if code_upper in ZONE_TYPE_MAP:
        return ZONE_TYPE_MAP[code_upper]

    # Prefix match (e.g., "R-1S.1" -> "R-1")
    for prefix in sorted(ZONE_TYPE_MAP.keys(), key=len, reverse=True):
        if code_upper.startswith(prefix):
            return ZONE_TYPE_MAP[prefix]

    # Fallback by first character
    first = code_upper[0] if code_upper else ""
    if first == "R":
        return ("residential", "residential")
    elif first == "C":
        return ("commercial", "retail,office,restaurant,coffee_shop,service")
    elif first in ("M", "E"):
        return ("industrial", "manufacturing,warehouse")
    elif first == "I":
        return ("institutional", "school,hospital,government")
    elif first in ("P", "O"):
        return ("open_space", "park,recreation")
    elif first == "D":
        return ("commercial", "retail,office,restaurant,coffee_shop,residential")

    return ("other", "unknown")


def try_download_zoning(url: str) -> list[dict] | None:
    """Try to download zoning features from an ArcGIS REST endpoint."""
    params = {
        "where": "1=1",
        "outFields": "*",
        "outSR": "4326",
        "f": "geojson",
        "resultRecordCount": 5000,
    }

    full_url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(full_url)
    req.add_header("User-Agent", "GeoAgent/1.0 (student project)")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        features = data.get("features", [])
        if features:
            return features
    except Exception as e:
        print(f"  Endpoint failed: {e}")

    return None


def download_zoning() -> list[dict]:
    """Try multiple endpoints to download zoning data."""
    for endpoint in ZONING_ENDPOINTS:
        print(f"  Trying: {endpoint}")
        features = try_download_zoning(endpoint)
        if features:
            print(f"  Got {len(features)} features")
            return features

    print("  All ArcGIS endpoints failed. Using Overpass API for land use data...")
    return download_zoning_from_osm()


def download_zoning_from_osm() -> list[dict]:
    """Fallback: get land use/zoning data from OpenStreetMap via Overpass API."""
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = """
    [out:json][timeout:90];
    (
      way["landuse"~"^(commercial|retail|residential|industrial|institutional|farmland)$"](43.35,-80.60,43.55,-80.30);
      relation["landuse"~"^(commercial|retail|residential|industrial|institutional|farmland)$"](43.35,-80.60,43.55,-80.30);
    );
    out center tags;
    """

    print("  Downloading land use data from Overpass API...")
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    req = urllib.request.Request(overpass_url, data=data)
    req.add_header("User-Agent", "GeoAgent/1.0 (student project)")

    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    elements = result.get("elements", [])
    print(f"  Received {len(elements)} land use areas")

    # Convert OSM elements to a common format
    features = []
    landuse_to_zone = {
        "commercial": ("COM", "commercial", "retail,office,restaurant,coffee_shop,service"),
        "retail": ("C-1", "commercial", "retail,office,restaurant,coffee_shop,service"),
        "residential": ("RES", "residential", "single_family,duplex,townhouse,apartment"),
        "industrial": ("IND", "industrial", "manufacturing,warehouse,logistics"),
        "institutional": ("INS", "institutional", "school,hospital,government,community"),
        "farmland": ("OS", "open_space", "agriculture"),
    }

    for el in elements:
        center = el.get("center")
        if not center:
            continue

        tags = el.get("tags", {})
        landuse = tags.get("landuse", "")
        zone_info = landuse_to_zone.get(landuse)
        if not zone_info:
            continue

        zone_code, zone_type, permitted_uses = zone_info
        name = tags.get("name", "")

        features.append({
            "zone_code": zone_code,
            "zone_type": zone_type,
            "permitted_uses": permitted_uses,
            "name": name,
            "lat": center["lat"],
            "lng": center["lon"],
        })

    return features


def load_zoning():
    """Download zoning data and insert into SQLite."""
    raw_features = download_zoning()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM zoning")

    inserted = 0

    for feature in raw_features:
        # Handle ArcGIS GeoJSON format
        if "geometry" in feature:
            props = feature.get("properties", {})
            geom = feature["geometry"]

            # Get zone code from properties (try common field names)
            zone_code = (
                props.get("ZONE_CODE")
                or props.get("ZoneCode")
                or props.get("ZONE")
                or props.get("Zone")
                or props.get("ZONECODE")
                or props.get("zone_code")
                or props.get("ZONING")
                or props.get("Zoning")
                or "unknown"
            )

            zone_type, permitted_uses = classify_zone(str(zone_code))

            # Get centroid from geometry
            if geom["type"] == "Point":
                lng, lat = geom["coordinates"]
            elif geom["type"] == "Polygon":
                coords = geom["coordinates"][0]
                lat = sum(c[1] for c in coords) / len(coords)
                lng = sum(c[0] for c in coords) / len(coords)
            elif geom["type"] == "MultiPolygon":
                # Use first polygon's centroid
                coords = geom["coordinates"][0][0]
                lat = sum(c[1] for c in coords) / len(coords)
                lng = sum(c[0] for c in coords) / len(coords)
            else:
                continue

            conn.execute(
                "INSERT INTO zoning (zone_code, zone_type, permitted_uses, lat, lng) VALUES (?, ?, ?, ?, ?)",
                (str(zone_code), zone_type, permitted_uses, lat, lng),
            )
            inserted += 1

        # Handle pre-processed OSM format
        elif "zone_code" in feature:
            conn.execute(
                "INSERT INTO zoning (zone_code, zone_type, permitted_uses, lat, lng) VALUES (?, ?, ?, ?, ?)",
                (
                    feature["zone_code"],
                    feature["zone_type"],
                    feature["permitted_uses"],
                    feature["lat"],
                    feature["lng"],
                ),
            )
            inserted += 1

    conn.commit()
    conn.close()
    print(f"  Loaded {inserted} zoning areas")

    # Print summary
    conn = sqlite3.connect(DB_PATH)
    print("\n  Zone type breakdown:")
    for row in conn.execute(
        "SELECT zone_type, COUNT(*) FROM zoning GROUP BY zone_type ORDER BY COUNT(*) DESC"
    ).fetchall():
        print(f"    {row[0]}: {row[1]}")
    conn.close()


if __name__ == "__main__":
    load_zoning()
