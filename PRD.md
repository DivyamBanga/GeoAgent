# GeoAgent - Product Requirements Document

## What is GeoAgent?

GeoAgent is a location intelligence system. You type a question like "Where should I open a coffee shop in Kitchener?" and it gives you a scored recommendation backed by real data — demographics, competition, traffic, zoning — all displayed on an interactive map.

It starts as a single Python script calling Claude. It ends as a multi-agent system with a React frontend, Django backend, SQLite database, and Leaflet map.

Every phase produces something you can run and test.

---

## Tech Stack (All Free)

| Layer | Tech | Why |
|-------|------|-----|
| LLM | Claude API (free tier) | Tool use support, Anthropic internship relevance |
| Agent Framework | LangGraph | Multi-agent orchestration, conditional routing |
| Backend | Django + Django REST Framework | Python, batteries-included, you know it |
| Database | SQLite | Built into Python, zero setup, just a file |
| Frontend | React + TypeScript | Modern, component-based UI |
| Map | Leaflet (react-leaflet) | Free, open-source map rendering |
| Data | StatsCan Census, Overture Maps, OSM | All free and open |

---

## How the Phases Connect

```
Phase 1: "Hello Claude" ──> Phase 2: Add tools ──> Phase 3: Real DB
   (1 script)              (1 script)              (SQLite + real data)
                                                          │
Phase 6: Multi-agent <── Phase 5: LangGraph <── Phase 4: Frontend
   (sub-agents)           (graph orchestration)   (React + Leaflet)
                                │
                          Phase 7: Polish & Deploy
```

Each phase is usable on its own. You can demo any phase.

---

# PHASE 1: Talk to Claude (Days 1-2)

**Goal:** Make a Python script that sends a question to Claude and gets an answer back. Nothing fancy. Just prove the API works.

**What you'll learn:** How the Claude API works, message format, response structure.

**What you can test:** Run the script, see a response printed in your terminal.

---

### Step 1.1: Set up the project

**What to do:**
1. Create a Python virtual environment
2. Install the anthropic package
3. Get a free API key from console.anthropic.com
4. Store the key in a `.env` file (never commit this)

**Files to create:**
```
GeoAgent/
├── backend/
│   ├── .env              ← ANTHROPIC_API_KEY=sk-ant-...
│   ├── requirements.txt  ← anthropic, python-dotenv
│   └── main.py           ← your first script
├── .gitignore            ← include .env
└── PRD.md
```

**Substeps:**
1. `cd backend && python -m venv venv`
2. `source venv/Scripts/activate` (Windows: `venv\Scripts\activate`)
3. `pip install anthropic python-dotenv`
4. `pip freeze > requirements.txt`
5. Create `.env` with your API key
6. Add `.env` and `venv/` to `.gitignore`

**Test:** `pip list` shows anthropic installed. `.env` has your key.

---

### Step 1.2: Make your first API call

**What to do:** Write a script that sends one message to Claude and prints the response.

**File:** `backend/main.py`

```python
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "What makes a good location for a coffee shop?"}
    ]
)

print(message.content[0].text)
```

**Substeps:**
1. Write the script exactly as above
2. Run it: `python main.py`
3. Read the output — Claude should give you a thoughtful answer about foot traffic, demographics, etc.
4. Try changing the question to "What data would you need to evaluate a retail location?"
5. Read the response — this tells you what your future agents need to provide

**Test:** You see a multi-paragraph response printed in your terminal. No errors.

**What you now understand:** The Claude API takes messages in, gives text out. That's it. Everything else is built on top of this.

---

### Step 1.3: Add conversation memory

**What to do:** Make it a loop so you can have a back-and-forth conversation.

**File:** `backend/main.py` (update it)

```python
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()
conversation = []

system_prompt = """You are GeoAgent, a location intelligence analyst.
You help people find the best locations for their businesses.
You think about demographics, competition, foot traffic, and zoning."""

while True:
    user_input = input("\nYou: ")
    if user_input.lower() in ("quit", "exit"):
        break

    conversation.append({"role": "user", "content": user_input})

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=conversation
    )

    assistant_message = response.content[0].text
    conversation.append({"role": "assistant", "content": assistant_message})
    print(f"\nGeoAgent: {assistant_message}")
```

**Substeps:**
1. Update main.py with the conversation loop
2. Run it and have a 3-4 message conversation about opening a coffee shop
3. Notice how Claude remembers what you said earlier — that's conversation memory
4. Try asking "What did I ask you first?" — it should remember

**Test:** You can have a multi-turn conversation. Claude references earlier messages.

---

### Phase 1 Checkpoint

You should now have:
- [x] A working Python environment with the anthropic package
- [x] A script that talks to Claude
- [x] A conversational loop with a system prompt
- [x] Understanding of: API key, messages array, system prompt, response structure

**Demo:** Run the script and have a conversation about location analysis. It's just a chatbot right now, but it's YOUR chatbot with a geo focus.

---

# PHASE 2: Give Claude Tools (Days 3-6)

**Goal:** Teach Claude to call Python functions. This is the core concept of "agents" — an LLM that can take actions, not just talk.

**What you'll learn:** Tool use (function calling), the tool-use loop, how agents actually work.

**What you can test:** Ask a question, watch Claude call your function, see the answer incorporate real data.

---

### Step 2.1: One tool — get_population

**What to do:** Define a single tool that returns population data. Hardcode the data for now — the point is learning the tool-use flow, not the data.

**File:** `backend/tools.py` (new file)

```python
# Hardcoded data for now. We'll replace with SQLite in Phase 3.
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
    elif lat > 43.45:
        data = MOCK_DATA["kitchener_downtown"]
    else:
        data = MOCK_DATA["kitchener_dtr"]

    return {
        "population": data["population"],
        "area_name": data["area"],
        "radius_km": radius_km,
        "source": "mock_data"
    }
```

**Substeps:**
1. Create `backend/tools.py` with the mock data and function above
2. Test it standalone: add `if __name__ == "__main__": print(get_population(43.45, -80.49, 2.0))`
3. Run `python tools.py` and verify it returns a dict

**Test:** `python tools.py` prints `{'population': 12500, 'area_name': 'Downtown Kitchener', ...}`

---

### Step 2.2: Tell Claude about the tool

**What to do:** Define the tool schema so Claude knows the function exists and when to call it.

**File:** `backend/agent.py` (new file)

```python
import json
import anthropic
from dotenv import load_dotenv
from tools import get_population

load_dotenv()

client = anthropic.Anthropic()

# This is the tool DEFINITION — tells Claude what the function does
tools = [
    {
        "name": "get_population",
        "description": "Get the population count within a radius of a geographic point. Use this when the user asks about population, demographics, or how many people live near a location.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {
                    "type": "number",
                    "description": "Latitude of the center point"
                },
                "lng": {
                    "type": "number",
                    "description": "Longitude of the center point"
                },
                "radius_km": {
                    "type": "number",
                    "description": "Radius in kilometers to search within"
                }
            },
            "required": ["lat", "lng", "radius_km"]
        }
    }
]

# This maps tool names to actual Python functions
TOOL_FUNCTIONS = {
    "get_population": get_population
}
```

**Substeps:**
1. Create `backend/agent.py` with the code above
2. Read the tool definition carefully — the `input_schema` tells Claude what arguments to pass
3. The `description` tells Claude WHEN to use this tool
4. `TOOL_FUNCTIONS` is a lookup table — when Claude says "call get_population", you look it up here and run it

**Test:** No test yet — this is just setup. Next step connects it.

---

### Step 2.3: The tool-use loop

**What to do:** This is the key step. Build the loop where:
1. User asks a question
2. Claude decides to call a tool (or just responds with text)
3. You execute the tool
4. You send the result back to Claude
5. Claude gives the final answer using the tool's data

**File:** `backend/agent.py` (add to it)

```python
def run_agent(user_message: str) -> str:
    """Run one turn of the agent loop."""
    messages = [{"role": "user", "content": user_message}]

    system = """You are GeoAgent, a location intelligence analyst.
    When users ask about locations, use your tools to get real data.
    Always provide specific numbers from the tools, not guesses.
    If the user mentions Kitchener downtown, use lat=43.45, lng=-80.49.
    If they mention Waterloo uptown, use lat=43.47, lng=-80.52."""

    # Step 1: Send message to Claude with tool definitions
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system,
        tools=tools,
        messages=messages
    )

    # Step 2: Check if Claude wants to use a tool
    while response.stop_reason == "tool_use":
        # Find the tool use block in the response
        tool_use_block = next(
            block for block in response.content if block.type == "tool_use"
        )
        tool_name = tool_use_block.name
        tool_input = tool_use_block.input

        print(f"  [Agent is calling: {tool_name}({tool_input})]")

        # Step 3: Execute the actual Python function
        result = TOOL_FUNCTIONS[tool_name](**tool_input)

        # Step 4: Send the result back to Claude
        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_block.id,
                    "content": json.dumps(result)
                }
            ]
        })

        # Step 5: Claude generates final answer using the tool result
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system,
            tools=tools,
            messages=messages
        )

    # Extract text response
    text_blocks = [b.text for b in response.content if hasattr(b, "text")]
    return "\n".join(text_blocks)


if __name__ == "__main__":
    while True:
        q = input("\nYou: ")
        if q.lower() in ("quit", "exit"):
            break
        answer = run_agent(q)
        print(f"\nGeoAgent: {answer}")
```

**Substeps:**
1. Add the `run_agent` function to `agent.py`
2. Run it: `python agent.py`
3. Ask: "What's the population near downtown Kitchener?"
4. Watch the output — you should see `[Agent is calling: get_population({...})]`
5. Then see Claude's answer that cites the actual number from your mock data
6. Ask: "What about Waterloo uptown?" — see it call the tool again with different coordinates
7. Ask: "What's your favorite color?" — Claude should just respond without calling a tool

**Test:**
- Question about population → Claude calls `get_population` → answer includes the number 12500
- Question NOT about population → Claude just responds with text, no tool call
- The `[Agent is calling...]` line appears showing you exactly what Claude decided to do

**What you now understand:** This is an agent. Claude reads the question, decides if a tool is needed, calls it with the right arguments, and uses the result. That's the whole pattern.

---

### Step 2.4: Add more tools

**What to do:** Add 2 more tools so Claude can call multiple tools for one question.

**File:** `backend/tools.py` (add these functions)

```python
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
    return {
        "competitors": nearby,
        "total_count": len(nearby),
        "nearest_distance_m": nearby[0]["distance_m"] if nearby else None,
        "source": "mock_data"
    }

def get_median_income(lat: float, lng: float) -> dict:
    """Get median household income near a location."""
    if lat > 43.46:
        data = MOCK_INCOME["waterloo_uptown"]
    else:
        data = MOCK_INCOME["kitchener_downtown"]
    return {**data, "source": "mock_data"}
```

**File:** `backend/agent.py` (update the tools list and TOOL_FUNCTIONS)

Add tool definitions for `find_competitors` and `get_median_income` in the same format as `get_population`. Update `TOOL_FUNCTIONS` to include them.

**Substeps:**
1. Add the new functions to `tools.py`
2. Add their tool definitions to the `tools` list in `agent.py`
3. Add them to `TOOL_FUNCTIONS`
4. Run it and ask: "Should I open a coffee shop in downtown Kitchener? What's the competition and demographics like?"
5. Watch Claude call MULTIPLE tools to answer one question
6. See it synthesize all the data into one coherent answer

**Test:**
- Complex question → Claude calls 2-3 tools in sequence
- Answer references data from multiple tools ("population of 12,500... 3 competitors within 1km... median income of $52,000...")
- Ask a simple question → Claude calls only the relevant tool(s)

---

### Step 2.5: Add structured output for scores

**What to do:** Make each tool return a score (0-100) alongside the raw data, and tell Claude to give an overall score.

**File:** `backend/tools.py` (update return values)

Add a `score` field to each tool's return dict. For example:
- `get_population`: score based on population (>10k = high score)
- `find_competitors`: score based on saturation (fewer competitors = higher score)
- `get_median_income`: score based on income level

**File:** Update the system prompt in `agent.py`:

```python
system = """You are GeoAgent, a location intelligence analyst.
When analyzing a location, use ALL relevant tools to gather data.
After gathering data, provide:
1. An overall score (0-100) for the location
2. The top 3 positive factors
3. The top 3 risks
4. A clear recommendation (Go / Caution / Avoid)
Format your response clearly with headers."""
```

**Substeps:**
1. Add score calculations to each tool
2. Update the system prompt
3. Ask: "Rate downtown Kitchener for a coffee shop"
4. Verify the response includes a score, positives, risks, and recommendation

**Test:** Response is structured with a score, factors, risks, and a clear recommendation.

---

### Phase 2 Checkpoint

You should now have:
- [x] 3 working tools (population, competitors, income)
- [x] A tool-use loop that handles Claude calling multiple tools
- [x] Structured output with scores and recommendations
- [x] Understanding of: tool definitions, tool-use loop, multi-tool orchestration

**Demo:** Ask "Should I open a coffee shop in downtown Kitchener?" and get a scored, data-backed recommendation.

**File structure:**
```
GeoAgent/
├── backend/
│   ├── .env
│   ├── requirements.txt
│   ├── main.py         ← simple chat (Phase 1)
│   ├── tools.py        ← tool functions with mock data
│   └── agent.py        ← agent with tool-use loop
└── PRD.md
```

---

# PHASE 3: Real Data with SQLite (Days 7-14)

**Goal:** Replace mock data with real spatial data. Set up SQLite, load Canadian census data and POIs, and make the tools query the actual database.

**What you'll learn:** SQLite, spatial distance calculations (Haversine), loading real geo data, connecting Python to a database.

**What you can test:** Same agent questions as Phase 2, but answers come from real data now.

---

### Step 3.1: Set up SQLite database

**What to do:** Create a SQLite database file. No installation needed — Python has `sqlite3` built in.

**Substeps:**
1. Create the `backend/db/` directory
2. The database will be a single file: `backend/db/geoagent.db`
3. Add `*.db` to `.gitignore` (database files shouldn't be committed)
4. Test: open a Python shell and run:
   ```python
   import sqlite3
   conn = sqlite3.connect("backend/db/geoagent.db")
   conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
   conn.execute("INSERT INTO test VALUES (1, 'hello')")
   print(conn.execute("SELECT * FROM test").fetchall())
   conn.execute("DROP TABLE test")
   conn.close()
   ```

**Test:** No errors. You can create tables and query them. That's the whole "setup."

---

### Step 3.2: Create the database schema

**What to do:** Create tables for demographics, POIs, roads, and zoning. Instead of PostGIS geometry columns, store lat/lng as regular floats and use the Haversine formula for distance calculations.

**File:** `backend/db/schema.sql` (new file)

```sql
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
```

**Substeps:**
1. Create `backend/db/schema.sql` with the SQL above
2. Run it with a small Python script or inline:
   ```python
   import sqlite3
   conn = sqlite3.connect("backend/db/geoagent.db")
   conn.executescript(open("backend/db/schema.sql").read())
   conn.close()
   ```
3. Verify: connect to DB and check tables exist:
   ```python
   conn = sqlite3.connect("backend/db/geoagent.db")
   tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
   print(tables)  # should show demographics, pois, roads, zoning
   ```

**Test:** All 4 tables exist. No Docker, no server, no extensions needed.

---

### Step 3.3: Create the Haversine distance helper

**What to do:** Write a Python function that calculates distance between two lat/lng points. This replaces PostGIS's `ST_DWithin` and `ST_Distance`.

**File:** `backend/db/geo_utils.py` (new file)

```python
import math

def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate the distance in km between two lat/lng points."""
    R = 6371  # Earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))
```

**Substeps:**
1. Create `backend/db/geo_utils.py`
2. Test it:
   ```python
   from db.geo_utils import haversine
   # Downtown Kitchener to Uptown Waterloo ≈ 2.5 km
   print(haversine(43.45, -80.49, 43.47, -80.52))
   ```

**Test:** Returns ~2.5 km for downtown Kitchener to uptown Waterloo. That's correct.

---

### Step 3.4: Download and load census data

**What to do:** Get real Canadian Census data for Kitchener-Waterloo and load it into SQLite.

**Data source:** Statistics Canada (all free, open data)
- Census boundary files: https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/index2021-eng.cfm
  - Download: Dissemination Areas (DA) boundary file for Ontario
- Census profile data: https://www12.statcan.gc.ca/census-recensement/2021/dp-pd/prof/index.cfm
  - Download CSV for the Kitchener-Cambridge-Waterloo CMA

**File:** `backend/db/load_census.py` (new file)

```python
"""Load Canadian Census data into SQLite.

Steps:
1. Download DA boundary shapefile for Ontario from StatsCan
2. Download census profile CSV for Kitchener CMA
3. This script loads both into the demographics table
"""

import csv
import sqlite3

DB_PATH = "backend/db/geoagent.db"

def load_boundaries(shapefile_path: str):
    """Load dissemination area boundaries from shapefile.
    Uses geopandas to read the shapefile, extract centroids, and insert into SQLite.
    """
    import geopandas as gpd

    gdf = gpd.read_file(shapefile_path)

    # Filter to Kitchener-Waterloo area (CMA code 541)
    gdf = gdf[gdf["CMAUID"] == "541"]

    # Convert to lat/lng (WGS84)
    gdf = gdf.to_crs(epsg=4326)

    # Get centroids for each dissemination area
    gdf["lat"] = gdf.geometry.centroid.y
    gdf["lng"] = gdf.geometry.centroid.x

    conn = sqlite3.connect(DB_PATH)
    for _, row in gdf.iterrows():
        conn.execute(
            "INSERT OR IGNORE INTO demographics (da_id, province, lat, lng) VALUES (?, ?, ?, ?)",
            (row["DAUID"], row["PRUID"], row["lat"], row["lng"])
        )
    conn.commit()
    conn.close()
    print(f"Loaded {len(gdf)} dissemination areas")

def load_census_profile(csv_path: str):
    """Load census profile data (population, income, age) and update demographics rows."""
    conn = sqlite3.connect(DB_PATH)

    # Census profile CSVs have a specific format — you'll need to pivot
    # the rows to get population, income, age as columns.
    # Key characteristic IDs:
    #   1 = Population 2021
    #   236 = Median total income
    #   39 = Average age

    # Parse CSV and update rows — adjust based on actual CSV structure
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pass  # Process based on actual StatsCan CSV format

    conn.commit()
    conn.close()
    print("Loaded census profile data")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python load_census.py <shapefile_path> [csv_path]")
        sys.exit(1)

    load_boundaries(sys.argv[1])
    if len(sys.argv) > 2:
        load_census_profile(sys.argv[2])
```

**Substeps:**
1. `pip install geopandas` (only needed for loading shapefiles, add to requirements.txt)
2. Download the DA boundary shapefile from StatsCan (it's a .zip with .shp files)
3. Unzip to `backend/db/data/` (add this directory to .gitignore — data files are large)
4. Run: `python db/load_census.py db/data/lda_000b21a_e.shp`
5. Verify: `SELECT COUNT(*) FROM demographics;` should show hundreds of rows
6. Verify: `SELECT da_id, lat, lng FROM demographics LIMIT 5;`
7. Download the census profile CSV and load it
8. Verify: `SELECT da_id, population, median_income FROM demographics WHERE population > 0 LIMIT 5;`

**Test:** Database has real census data with centroids for each dissemination area.

---

### Step 3.5: Load POI data

**What to do:** Load real business/POI data from Overture Maps (free, open dataset).

**Data source:** Overture Maps Foundation — https://overturemaps.org/
- You can download place data using their CLI tool or DuckDB

**File:** `backend/db/load_pois.py` (new file)

```python
"""Load POI data from Overture Maps into SQLite.

Download first:
    pip install overturemaps
    overturemaps download --bbox=-80.6,43.35,-80.3,43.55 -t places -o places.geojson
"""

import json
import sqlite3

DB_PATH = "backend/db/geoagent.db"

def load_pois(geojson_path: str):
    """Load POIs from a GeoJSON file into SQLite."""
    with open(geojson_path, "r") as f:
        data = json.load(f)

    conn = sqlite3.connect(DB_PATH)

    count = 0
    for feature in data["features"]:
        props = feature["properties"]
        coords = feature["geometry"]["coordinates"]
        lng, lat = coords[0], coords[1]

        name = props.get("names", {}).get("primary", "Unknown") if isinstance(props.get("names"), dict) else str(props.get("names", "Unknown"))
        category = props.get("categories", {}).get("primary", "other") if isinstance(props.get("categories"), dict) else str(props.get("categories", "other"))

        conn.execute(
            "INSERT INTO pois (name, category, lat, lng) VALUES (?, ?, ?, ?)",
            (name, category, lat, lng)
        )
        count += 1

    conn.commit()
    conn.close()
    print(f"Loaded {count} POIs")

if __name__ == "__main__":
    import sys
    load_pois(sys.argv[1])
```

**Substeps:**
1. `pip install overturemaps` (add to requirements.txt)
2. Download KW area POIs:
   ```bash
   overturemaps download --bbox=-80.6,43.35,-80.3,43.55 -t places -o backend/db/data/places.geojson
   ```
3. Run: `python db/load_pois.py db/data/places.geojson`
4. Verify: `SELECT COUNT(*) FROM pois;`
5. Verify categories: `SELECT category, COUNT(*) FROM pois GROUP BY category ORDER BY COUNT(*) DESC LIMIT 10;`

**Test:** Database has real POI data. You can find coffee shops near downtown Kitchener.

---

### Step 3.6: Write real query functions

**What to do:** Replace mock tool functions with real SQLite queries + Haversine distance.

**File:** `backend/tools.py` (rewrite)

```python
import sqlite3
from db.geo_utils import haversine

DB_PATH = "db/geoagent.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_population(lat: float, lng: float, radius_km: float) -> dict:
    """Get population within radius using Haversine distance."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT population, median_income, avg_age FROM demographics WHERE population > 0"
    ).fetchall()
    conn.close()

    # Filter by distance in Python
    nearby = [r for r in rows if haversine(lat, lng, r["lat"], r["lng"]) <= radius_km]

    total_pop = sum(r["population"] or 0 for r in nearby)
    incomes = [r["median_income"] for r in nearby if r["median_income"]]
    ages = [r["avg_age"] for r in nearby if r["avg_age"]]

    score = min(100, int(total_pop / 200))

    return {
        "population": total_pop,
        "avg_median_income": round(sum(incomes) / len(incomes), 0) if incomes else 0,
        "avg_age": round(sum(ages) / len(ages), 1) if ages else 0,
        "areas_covered": len(nearby),
        "radius_km": radius_km,
        "score": score,
        "source": "statscan_census_2021"
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
```

**Substeps:**
1. Rewrite `tools.py` with SQLite queries + Haversine
2. Test each function standalone:
   ```python
   python -c "from tools import get_population; print(get_population(43.45, -80.49, 2.0))"
   ```
3. Test `find_competitors`: should return real business names
4. Test `get_median_income`: should return real income data
5. Run `agent.py` again with the same questions from Phase 2
6. Answers should now include real data instead of mock data

**Test:** Same questions, but real data from SQLite. Business names are real. Population numbers match census data.

---

### Step 3.7: Add two more tools

**What to do:** Add zoning check and road info tools.

**Add to `tools.py`:**
- `check_zoning(lat, lng)` → finds nearest zoning area, returns if commercial use is allowed
- `get_road_info(lat, lng)` → finds nearest road, returns road class and speed limit

**Add to `agent.py`:**
- Add tool definitions for both
- Add to TOOL_FUNCTIONS

**Substeps:**
1. Write `check_zoning()` — finds nearest zone using Haversine
2. Write `get_road_info()` — finds nearest road using Haversine
3. Load road data from OSM (download from Geofabrik: https://download.geofabrik.de/north-america/canada/ontario.html)
4. Load zoning data from City of Kitchener open data portal
5. Add tool definitions in agent.py
6. Test: "Is downtown Kitchener zoned for commercial use?"
7. Test: "What's the road access like near King Street?"

**Test:** 5 working tools, all querying real SQLite data.

---

### Phase 3 Checkpoint

You should now have:
- [x] SQLite database with real data (zero setup, just a file)
- [x] Haversine distance function for spatial queries
- [x] Census demographics for KW area
- [x] POI data from Overture Maps
- [x] 5 tools querying real data
- [x] Same agent interface as Phase 2 but with real data

**Demo:** "Should I open a coffee shop on King Street in downtown Kitchener?" → answer includes real population, real competitor names, real income data, real zoning info.

**File structure:**
```
GeoAgent/
├── backend/
│   ├── .env
│   ├── requirements.txt
│   ├── main.py
│   ├── tools.py          ← now queries SQLite
│   ├── agent.py           ← tool-use loop (unchanged)
│   └── db/
│       ├── schema.sql
│       ├── geo_utils.py   ← Haversine distance function
│       ├── load_census.py
│       ├── load_pois.py
│       ├── geoagent.db    ← the database (gitignored)
│       └── data/          ← .gitignore'd raw data files
└── PRD.md
```

---

# PHASE 4: Django Backend (Days 15-20)

**Goal:** Wrap the agent in a proper Django API so the React frontend can talk to it. Add streaming so the user sees the agent "thinking" in real time.

**What you'll learn:** Django REST framework, API design, server-sent events for streaming.

**What you can test:** Hit the API with curl or Postman and get agent responses.

---

### Step 4.1: Create the Django project

**What to do:** Set up a Django project with an `api` app.

**Substeps:**
1. `pip install django djangorestframework django-cors-headers`
2. `cd backend && django-admin startproject geoagent_project .`
3. `python manage.py startapp api`
4. Add to `INSTALLED_APPS` in settings.py:
   ```python
   "rest_framework",
   "corsheaders",
   "api",
   ```
5. Add `corsheaders.middleware.CorsMiddleware` to MIDDLEWARE (before CommonMiddleware)
6. Add `CORS_ALLOW_ALL_ORIGINS = True` (for dev only)
7. `python manage.py migrate`
8. `python manage.py runserver` — verify Django welcome page at http://localhost:8000

**Test:** Django dev server runs. Welcome page loads.

---

### Step 4.2: Create the analysis API endpoint

**What to do:** Create a POST endpoint that takes a user question and returns the agent's response.

**File:** `backend/api/views.py`

```python
from rest_framework.decorators import api_view
from rest_framework.response import Response
from agent import run_agent

@api_view(["POST"])
def analyze(request):
    """Main endpoint: send a question, get an analysis back."""
    question = request.data.get("question", "")
    if not question:
        return Response({"error": "No question provided"}, status=400)

    result = run_agent(question)
    return Response({
        "question": question,
        "answer": result
    })

@api_view(["GET"])
def health(request):
    """Health check endpoint."""
    return Response({"status": "ok"})
```

**File:** `backend/api/urls.py` (new file)

```python
from django.urls import path
from . import views

urlpatterns = [
    path("analyze/", views.analyze, name="analyze"),
    path("health/", views.health, name="health"),
]
```

**File:** `backend/geoagent_project/urls.py` (update)

```python
from django.urls import path, include

urlpatterns = [
    path("api/", include("api.urls")),
]
```

**Substeps:**
1. Create the view, api urls, and update project urls
2. Move `tools.py` and `agent.py` into the `api/` app (or keep them at backend root and import)
3. Run the server: `python manage.py runserver`
4. Test with curl:
   ```bash
   curl -X POST http://localhost:8000/api/analyze/ \
     -H "Content-Type: application/json" \
     -d '{"question": "What is the population near downtown Kitchener?"}'
   ```
5. Verify you get a JSON response with the agent's answer

**Test:** curl returns `{"question": "...", "answer": "..."}` with real agent analysis.

---

### Step 4.3: Add streaming with Server-Sent Events (SSE)

**What to do:** Stream the agent's "thinking" process so the frontend can show progress in real time.

**File:** `backend/api/views.py` (add streaming view)

```python
import json
from django.http import StreamingHttpResponse
from agent import run_agent_streaming  # we'll create this

@api_view(["POST"])
def analyze_stream(request):
    """Streaming endpoint: sends agent events as they happen."""
    question = request.data.get("question", "")

    def event_stream():
        for event in run_agent_streaming(question):
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: {\"type\": \"done\"}\n\n"

    response = StreamingHttpResponse(
        event_stream(),
        content_type="text/event-stream"
    )
    response["Cache-Control"] = "no-cache"
    return response
```

**File:** `backend/agent.py` (add streaming version)

```python
def run_agent_streaming(user_message: str):
    """Generator that yields events as the agent works."""
    yield {"type": "status", "message": "Parsing your question..."}

    messages = [{"role": "user", "content": user_message}]

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system,
        tools=tools,
        messages=messages
    )

    while response.stop_reason == "tool_use":
        tool_use_block = next(
            b for b in response.content if b.type == "tool_use"
        )

        yield {
            "type": "tool_call",
            "tool": tool_use_block.name,
            "input": tool_use_block.input
        }

        result = TOOL_FUNCTIONS[tool_use_block.name](**tool_use_block.input)

        yield {
            "type": "tool_result",
            "tool": tool_use_block.name,
            "result": result
        }

        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_use_block.id,
                "content": json.dumps(result)
            }]
        })

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system,
            tools=tools,
            messages=messages
        )

    text_blocks = [b.text for b in response.content if hasattr(b, "text")]
    final_answer = "\n".join(text_blocks)

    yield {"type": "answer", "content": final_answer}
```

**Substeps:**
1. Add `run_agent_streaming` to `agent.py`
2. Add the streaming view to `views.py`
3. Add `path("analyze/stream/", views.analyze_stream)` to urls
4. Test with curl:
   ```bash
   curl -N -X POST http://localhost:8000/api/analyze/stream/ \
     -H "Content-Type: application/json" \
     -d '{"question": "Rate King Street for a coffee shop"}'
   ```
5. You should see SSE events appearing one at a time: status → tool_call → tool_result → answer

**Test:** curl shows events streaming in real time. You can see which tools are being called.

---

### Step 4.4: Add conversation history endpoint

**What to do:** Add endpoints to save and retrieve past analyses.

**File:** `backend/api/models.py`

```python
from django.db import models

class Analysis(models.Model):
    question = models.TextField()
    answer = models.TextField()
    scores = models.JSONField(default=dict)  # sub-agent scores
    lat = models.FloatField(null=True)
    lng = models.FloatField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
```

**Substeps:**
1. Create the model
2. `python manage.py makemigrations && python manage.py migrate`
3. Save analyses after they complete (update the `analyze` view)
4. Add a `GET /api/analyses/` endpoint to list past analyses
5. Test: run a few analyses, then GET the list endpoint

**Test:** Past analyses are saved and retrievable via the API.

---

### Phase 4 Checkpoint

You should now have:
- [x] Django backend serving the agent via REST API
- [x] POST `/api/analyze/` for one-shot analysis
- [x] POST `/api/analyze/stream/` for streaming analysis
- [x] GET `/api/analyses/` for history
- [x] CORS enabled for frontend connection

**Demo:** Hit the API with curl and see streaming agent analysis.

**File structure:**
```
GeoAgent/
├── backend/
│   ├── .env
│   ├── requirements.txt
│   ├── manage.py
│   ├── geoagent_project/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── api/
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── serializers.py
│   ├── tools.py
│   ├── agent.py
│   └── db/
│       ├── schema.sql
│       ├── geo_utils.py
│       ├── geoagent.db
│       ├── load_census.py
│       └── load_pois.py
└── PRD.md
```

---

# PHASE 5: React + Leaflet Frontend (Days 21-28)

**Goal:** Build a chat + map interface. User types a question on the left, sees the agent thinking and the map updating on the right.

**What you'll learn:** React with TypeScript, Leaflet map integration, SSE consumption, responsive layout.

**What you can test:** Full end-to-end: type a question → see agent work → see map update.

---

### Step 5.1: Create the React app

**Substeps:**
1. From the GeoAgent root: `npx create-react-app frontend --template typescript`
   (or use Vite: `npm create vite@latest frontend -- --template react-ts`)
2. `cd frontend && npm install`
3. Install dependencies:
   ```bash
   npm install react-leaflet leaflet @types/leaflet axios
   ```
4. `npm run dev` — verify the default page loads at http://localhost:5173
5. Clean out the boilerplate (delete default App content)

**Test:** React dev server runs. Empty page loads.

---

### Step 5.2: Build the layout — chat left, map right

**What to do:** Create a split-panel layout.

**File:** `frontend/src/App.tsx`

```tsx
import { useState } from "react"
import ChatPanel from "./components/ChatPanel"
import MapPanel from "./components/MapPanel"
import "./App.css"

function App() {
  const [markers, setMarkers] = useState([])
  const [center, setCenter] = useState<[number, number]>([43.45, -80.49]) // Kitchener

  return (
    <div className="app">
      <div className="chat-panel">
        <ChatPanel onMapUpdate={setMarkers} onCenterChange={setCenter} />
      </div>
      <div className="map-panel">
        <MapPanel markers={markers} center={center} />
      </div>
    </div>
  )
}
```

**File:** `frontend/src/App.css`

```css
.app {
  display: flex;
  height: 100vh;
  width: 100vw;
}
.chat-panel {
  width: 40%;
  border-right: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
}
.map-panel {
  width: 60%;
}
```

**Substeps:**
1. Create `App.tsx` and `App.css`
2. Create stub components: `frontend/src/components/ChatPanel.tsx` and `MapPanel.tsx`
3. Verify the layout renders — chat area on left, map area on right

**Test:** Two-panel layout visible in browser.

---

### Step 5.3: Build the map component

**File:** `frontend/src/components/MapPanel.tsx`

```tsx
import { MapContainer, TileLayer, Marker, Popup, Circle } from "react-leaflet"
import "leaflet/dist/leaflet.css"

interface MapMarker {
  lat: number
  lng: number
  label: string
  type: "target" | "competitor" | "complementary"
}

interface MapPanelProps {
  markers: MapMarker[]
  center: [number, number]
}

export default function MapPanel({ markers, center }: MapPanelProps) {
  return (
    <MapContainer center={center} zoom={14} style={{ height: "100%", width: "100%" }}>
      <TileLayer
        attribution='&copy; OpenStreetMap contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {markers.map((m, i) => (
        <Marker key={i} position={[m.lat, m.lng]}>
          <Popup>{m.label} ({m.type})</Popup>
        </Marker>
      ))}
    </MapContainer>
  )
}
```

**Substeps:**
1. Create MapPanel.tsx
2. Verify the map renders with OpenStreetMap tiles (free, no API key needed)
3. Add a test marker to make sure markers work
4. Add the Circle component for trade area radius (we'll use this later)

**Test:** Interactive map of Kitchener visible. Can pan and zoom. Test marker shows up.

---

### Step 5.4: Build the chat component

**File:** `frontend/src/components/ChatPanel.tsx`

```tsx
import { useState, useRef, useEffect } from "react"

interface Message {
  role: "user" | "assistant" | "status"
  content: string
}

export default function ChatPanel({ onMapUpdate, onCenterChange }) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => { scrollToBottom() }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const question = input.trim()
    setInput("")
    setMessages(prev => [...prev, { role: "user", content: question }])
    setLoading(true)

    try {
      // Connect to SSE streaming endpoint
      const response = await fetch("http://localhost:8000/api/analyze/stream/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question })
      })

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      while (reader) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value)
        const lines = text.split("\n").filter(l => l.startsWith("data: "))

        for (const line of lines) {
          const data = JSON.parse(line.slice(6))

          if (data.type === "status") {
            setMessages(prev => [...prev, { role: "status", content: data.message }])
          } else if (data.type === "tool_call") {
            setMessages(prev => [...prev, {
              role: "status",
              content: `Calling ${data.tool}...`
            }])
          } else if (data.type === "tool_result") {
            // Update map with competitor data if available
            if (data.tool === "find_competitors" && data.result.competitors) {
              onMapUpdate(data.result.competitors.map(c => ({
                lat: c.lat || 0, lng: c.lng || 0,
                label: c.name, type: "competitor"
              })))
            }
          } else if (data.type === "answer") {
            setMessages(prev => [...prev, { role: "assistant", content: data.content }])
          }
        }
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: "assistant", content: "Error connecting to server." }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ padding: "16px", borderBottom: "1px solid #e0e0e0" }}>
        <h2>GeoAgent</h2>
      </div>
      <div style={{ flex: 1, overflowY: "auto", padding: "16px" }}>
        {messages.map((msg, i) => (
          <div key={i} style={{
            marginBottom: "12px",
            padding: "8px 12px",
            borderRadius: "8px",
            backgroundColor: msg.role === "user" ? "#e3f2fd"
              : msg.role === "status" ? "#fff3e0"
              : "#f5f5f5",
            alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
            fontSize: msg.role === "status" ? "0.85em" : "1em",
            color: msg.role === "status" ? "#e65100" : "#212121",
          }}>
            {msg.content}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      <form onSubmit={handleSubmit} style={{ padding: "16px", borderTop: "1px solid #e0e0e0", display: "flex", gap: "8px" }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Ask about a location..."
          style={{ flex: 1, padding: "10px", borderRadius: "6px", border: "1px solid #ccc" }}
        />
        <button type="submit" disabled={loading}
          style={{ padding: "10px 20px", borderRadius: "6px", background: "#1976d2", color: "white", border: "none", cursor: "pointer" }}>
          {loading ? "..." : "Ask"}
        </button>
      </form>
    </div>
  )
}
```

**Substeps:**
1. Create ChatPanel.tsx
2. Type a question and submit it
3. Watch the streaming events appear as status messages
4. See the final answer appear
5. Check that competitor pins appear on the map (if find_competitors was called)

**Test:** Full loop works: type question → see "Calling get_population..." → see answer → see map pins.

---

### Step 5.5: Add score card component

**What to do:** Display the sub-scores in a visual card below the answer.

**File:** `frontend/src/components/ScoreCard.tsx`

```tsx
interface ScoreCardProps {
  scores: {
    demographics: number
    competition: number
    traffic: number
    zoning: number
    overall: number
  }
}

export default function ScoreCard({ scores }: ScoreCardProps) {
  const getColor = (score: number) => {
    if (score >= 70) return "#4caf50"  // green
    if (score >= 40) return "#ff9800"  // orange
    return "#f44336"                    // red
  }

  return (
    <div style={{ display: "flex", gap: "12px", padding: "12px", flexWrap: "wrap" }}>
      {Object.entries(scores).map(([key, value]) => (
        <div key={key} style={{
          textAlign: "center", padding: "8px 16px",
          borderRadius: "8px", border: `2px solid ${getColor(value)}`,
          minWidth: "80px"
        }}>
          <div style={{ fontSize: "1.5em", fontWeight: "bold", color: getColor(value) }}>
            {value}
          </div>
          <div style={{ fontSize: "0.8em", textTransform: "capitalize" }}>{key}</div>
        </div>
      ))}
    </div>
  )
}
```

**Substeps:**
1. Create ScoreCard.tsx
2. Parse scores from tool_result events in ChatPanel
3. Display ScoreCard below the final answer
4. Verify scores show with color coding (green/orange/red)

**Test:** Score card appears with sub-scores after analysis. Colors reflect good/bad scores.

---

### Step 5.6: Add trade area circle and census boundaries

**What to do:** Show the analysis radius on the map and color census areas by demographics.

**Substeps:**
1. When an analysis runs, add a `Circle` to the map at the target location with the search radius
2. Return GeoJSON boundary data from the `get_population` tool result
3. Render census area polygons using the `GeoJSON` component in react-leaflet
4. Color polygons by income (darker = higher income) or population (darker = more dense)

**Test:** Map shows a circle around the target location and colored census boundaries.

---

### Phase 5 Checkpoint

You should now have:
- [x] React frontend with chat panel and Leaflet map
- [x] Streaming agent responses visible in real time
- [x] Map updates with competitor pins and trade area circles
- [x] Score card showing sub-scores with color coding
- [x] Full end-to-end working system

**Demo:** Open the app. Ask "Should I open a coffee shop in downtown Kitchener?" See the agent think, scores appear, map pins drop, census areas color in. This is a demo-able product.

---

# PHASE 6: Multi-Agent with LangGraph (Days 29-38)

**Goal:** Upgrade from a single agent with many tools to a multi-agent system where specialized sub-agents each handle their domain. An orchestrator agent dispatches to the right sub-agents and synthesizes their reports.

**What you'll learn:** LangGraph, state management, conditional routing, parallel execution.

**What you can test:** Same user experience, but the architecture is now production-grade.

---

### Step 6.1: Install LangGraph and understand the concepts

**Substeps:**
1. `pip install langgraph langchain-anthropic`
2. Read the 3 core concepts (15 min):
   - **State**: A TypedDict that flows through the graph. Every node reads and writes to it.
   - **Nodes**: Python functions that take state, do work, return updated state.
   - **Edges**: Define which node runs after which. Can be conditional.
3. Build a hello-world graph:
   ```python
   from langgraph.graph import StateGraph
   from typing import TypedDict

   class State(TypedDict):
       message: str

   def step_one(state: State) -> State:
       return {"message": state["message"] + " -> step one done"}

   def step_two(state: State) -> State:
       return {"message": state["message"] + " -> step two done"}

   graph = StateGraph(State)
   graph.add_node("step_one", step_one)
   graph.add_node("step_two", step_two)
   graph.add_edge("step_one", "step_two")
   graph.set_entry_point("step_one")
   graph.set_finish_point("step_two")

   app = graph.compile()
   result = app.invoke({"message": "start"})
   print(result)  # {"message": "start -> step one done -> step two done"}
   ```

**Test:** Hello-world graph runs and prints the expected output.

---

### Step 6.2: Define the GeoAgent state

**File:** `backend/agents/state.py` (new file)

```python
from typing import TypedDict, Optional

class SubAgentReport(TypedDict):
    score: int             # 0-100
    summary: str           # 1-2 sentence summary
    details: dict          # raw data
    factors_positive: list # what's good
    factors_negative: list # what's bad

class GeoAgentState(TypedDict):
    # Input
    query: str
    lat: float
    lng: float
    business_type: str
    radius_km: float

    # Routing
    agents_to_run: list  # which sub-agents the orchestrator picks

    # Sub-agent reports
    demographics_report: Optional[SubAgentReport]
    competition_report: Optional[SubAgentReport]
    traffic_report: Optional[SubAgentReport]
    zoning_report: Optional[SubAgentReport]

    # Output
    overall_score: Optional[int]
    recommendation: Optional[str]  # "Go" / "Caution" / "Avoid"
    final_answer: Optional[str]
```

**Substeps:**
1. Create `backend/agents/` directory with `__init__.py`
2. Create `state.py` with the state definition above
3. This is just a data class — nothing to test yet

---

### Step 6.3: Build the intent parser node

**What to do:** First node in the graph. Takes the raw user question and extracts structured intent.

**File:** `backend/agents/intent_parser.py`

```python
import json
import anthropic
from .state import GeoAgentState

client = anthropic.Anthropic()

def parse_intent(state: GeoAgentState) -> dict:
    """Extract business type, location, and which agents to run."""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        system="""Extract structured info from the user's location question.
        Return JSON with:
        - business_type: what kind of business (e.g. "coffee_shop")
        - lat: latitude (if mentioned or inferable, else null)
        - lng: longitude (if mentioned or inferable, else null)
        - radius_km: analysis radius (default 2.0)
        - agents_needed: list from ["demographics", "competition", "traffic", "zoning"]
          Choose which agents are relevant to the question.

        Known locations:
        - Downtown Kitchener: 43.4516, -80.4925
        - Uptown Waterloo: 43.4643, -80.5204
        - King Street Kitchener: 43.4530, -80.4930
        - University of Waterloo area: 43.4723, -80.5449

        Return ONLY valid JSON, no other text.""",
        messages=[{"role": "user", "content": state["query"]}]
    )

    parsed = json.loads(response.content[0].text)

    return {
        "business_type": parsed.get("business_type", "retail"),
        "lat": parsed.get("lat", 43.45),
        "lng": parsed.get("lng", -80.49),
        "radius_km": parsed.get("radius_km", 2.0),
        "agents_to_run": parsed.get("agents_needed", ["demographics", "competition"])
    }
```

**Substeps:**
1. Create `intent_parser.py`
2. Test it standalone:
   ```python
   result = parse_intent({"query": "Best area for a coffee shop in downtown Kitchener"})
   print(result)
   # Should extract: business_type="coffee_shop", lat=43.45, agents_to_run=[...]
   ```
3. Try different questions and check the extracted intent makes sense

**Test:** Correctly extracts business type, coordinates, and which agents to run.

---

### Step 6.4: Build the demographics sub-agent

**File:** `backend/agents/demographics_agent.py`

```python
import json
import anthropic
from .state import GeoAgentState, SubAgentReport
from tools import get_population, get_median_income

client = anthropic.Anthropic()

TOOLS = [
    {
        "name": "get_population",
        "description": "Get population within radius of a point",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number"},
                "lng": {"type": "number"},
                "radius_km": {"type": "number"}
            },
            "required": ["lat", "lng", "radius_km"]
        }
    },
    {
        "name": "get_median_income",
        "description": "Get median household income at a location",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number"},
                "lng": {"type": "number"}
            },
            "required": ["lat", "lng"]
        }
    }
]

TOOL_FNS = {
    "get_population": get_population,
    "get_median_income": get_median_income,
}

def run_demographics_agent(state: GeoAgentState) -> dict:
    """Demographics sub-agent: analyzes population and income."""
    messages = [{
        "role": "user",
        "content": f"""Analyze the demographics for a {state['business_type']} at
        lat={state['lat']}, lng={state['lng']}, radius={state['radius_km']}km.
        Use your tools to get population and income data.
        Return JSON with: score (0-100), summary (1-2 sentences),
        factors_positive (list), factors_negative (list), and raw details."""
    }]

    system = """You are a demographics analyst sub-agent. Use your tools to
    gather population and income data, then evaluate how well the demographics
    support the given business type. Return ONLY valid JSON."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system,
        tools=TOOLS,
        messages=messages
    )

    # Tool-use loop (same pattern as Phase 2)
    while response.stop_reason == "tool_use":
        tool_block = next(b for b in response.content if b.type == "tool_use")
        result = TOOL_FNS[tool_block.name](**tool_block.input)

        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": tool_block.id,
                         "content": json.dumps(result)}]
        })
        response = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=1024,
            system=system, tools=TOOLS, messages=messages
        )

    text = next(b.text for b in response.content if hasattr(b, "text"))
    report = json.loads(text)

    return {"demographics_report": report}
```

**Substeps:**
1. Create `demographics_agent.py`
2. Test standalone:
   ```python
   result = run_demographics_agent({
       "query": "coffee shop", "business_type": "coffee_shop",
       "lat": 43.45, "lng": -80.49, "radius_km": 2.0,
       "agents_to_run": ["demographics"]
   })
   print(result["demographics_report"])
   ```
3. Verify it calls the database tools and returns a structured report with score

**Test:** Returns a dict with score, summary, positive/negative factors, and raw data.

---

### Step 6.5: Build the competition sub-agent

Same pattern as demographics but uses `find_competitors` tool.

**File:** `backend/agents/competition_agent.py`

**Substeps:**
1. Create the competition agent following the same pattern as Step 6.4
2. Its tools: `find_competitors`, optionally a `find_complementary_businesses` tool
3. Test standalone
4. Verify it finds real competitors from the POI database

---

### Step 6.6: Build the traffic and zoning sub-agents

Same pattern. Two more sub-agents.

**File:** `backend/agents/traffic_agent.py`
- Tools: `get_road_info`, `nearest_transit_stops`

**File:** `backend/agents/zoning_agent.py`
- Tools: `check_zoning`

**Substeps:**
1. Create both agents
2. Test each standalone
3. All 4 sub-agents now work independently

---

### Step 6.7: Build the synthesis node

**File:** `backend/agents/synthesizer.py`

```python
import json
import anthropic
from .state import GeoAgentState

client = anthropic.Anthropic()

def synthesize(state: GeoAgentState) -> dict:
    """Collect all sub-agent reports and produce final recommendation."""
    reports = {}
    if state.get("demographics_report"):
        reports["demographics"] = state["demographics_report"]
    if state.get("competition_report"):
        reports["competition"] = state["competition_report"]
    if state.get("traffic_report"):
        reports["traffic"] = state["traffic_report"]
    if state.get("zoning_report"):
        reports["zoning"] = state["zoning_report"]

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system="""You are a senior location intelligence analyst.
        Synthesize the sub-agent reports into a final recommendation.

        Provide:
        1. Overall score (0-100) — weighted average of sub-scores
        2. Recommendation: "Go" (70+), "Caution" (40-69), "Avoid" (<40)
        3. Top 3 positive factors across all reports
        4. Top 3 risks across all reports
        5. A clear, actionable 2-3 paragraph summary

        Be specific. Cite numbers from the reports. Make it useful.""",
        messages=[{
            "role": "user",
            "content": f"""Original question: {state['query']}

            Sub-agent reports:
            {json.dumps(reports, indent=2)}

            Synthesize these into a final recommendation."""
        }]
    )

    answer = response.content[0].text

    # Calculate overall score as weighted average
    scores = [r.get("score", 50) for r in reports.values()]
    overall = int(sum(scores) / len(scores)) if scores else 50

    return {
        "overall_score": overall,
        "recommendation": "Go" if overall >= 70 else "Caution" if overall >= 40 else "Avoid",
        "final_answer": answer
    }
```

**Substeps:**
1. Create `synthesizer.py`
2. Test with mock sub-agent reports
3. Verify it produces a clear, data-backed recommendation

---

### Step 6.8: Wire it all together in LangGraph

**File:** `backend/agents/graph.py`

```python
from langgraph.graph import StateGraph, END
from .state import GeoAgentState
from .intent_parser import parse_intent
from .demographics_agent import run_demographics_agent
from .competition_agent import run_competition_agent
from .traffic_agent import run_traffic_agent
from .zoning_agent import run_zoning_agent
from .synthesizer import synthesize

def should_run_agent(agent_name: str):
    """Create a conditional check for whether a sub-agent should run."""
    def check(state: GeoAgentState) -> str:
        if agent_name in state.get("agents_to_run", []):
            return agent_name
        return "skip"
    return check

# Build the graph
graph = StateGraph(GeoAgentState)

# Add all nodes
graph.add_node("parse_intent", parse_intent)
graph.add_node("demographics", run_demographics_agent)
graph.add_node("competition", run_competition_agent)
graph.add_node("traffic", run_traffic_agent)
graph.add_node("zoning", run_zoning_agent)
graph.add_node("synthesize", synthesize)

# Entry point
graph.set_entry_point("parse_intent")

# After parsing, run all relevant sub-agents
# (For simplicity, run them in sequence first. Parallel comes in Step 6.9)
graph.add_edge("parse_intent", "demographics")
graph.add_edge("demographics", "competition")
graph.add_edge("competition", "traffic")
graph.add_edge("traffic", "zoning")
graph.add_edge("zoning", "synthesize")
graph.add_edge("synthesize", END)

# Compile
geoagent_app = graph.compile()

def run_geoagent(query: str) -> dict:
    """Run the full multi-agent analysis."""
    result = geoagent_app.invoke({"query": query})
    return {
        "overall_score": result.get("overall_score"),
        "recommendation": result.get("recommendation"),
        "answer": result.get("final_answer"),
        "demographics": result.get("demographics_report"),
        "competition": result.get("competition_report"),
        "traffic": result.get("traffic_report"),
        "zoning": result.get("zoning_report"),
    }
```

**Substeps:**
1. Create `graph.py`
2. Test:
   ```python
   from agents.graph import run_geoagent
   result = run_geoagent("Best area for a coffee shop in downtown Kitchener")
   print(result["answer"])
   print(f"Score: {result['overall_score']}, Recommendation: {result['recommendation']}")
   ```
3. Verify all sub-agents run and the synthesis is coherent
4. Update Django views to use `run_geoagent` instead of the old `run_agent`

**Test:** End-to-end multi-agent flow works. One question triggers 4 sub-agents and a synthesis.

---

### Step 6.9: Add conditional routing (skip irrelevant agents)

**What to do:** Use LangGraph conditional edges so the orchestrator only runs relevant sub-agents.

**Update `graph.py`:**

Replace the linear edges with conditional routing based on `agents_to_run`.

```python
def route_after_parse(state: GeoAgentState) -> list[str]:
    """Return list of agents to run based on intent parsing."""
    agents = state.get("agents_to_run", [])
    # Map agent names to node names
    return [a for a in agents if a in ["demographics", "competition", "traffic", "zoning"]]
```

**Substeps:**
1. Implement conditional edges
2. Test: "Is this location zoned for commercial?" → should only run zoning agent
3. Test: "What's the competition like?" → should only run competition agent
4. Test: "Full analysis of downtown Kitchener for a bakery" → runs all agents

**Test:** Irrelevant agents are skipped. Fewer API calls = faster response.

---

### Step 6.10: Add parallel execution

**What to do:** Sub-agents that don't depend on each other should run in parallel.

**Update `graph.py`:** Use LangGraph's fan-out/fan-in pattern to run demographics, competition, traffic, and zoning in parallel, then fan back in to the synthesizer.

**Substeps:**
1. Replace sequential edges with parallel fan-out from `parse_intent`
2. Fan-in to `synthesize` after all sub-agents complete
3. Test that response time is faster (parallel sub-agents ≈ time of slowest one, not sum of all)

**Test:** Same results, but noticeably faster because sub-agents run in parallel.

---

### Phase 6 Checkpoint

You should now have:
- [x] 4 specialized sub-agents (demographics, competition, traffic, zoning)
- [x] An orchestrator that parses intent and routes to relevant agents
- [x] Conditional routing (skip irrelevant agents)
- [x] Parallel execution of independent sub-agents
- [x] Synthesis node that produces scored, explained recommendations
- [x] LangGraph managing the entire flow

**Demo:** "Should I open a coffee shop in downtown Kitchener?" triggers: intent parsing → 4 sub-agents running in parallel → synthesis → scored recommendation with reasoning.

**File structure:**
```
GeoAgent/
├── backend/
│   ├── .env
│   ├── requirements.txt
│   ├── manage.py
│   ├── geoagent_project/
│   ├── api/
│   │   ├── views.py      ← now calls run_geoagent()
│   │   ├── urls.py
│   │   └── models.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── state.py
│   │   ├── graph.py
│   │   ├── intent_parser.py
│   │   ├── demographics_agent.py
│   │   ├── competition_agent.py
│   │   ├── traffic_agent.py
│   │   ├── zoning_agent.py
│   │   └── synthesizer.py
│   ├── tools.py
│   └── db/
│       ├── schema.sql
│       ├── geo_utils.py
│       ├── geoagent.db
│       ├── load_census.py
│       └── load_pois.py
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── ChatPanel.tsx
│   │   │   ├── MapPanel.tsx
│   │   │   └── ScoreCard.tsx
│   │   └── App.css
│   └── package.json
└── PRD.md
```

---

# PHASE 7: Polish and Advanced Features (Days 39-45)

**Goal:** Add comparison mode, drill-down, history, and visual polish. Make it demo-ready.

---

### Step 7.1: Multi-location comparison

**What to do:** Allow "Compare Main Street vs King Street for a coffee shop."

**Substeps:**
1. Update intent parser to detect comparison queries
2. Run the full agent graph for EACH location
3. Return results side by side
4. Frontend: show two score cards and map pins for both locations
5. Add a comparison summary ("Location A scores higher because...")

**Test:** "Compare downtown Kitchener vs uptown Waterloo for a bakery" → two analyses side by side.

---

### Step 7.2: Drill-down follow-ups

**What to do:** Allow "Why did competition score low?" after an analysis.

**Substeps:**
1. Store the last analysis result in session/state
2. Detect follow-up questions (references to sub-scores)
3. Re-run just the relevant sub-agent with a more detailed prompt
4. Return a deeper explanation

**Test:** After analysis → "Tell me more about the demographics" → detailed demographic breakdown.

---

### Step 7.3: Analysis history page

**What to do:** A page showing all past analyses with scores.

**Substeps:**
1. Frontend: new route `/history`
2. Fetch from `GET /api/analyses/`
3. Show list with question, score, date, recommendation badge
4. Click an analysis to load it back into the chat + map

**Test:** Run 3 analyses. Go to /history. See all 3. Click one to reload it.

---

### Step 7.4: Visual polish

**Substeps:**
1. Improve chat message styling (markdown rendering for agent answers)
2. Add loading skeleton animations while agent is working
3. Custom map marker icons (red for competitors, green for complementary, blue for target)
4. Animate map pins dropping in as tool results arrive
5. Add a legend to the map
6. Responsive layout for mobile
7. Add a header with the GeoAgent logo/name

---

### Step 7.5: Deployment setup

**What to do:** Since SQLite is just a file, deployment is simple. No database server to manage.

**Substeps:**
1. Backend: Deploy to Railway (free tier) or Render
   - Set environment variables (ANTHROPIC_API_KEY)
   - Include the `geoagent.db` file in the deployment
   - `python manage.py runserver 0.0.0.0:8000`
2. Frontend: Deploy to Vercel (free tier)
   - `npm run build` produces static files
   - Point API calls to your backend URL
3. Test the full stack running in production

---

### Phase 7 Checkpoint

You should now have:
- [x] Multi-location comparison
- [x] Drill-down follow-ups
- [x] Analysis history
- [x] Polished UI with animations and custom markers
- [x] Simple deployment (no Docker needed)
- [x] A complete, demo-ready product

---

# Summary: What You're Building at Each Phase

| Phase | What Works | Can Demo? |
|-------|-----------|-----------|
| 1 | Chat with Claude in terminal | Yes (terminal) |
| 2 | Agent calls tools, gives scored recommendations | Yes (terminal) |
| 3 | Real SQLite data, real business names, real demographics | Yes (terminal) |
| 4 | Django API serving agent responses with streaming | Yes (curl/Postman) |
| 5 | React chat + Leaflet map with live agent | Yes (browser!) |
| 6 | Multi-agent orchestration with LangGraph | Yes (browser, faster + smarter) |
| 7 | Comparison, history, polish, deployment | Yes (production-ready) |

---

# Key Principle

**Every phase produces something you can run and show someone.**

You are never more than a few days away from a working demo. If you get stuck on Phase 6, you still have a working Phase 5 app. If data loading is giving you trouble in Phase 3, you still have mock data from Phase 2.

Build small. Test constantly. Expand when it works.

---

# Free Resources

| Resource | What For | Link |
|----------|----------|------|
| Claude API free tier | LLM calls | console.anthropic.com |
| Statistics Canada | Census data | www12.statcan.gc.ca |
| Overture Maps | POI data | overturemaps.org |
| OpenStreetMap | Map tiles + road data | openstreetmap.org |
| Geofabrik | OSM data downloads | download.geofabrik.de |
| City of Kitchener Open Data | Zoning data | open-kitchener.opendata.arcgis.com |
| SQLite | Database (built into Python) | sqlite.org |
| Vercel | Frontend hosting (free tier) | vercel.com |
| Railway | Backend hosting (free tier) | railway.app |
