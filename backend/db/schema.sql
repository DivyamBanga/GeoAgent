-- Census demographics (one row per dissemination area)
CREATE TABLE IF NOT EXISTS demographics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    da_id TEXT UNIQUE,                -- dissemination area ID
    province TEXT,
    population INTEGER,
    median_income INTEGER,
    avg_age REAL,
    total_households INTEGER,
    lat REAL,                         -- centroid latitude
    lng REAL                          -- centroid longitude
);

CREATE INDEX IF NOT EXISTS idx_demographics_location ON demographics (lat, lng);

-- Points of interest (restaurants, shops, etc.)
CREATE TABLE IF NOT EXISTS pois (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    category TEXT,                    -- "coffee_shop", "restaurant", etc.
    brand TEXT,
    address TEXT,
    lat REAL,
    lng REAL
);

CREATE INDEX IF NOT EXISTS idx_pois_category ON pois (category);
CREATE INDEX IF NOT EXISTS idx_pois_location ON pois (lat, lng);

-- Road network (for traffic estimates)
CREATE TABLE IF NOT EXISTS roads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    road_name TEXT,
    road_class TEXT,                  -- "highway", "arterial", "residential"
    speed_limit INTEGER,
    lat REAL,                         -- midpoint latitude
    lng REAL                          -- midpoint longitude
);

CREATE INDEX IF NOT EXISTS idx_roads_location ON roads (lat, lng);

-- Zoning areas
CREATE TABLE IF NOT EXISTS zoning (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_code TEXT,
    zone_type TEXT,                   -- "commercial", "residential", "mixed"
    permitted_uses TEXT,              -- comma-separated list of permitted use types
    lat REAL,                         -- centroid latitude
    lng REAL                          -- centroid longitude
);

CREATE INDEX IF NOT EXISTS idx_zoning_location ON zoning (lat, lng);
