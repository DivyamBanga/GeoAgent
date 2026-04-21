"""Load POI data from Overture Maps into SQLite.

Download first:
    pip install overturemaps
    overturemaps download --bbox=-80.6,43.35,-80.3,43.55 -t place -f geoparquet -o backend/db/data/places.parquet
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "geoagent.db")


def load_pois(parquet_path: str):
    """Load POIs from a GeoParquet file into SQLite."""
    import geopandas as gpd

    print("Reading parquet file...")
    gdf = gpd.read_parquet(parquet_path)
    print(f"  Total POIs: {len(gdf)}")

    conn = sqlite3.connect(DB_PATH)

    count = 0
    for _, row in gdf.iterrows():
        # Extract coordinates
        geom = row["geometry"]
        lat, lng = geom.y, geom.x

        # Extract name
        names = row.get("names")
        name = names.get("primary", "Unknown") if isinstance(names, dict) else "Unknown"

        # Extract category
        categories = row.get("categories")
        category = categories.get("primary", "other") if isinstance(categories, dict) else "other"

        # Extract brand name
        brand_info = row.get("brand")
        brand = None
        if isinstance(brand_info, dict):
            brand_names = brand_info.get("names")
            if isinstance(brand_names, dict):
                brand = brand_names.get("primary")

        # Extract address
        addresses = row.get("addresses")
        address = None
        if addresses is not None and len(addresses) > 0:
            addr = addresses[0]
            if isinstance(addr, dict):
                parts = [addr.get("freeform", ""), addr.get("locality", ""), addr.get("region", "")]
                address = ", ".join(p for p in parts if p)

        conn.execute(
            "INSERT INTO pois (name, category, brand, address, lat, lng) VALUES (?, ?, ?, ?, ?, ?)",
            (name, category, brand, address, lat, lng)
        )
        count += 1

    conn.commit()
    conn.close()
    print(f"  Loaded {count} POIs into database")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python load_pois.py <parquet_path>")
        sys.exit(1)
    load_pois(sys.argv[1])
