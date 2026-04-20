# Hardcoded data for now. We'll replace with PostGIS in Phase 3.
MOCK_DATA = {
    "kitchener_downtown": {"population": 12500, "area": "Downtown Kitchener"},
    "kitchener_dtr": {"population": 8200, "area": "DTK - Innovation District"},
    "waterloo_uptown": {"population": 15000, "area": "Uptown Waterloo"},
}

def get_population(lat: float, lng: float, radius_km: float) -> dict:
    """Get population within a radius of a point. Returns mock data for now."""
    # Simple mock: pick closest area based on lat
    if lat > 43.47:
        data = MOCK_DATA["waterloo_uptown"]
    elif lat >= 43.45:
        data = MOCK_DATA["kitchener_downtown"]
    else:
        data = MOCK_DATA["kitchener_dtr"]

    population = data["population"]

    # Score: 0-100 based on population size
    # <5k = low, 5-10k = moderate, >10k = high
    if population >= 10000:
        score = min(100, 60 + (population - 10000) // 250)
    elif population >= 5000:
        score = 30 + (population - 5000) // 167
    else:
        score = max(0, population // 167)

    return {
        "population": population,
        "area_name": data["area"],
        "radius_km": radius_km,
        "score": score,
        "source": "mock_data"
    }

MOCK_COMPETITORS = [
    {"name": "Starbucks", "lat": 43.451, "lng": -80.492, "distance_m": 200},
    {"name": "Williams Fresh Cafe", "lat": 43.449, "lng": -80.488, "distance_m": 450},
    {"name": "Balzac's Coffee", "lat": 43.453, "lng": -80.495, "distance_m": 600},
]

MOCK_INCOME = {
    "kitchener_downtown": {"median_income": 52000, "avg_household_spend": 4200},
    "waterloo_uptown": {"median_income": 68000, "avg_household_spend": 5100},
}

def find_competitors(lat: float, lng: float, business_type: str, radius_km: float) -> dict:
    """Find competing businesses near a location."""
    # Filter mock competitors within radius (simplified)
    nearby = [c for c in MOCK_COMPETITORS if c["distance_m"] < radius_km * 1000]
    count = len(nearby)

    # Score: fewer competitors = higher score (less saturation)
    # 0 competitors = 95, 1 = 80, 2 = 60, 3 = 40, 4+ = 20
    if count == 0:
        score = 95
    elif count == 1:
        score = 80
    elif count == 2:
        score = 60
    elif count == 3:
        score = 40
    else:
        score = max(10, 100 - count * 20)

    return {
        "competitors": nearby,
        "total_count": count,
        "nearest_distance_m": nearby[0]["distance_m"] if nearby else None,
        "score": score,
        "source": "mock_data"
    }

def get_median_income(lat: float, lng: float) -> dict:
    """Get median household income near a location."""
    if lat > 43.46:
        data = MOCK_INCOME["waterloo_uptown"]
    else:
        data = MOCK_INCOME["kitchener_downtown"]

    income = data["median_income"]

    # Score: 0-100 based on income level
    # <40k = low, 40-60k = moderate, >60k = high
    if income >= 60000:
        score = min(100, 70 + (income - 60000) // 1000)
    elif income >= 40000:
        score = 30 + (income - 40000) // 500
    else:
        score = max(0, income // 1334)

    return {**data, "score": score, "source": "mock_data"}


if __name__ == "__main__":
    print("--- get_population ---")
    print(get_population(43.45, -80.49, 2.0))
    print("\n--- find_competitors ---")
    print(find_competitors(43.45, -80.49, "coffee_shop", 1.0))
    print("\n--- get_median_income ---")
    print(get_median_income(43.45, -80.49))
