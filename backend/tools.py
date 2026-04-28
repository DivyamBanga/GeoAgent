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


if __name__ == "__main__":
    print("--- get_population (downtown Kitchener, 2km) ---")
    print(get_population(43.45, -80.49, 2.0))
    print("\n--- find_competitors (coffee_shop, downtown Kitchener, 1km) ---")
    print(find_competitors(43.45, -80.49, "coffee_shop", 1.0))
    print("\n--- get_median_income (downtown Kitchener) ---")
    print(get_median_income(43.45, -80.49))
