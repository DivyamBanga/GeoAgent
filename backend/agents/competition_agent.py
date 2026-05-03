"""
Competition Sub-Agent — analyzes nearby competitors for a location.

Uses the find_competitors tool to identify competing businesses within the radius,
then has Claude evaluate market saturation and competitive positioning.

Returns a standardized SubAgentReport with score, summary, and factors.
"""

import json
import os
import sys
import anthropic
from dotenv import load_dotenv
from .state import GeoAgentState, SubAgentReport

# Ensure the backend directory is on the path so we can import tools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tools import find_competitors

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = anthropic.Anthropic()

TOOLS = [
    {
        "name": "find_competitors",
        "description": "Find competing businesses of a given type within a radius. Returns a list of competitors with names, categories, and distances in meters.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "Latitude of the center point"},
                "lng": {"type": "number", "description": "Longitude of the center point"},
                "business_type": {
                    "type": "string",
                    "description": "Category of business to search for (e.g. 'coffee_shop', 'gym', 'bakery', 'restaurant')"
                },
                "radius_km": {"type": "number", "description": "Radius in kilometers to search within"}
            },
            "required": ["lat", "lng", "business_type", "radius_km"]
        }
    }
]

TOOL_FNS = {
    "find_competitors": find_competitors,
}

SYSTEM_PROMPT = """You are a competition analyst sub-agent for a location intelligence system.
Your job: use the find_competitors tool to identify competing businesses near the target location,
then evaluate the competitive landscape for the given business type.

You may call find_competitors multiple times with different business_type values to check
for both direct competitors AND closely related businesses. For example:
- For a coffee_shop: also check "cafe", "bakery", "bubble_tea"
- For a gym: also check "yoga_studio", "pilates_studio", "boxing_gym"
- For a restaurant: also check the specific cuisine type and "fast_food_restaurant"
- For a bakery: also check "cafe", "coffee_shop", "desserts"

After gathering data, return ONLY valid JSON with this structure:
{
    "score": <0-100 integer>,
    "summary": "<1-2 sentence evaluation of competitive landscape>",
    "details": {
        "direct_competitors": <count of same-type businesses>,
        "related_competitors": <count of related businesses>,
        "nearest_competitor_m": <distance to nearest in meters>,
        "competitors_list": [<top competitors with names and distances>]
    },
    "factors_positive": ["<list of competitive advantages>"],
    "factors_negative": ["<list of competitive risks>"]
}

Scoring guidelines:
- 0 direct competitors in radius: 95-100 (blue ocean, but verify there's demand)
- 1-3 competitors: 70-85 (healthy market, proven demand)
- 4-7 competitors: 40-60 (crowded, need differentiation)
- 8+ competitors: 10-30 (saturated market)
- Nearest competitor < 100m: significant penalty
- Nearest competitor > 500m: bonus (breathing room)
- Related businesses nearby can be positive (foot traffic) or negative (substitutes)"""


def run_competition_agent(state: GeoAgentState) -> dict:
    """Competition sub-agent: analyzes nearby competitors for the location."""
    messages = [{
        "role": "user",
        "content": (
            f"Analyze the competition for a {state['business_type']} at "
            f"lat={state['lat']}, lng={state['lng']}, radius={state['radius_km']}km. "
            f"Search for direct competitors and closely related businesses. "
            f"Evaluate market saturation and competitive positioning."
        )
    }]

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=messages
    )

    # Tool-use loop — keep calling tools until Claude gives a final text answer
    while response.stop_reason == "tool_use":
        tool_results = []
        assistant_content = response.content

        for block in assistant_content:
            if block.type == "tool_use":
                fn = TOOL_FNS[block.name]
                result = fn(**block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result)
                })

        messages.append({"role": "assistant", "content": assistant_content})
        messages.append({"role": "user", "content": tool_results})

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

    # Extract the final text response and parse as JSON
    text_blocks = [b.text for b in response.content if hasattr(b, "text")]
    text = text_blocks[0] if text_blocks else ""

    # Handle markdown fences if present
    clean = text.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1]
        clean = clean.rsplit("```", 1)[0]
        clean = clean.strip()

    # Try to extract JSON object if there's surrounding text
    if clean and not clean.startswith("{"):
        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start != -1 and end > start:
            clean = clean[start:end]

    try:
        report = json.loads(clean)
    except (json.JSONDecodeError, ValueError):
        report = {
            "score": 50,
            "summary": text[:200] if text else "Competition analysis completed but response parsing failed.",
            "details": {},
            "factors_positive": [],
            "factors_negative": ["Unable to parse structured response"]
        }

    return {"competition_report": report}


# --- Standalone test ---
if __name__ == "__main__":
    test_state = {
        "query": "coffee shop in downtown Kitchener",
        "business_type": "coffee_shop",
        "lat": 43.4516,
        "lng": -80.4925,
        "radius_km": 2.0,
        "agents_to_run": ["competition"],
    }

    print("Running competition agent...")
    print(f"Location: lat={test_state['lat']}, lng={test_state['lng']}")
    print(f"Business: {test_state['business_type']}")
    print(f"Radius: {test_state['radius_km']}km")
    print("-" * 50)

    result = run_competition_agent(test_state)
    report = result["competition_report"]

    print(f"\nScore: {report['score']}/100")
    print(f"Summary: {report['summary']}")
    print(f"\nPositive factors:")
    for f in report.get("factors_positive", []):
        print(f"  + {f}")
    print(f"\nNegative factors:")
    for f in report.get("factors_negative", []):
        print(f"  - {f}")
    print(f"\nDetails: {json.dumps(report.get('details', {}), indent=2)}")
