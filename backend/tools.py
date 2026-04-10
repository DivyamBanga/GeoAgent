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

    return {
        "population": data["population"],
        "area_name": data["area"],
        "radius_km": radius_km,
        "source": "mock_data"
    }

if __name__ == "__main__":
    print(get_population(43.45, -80.49, 2.0))
