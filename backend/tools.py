import sqlite3
import os
from db.geo_utils import haversine

DB_PATH = os.path.join(os.path.dirname(__file__), "db", "geoagent.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_population(lat: float, lng: float, radius_km: float) -> dict:
    """Get population within radius using Haversine distance."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT population, median_income, avg_age, lat, lng FROM demographics WHERE population > 0"
    ).fetchall()
    conn.close()

    # Filter by distance in Python
    nearby = [r for r in rows if haversine(lat, lng, r["lat"], r["lng"]) <= radius_km]

    total_pop = sum(r["population"] or 0 for r in nearby)
    incomes = [r["median_income"] for r in nearby if r["median_income"]]
    ages = [r["avg_age"] for r in nearby if r["avg_age"]]

    score = min(100, int(total_pop / 200))

    # Per-DA centroid data for map visualization
    nearby_areas = [
        {
            "lat": r["lat"],
            "lng": r["lng"],
            "population": r["population"] or 0,
            "median_income": r["median_income"] or 0,
        }
        for r in nearby
    ]

    return {
        "population": total_pop,
        "avg_median_income": round(sum(incomes) / len(incomes), 0) if incomes else 0,
        "avg_age": round(sum(ages) / len(ages), 1) if ages else 0,
        "areas_covered": len(nearby),
        "radius_km": radius_km,
        "score": score,
        "source": "statscan_census_2021",
        "nearby_areas": nearby_areas,
    }


def find_competitors(lat: float, lng: float, business_type: str, radius_km: float) -> dict:
    """Find competing businesses using Haversine distance."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT name, category, lat, lng FROM pois WHERE category = ?",
        (business_type,)
    ).fetchall()
    conn.close()

    # Calculate distance for each and filter
    competitors = []
    for r in rows:
        dist = haversine(lat, lng, r["lat"], r["lng"])
        if dist <= radius_km:
            competitors.append({
                "name": r["name"],
                "category": r["category"],
                "distance_m": round(dist * 1000, 0)
            })

    competitors.sort(key=lambda c: c["distance_m"])
    count = len(competitors)
    score = max(0, 100 - (count * 15))

    return {
        "competitors": competitors[:5],
        "total_count": count,
        "nearest_distance_m": competitors[0]["distance_m"] if competitors else None,
        "score": score,
        "source": "overture_maps"
    }


def get_median_income(lat: float, lng: float) -> dict:
    """Get median income from the nearest census dissemination area."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT median_income, population, avg_age, da_id, lat, lng FROM demographics WHERE median_income > 0"
    ).fetchall()
    conn.close()

    if not rows:
        return {"error": "No census data found for this location"}

    # Find the nearest dissemination area
    nearest = min(rows, key=lambda r: haversine(lat, lng, r["lat"], r["lng"]))

    income = nearest["median_income"]
    score = min(100, int(income / 800))

    return {
        "median_income": income,
        "population": nearest["population"],
        "avg_age": float(nearest["avg_age"]) if nearest["avg_age"] else 0,
        "da_id": nearest["da_id"],
        "score": score,
        "source": "statscan_census_2021"
    }


def get_nearby_roads(lat: float, lng: float, radius_km: float) -> dict:
    """Get road infrastructure info within radius using Haversine distance."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT road_name, road_class, speed_limit, lat, lng FROM roads"
    ).fetchall()
    conn.close()

    nearby = []
    for r in rows:
        dist = haversine(lat, lng, r["lat"], r["lng"])
        if dist <= radius_km:
            nearby.append({
                "road_name": r["road_name"],
                "road_class": r["road_class"],
                "speed_limit": r["speed_limit"],
                "distance_km": round(dist, 3),
            })

    nearby.sort(key=lambda x: x["distance_km"])

    # Count by class
    class_counts = {}
    for r in nearby:
        cls = r["road_class"]
        class_counts[cls] = class_counts.get(cls, 0) + 1

    # Find major roads (arterial/highway) — these drive foot/car traffic
    major_roads = [r for r in nearby if r["road_class"] in ("arterial", "highway")]
    major_roads.sort(key=lambda x: x["distance_km"])

    # Score: more arterials nearby = more traffic = better for retail
    arterial_count = class_counts.get("arterial", 0)
    highway_count = class_counts.get("highway", 0)
    score = min(100, arterial_count * 8 + highway_count * 5)

    return {
        "total_roads": len(nearby),
        "road_class_breakdown": class_counts,
        "major_roads_nearby": major_roads[:5],
        "nearest_arterial_km": major_roads[0]["distance_km"] if major_roads else None,
        "score": score,
        "source": "openstreetmap_overpass",
    }


def get_nearest_transit(lat: float, lng: float, radius_km: float) -> dict:
    """Find nearest transit stops (bus stations, train stations, LRT) from POI data."""
    conn = get_db_connection()
    transit_categories = (
        "bus_station", "bus_service", "light_rail_and_subway_stations", "train_station"
    )
    placeholders = ",".join("?" * len(transit_categories))
    rows = conn.execute(
        f"SELECT name, category, lat, lng FROM pois WHERE category IN ({placeholders})",
        transit_categories,
    ).fetchall()
    conn.close()

    nearby = []
    for r in rows:
        dist = haversine(lat, lng, r["lat"], r["lng"])
        if dist <= radius_km:
            nearby.append({
                "name": r["name"],
                "type": r["category"],
                "distance_m": round(dist * 1000, 0),
            })

    nearby.sort(key=lambda x: x["distance_m"])

    # Score based on transit accessibility
    if not nearby:
        score = 10
    elif nearby[0]["distance_m"] <= 200:
        score = 95
    elif nearby[0]["distance_m"] <= 500:
        score = 80
    elif nearby[0]["distance_m"] <= 1000:
        score = 60
    else:
        score = 30

    # Bonus for multiple stops
    score = min(100, score + len(nearby) * 3)

    return {
        "transit_stops": nearby[:10],
        "total_stops_in_radius": len(nearby),
        "nearest_stop_m": nearby[0]["distance_m"] if nearby else None,
        "score": score,
        "source": "overture_maps_pois",
    }


def check_zoning(lat: float, lng: float, business_type: str) -> dict:
    """Check zoning at a location and whether the business type is permitted."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT zone_code, zone_type, permitted_uses, lat, lng FROM zoning"
    ).fetchall()
    conn.close()

    if not rows:
        return {"error": "No zoning data available", "score": 50}

    # Find all zones within 0.5km — OSM data is coarse, so check a small area
    zones_nearby = []
    for r in rows:
        dist = haversine(lat, lng, r["lat"], r["lng"])
        if dist <= 0.5:
            zones_nearby.append({
                "zone_code": r["zone_code"],
                "zone_type": r["zone_type"],
                "permitted_uses": r["permitted_uses"].split(",") if r["permitted_uses"] else [],
                "distance_km": round(dist, 3),
            })

    # If nothing within 0.5km, use absolute nearest
    if not zones_nearby:
        nearest = min(rows, key=lambda r: haversine(lat, lng, r["lat"], r["lng"]))
        nearest_dist = haversine(lat, lng, nearest["lat"], nearest["lng"])
        zones_nearby = [{
            "zone_code": nearest["zone_code"],
            "zone_type": nearest["zone_type"],
            "permitted_uses": nearest["permitted_uses"].split(",") if nearest["permitted_uses"] else [],
            "distance_km": round(nearest_dist, 3),
        }]

    zones_nearby.sort(key=lambda x: x["distance_km"])

    # Map common business types to zoning categories
    business_to_zoning = {
        "coffee_shop": ["coffee_shop", "retail", "restaurant", "service"],
        "cafe": ["coffee_shop", "retail", "restaurant", "service"],
        "restaurant": ["restaurant", "retail", "service"],
        "bakery": ["retail", "restaurant", "coffee_shop", "service"],
        "gym": ["retail", "service", "entertainment"],
        "retail": ["retail", "service"],
        "office": ["office"],
        "bar": ["restaurant", "entertainment", "service"],
        "hotel": ["hotel", "service"],
    }

    required_uses = business_to_zoning.get(business_type, ["retail", "service"])

    # Check if ANY nearby zone permits the business (most permissive interpretation)
    best_zone = zones_nearby[0]
    is_permitted = False
    for z in zones_nearby:
        if any(use in z["permitted_uses"] for use in required_uses):
            best_zone = z
            is_permitted = True
            break

    # Summarize zone types in the area
    zone_types_nearby = list(set(z["zone_type"] for z in zones_nearby))

    # Score
    if is_permitted:
        score = 90
    elif "commercial" in zone_types_nearby or "mixed" in zone_types_nearby:
        score = 70  # Commercial zones nearby, likely OK
    elif best_zone["zone_type"] == "residential" and len(zones_nearby) == 1:
        score = 20  # Purely residential, probably not allowed
    elif best_zone["zone_type"] == "industrial":
        score = 15
    else:
        score = 40

    return {
        "zone_code": best_zone["zone_code"],
        "zone_type": best_zone["zone_type"],
        "permitted_uses": best_zone["permitted_uses"],
        "is_permitted": is_permitted,
        "zones_in_area": zone_types_nearby,
        "total_zones_nearby": len(zones_nearby),
        "distance_to_zone_center_km": best_zone["distance_km"],
        "score": score,
        "source": "openstreetmap_landuse",
    }


if __name__ == "__main__":
    print("--- get_population (downtown Kitchener, 2km) ---")
    print(get_population(43.45, -80.49, 2.0))
    print("\n--- find_competitors (coffee_shop, downtown Kitchener, 1km) ---")
    print(find_competitors(43.45, -80.49, "coffee_shop", 1.0))
    print("\n--- get_median_income (downtown Kitchener) ---")
    print(get_median_income(43.45, -80.49))
    print("\n--- get_nearby_roads (downtown Kitchener, 0.5km) ---")
    print(get_nearby_roads(43.45, -80.49, 0.5))
    print("\n--- get_nearest_transit (downtown Kitchener, 1km) ---")
    print(get_nearest_transit(43.45, -80.49, 1.0))
    print("\n--- check_zoning (downtown Kitchener, coffee_shop) ---")
    print(check_zoning(43.45, -80.49, "coffee_shop"))
