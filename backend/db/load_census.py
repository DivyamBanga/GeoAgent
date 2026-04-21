"""Load Canadian Census data into SQLite.

Steps:
1. Download DA boundary shapefile for Ontario from StatsCan
2. Download census profile CSV for Ontario (comprehensive, GEONO=006_Ontario)
3. This script loads both into the demographics table

Data sources:
    Boundaries: https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/files-fichiers/lda_000a21a_e.zip
    Census profile: https://www12.statcan.gc.ca/census-recensement/2021/dp-pd/prof/details/download-telecharger/comp/GetFile.cfm?Lang=E&FILETYPE=CSV&GEONO=006_Ontario
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "geoagent.db")

# Kitchener-Waterloo CMA bounding box
KW_BOUNDS = {
    "lat_min": 43.30,
    "lat_max": 43.60,
    "lng_min": -80.70,
    "lng_max": -80.20,
}

# Census profile characteristic IDs we care about
CHAR_POPULATION = "1"       # Population, 2021
CHAR_AVG_AGE = "39"         # Average age of the population
CHAR_HOUSEHOLDS = "50"      # Total private households by size
CHAR_MEDIAN_INCOME = "243"  # Median total income of household in 2020 ($)
TARGET_CHARS = {CHAR_POPULATION, CHAR_AVG_AGE, CHAR_HOUSEHOLDS, CHAR_MEDIAN_INCOME}


def load_boundaries(shapefile_path: str):
    """Load dissemination area boundaries from shapefile.
    Reads the shapefile, filters to KW bounding box, extracts centroids,
    and inserts into SQLite.
    """
    import geopandas as gpd

    print("Reading shapefile (this may take a minute)...")
    gdf = gpd.read_file(shapefile_path)
    print(f"  Total DAs in Canada: {len(gdf)}")

    # Filter to Ontario first (PRUID=35) for faster CRS conversion
    gdf = gdf[gdf["PRUID"] == "35"]
    print(f"  Ontario DAs: {len(gdf)}")

    # Convert to WGS84 (lat/lng)
    gdf = gdf.to_crs(epsg=4326)

    # Extract centroids
    gdf["lat"] = gdf.geometry.centroid.y
    gdf["lng"] = gdf.geometry.centroid.x

    # Filter to KW bounding box
    gdf = gdf[
        (gdf["lat"] >= KW_BOUNDS["lat_min"]) & (gdf["lat"] <= KW_BOUNDS["lat_max"]) &
        (gdf["lng"] >= KW_BOUNDS["lng_min"]) & (gdf["lng"] <= KW_BOUNDS["lng_max"])
    ]
    print(f"  KW area DAs: {len(gdf)}")

    conn = sqlite3.connect(DB_PATH)
    inserted = 0
    for _, row in gdf.iterrows():
        conn.execute(
            "INSERT OR IGNORE INTO demographics (da_id, province, lat, lng) VALUES (?, ?, ?, ?)",
            (row["DAUID"], row["PRUID"], row["lat"], row["lng"])
        )
        inserted += 1
    conn.commit()
    conn.close()
    print(f"  Loaded {inserted} dissemination areas into database")


def load_census_profile(zip_path: str):
    """Load census profile data (population, income, age, households) from zip.

    Streams through the CSV inside the zip file, matching only the
    characteristic IDs we need for DAs already in the database.
    """
    import zipfile
    import csv
    import io

    # Get the set of DAUIDs we care about (already loaded from shapefile)
    conn = sqlite3.connect(DB_PATH)
    da_rows = conn.execute("SELECT da_id FROM demographics").fetchall()
    target_das = {row[0] for row in da_rows}
    conn.close()

    if not target_das:
        print("  ERROR: No DAs in database. Run load_boundaries first.")
        return

    print(f"  Looking for census data for {len(target_das)} DAs...")

    # Find the CSV file inside the zip
    zf = zipfile.ZipFile(zip_path)
    csv_files = [n for n in zf.namelist() if n.endswith("_data_Ontario.csv")]
    if not csv_files:
        print(f"  ERROR: No CSV data file found in {zip_path}")
        return
    csv_name = csv_files[0]
    print(f"  Streaming {csv_name} (~8 GB, this will take a few minutes)...")

    # Stream through and collect data for our DAs
    # Key: (da_id) -> {population, avg_age, total_households, median_income}
    da_data = {}
    lines_read = 0
    matches = 0

    with zf.open(csv_name) as f:
        text_stream = io.TextIOWrapper(f, encoding="latin-1")
        reader = csv.reader(text_stream)
        next(reader)  # skip header

        for row in reader:
            lines_read += 1

            if lines_read % 5_000_000 == 0:
                print(f"    ...processed {lines_read:,} lines, {matches} matches so far")

            if len(row) < 12:
                continue

            # row[8] = CHARACTERISTIC_ID, row[2] = ALT_GEO_CODE, row[11] = C1_COUNT_TOTAL
            char_id = row[8]
            if char_id not in TARGET_CHARS:
                continue

            alt_geo_code = row[2]
            if alt_geo_code not in target_das:
                continue

            value_str = row[11].strip()
            try:
                value = float(value_str) if value_str else None
            except ValueError:
                value = None

            if value is None:
                continue

            matches += 1
            if alt_geo_code not in da_data:
                da_data[alt_geo_code] = {}

            if char_id == CHAR_POPULATION:
                da_data[alt_geo_code]["population"] = int(value)
            elif char_id == CHAR_AVG_AGE:
                da_data[alt_geo_code]["avg_age"] = value
            elif char_id == CHAR_HOUSEHOLDS:
                da_data[alt_geo_code]["total_households"] = int(value)
            elif char_id == CHAR_MEDIAN_INCOME:
                da_data[alt_geo_code]["median_income"] = int(value)

    print(f"  Finished: {lines_read:,} lines, {matches} matches for {len(da_data)} DAs")

    # Update the database
    conn = sqlite3.connect(DB_PATH)
    updated = 0
    for da_id, data in da_data.items():
        conn.execute(
            """UPDATE demographics
               SET population = ?, median_income = ?, avg_age = ?, total_households = ?
               WHERE da_id = ?""",
            (
                data.get("population"),
                data.get("median_income"),
                data.get("avg_age"),
                data.get("total_households"),
                da_id,
            )
        )
        updated += 1
    conn.commit()
    conn.close()
    print(f"  Updated {updated} DAs with census profile data")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python load_census.py boundaries <shapefile_path>")
        print("  python load_census.py profile <census_zip_path>")
        print("  python load_census.py all <shapefile_path> <census_zip_path>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "boundaries":
        load_boundaries(sys.argv[2])
    elif command == "profile":
        load_census_profile(sys.argv[2])
    elif command == "all":
        load_boundaries(sys.argv[2])
        load_census_profile(sys.argv[3])
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
