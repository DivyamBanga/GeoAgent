"""
Traffic Sub-Agent — analyzes road infrastructure and transit accessibility.

Uses get_nearby_roads and get_nearest_transit tools to evaluate how accessible
a location is by car and public transit.

Returns a standardized SubAgentReport with score, summary, and factors.
"""

import json
import os
import sys
import anthropic
from dotenv import load_dotenv
from .state import GeoAgentState, SubAgentReport

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tools import get_nearby_roads, get_nearest_transit

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = anthropic.Anthropic()

TOOLS = [
    {
        "name": "get_nearby_roads",
        "description": "Get road infrastructure within a radius. Returns road counts by class (highway, arterial, collector, residential), nearest arterial distance, and major road names.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "Latitude of the center point"},
                "lng": {"type": "number", "description": "Longitude of the center point"},
                "radius_km": {"type": "number", "description": "Radius in kilometers to search within"}
            },
            "required": ["lat", "lng", "radius_km"]
        }
    },
    {
        "name": "get_nearest_transit",
        "description": "Find nearest transit stops (bus stations, LRT stations, train stations) within a radius. Returns stop names, types, and distances.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "Latitude of the center point"},
                "lng": {"type": "number", "description": "Longitude of the center point"},
                "radius_km": {"type": "number", "description": "Radius in kilometers to search within"}
            },
            "required": ["lat", "lng", "radius_km"]
        }
    }
]

TOOL_FNS = {
    "get_nearby_roads": get_nearby_roads,
    "get_nearest_transit": get_nearest_transit,
}

SYSTEM_PROMPT = """You are a traffic and accessibility analyst sub-agent for a location intelligence system.
Your job: use your tools to evaluate road infrastructure and transit access at the target location,
then assess how well-served the location is for customer traffic (both car and public transit).

Call both tools to get a complete picture of accessibility.

After gathering data, return ONLY valid JSON with this structure:
{
    "score": <0-100 integer>,
    "summary": "<1-2 sentence evaluation of traffic/accessibility>",
    "details": {<raw data summary>},
    "factors_positive": ["<list of accessibility strengths>"],
    "factors_negative": ["<list of accessibility weaknesses>"]
}

Scoring guidelines:
- Arterial road within 100m: high visibility, easy car access (+20)
- Multiple transit stops within 500m: excellent walk-in traffic (+25)
- LRT/subway station nearby: significant bonus (+15)
- No transit within 1km: major negative for foot traffic
- Highway-only access (no arterials): bad for walk-ins
- Mix of road classes indicates well-connected area
- Consider the business type: restaurants need foot traffic, warehouses need highway access"""


def run_traffic_agent(state: GeoAgentState) -> dict:
    """Traffic sub-agent: analyzes road and transit accessibility."""
    messages = [{
        "role": "user",
        "content": (
            f"Analyze the traffic and accessibility for a {state['business_type']} at "
            f"lat={state['lat']}, lng={state['lng']}, radius={state['radius_km']}km. "
            f"Check both road infrastructure and public transit access."
        )
    }]

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=messages
    )

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

    text_blocks = [b.text for b in response.content if hasattr(b, "text")]
    text = text_blocks[0] if text_blocks else ""

    clean = text.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1]
        clean = clean.rsplit("```", 1)[0]
        clean = clean.strip()

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
            "summary": text[:200] if text else "Traffic analysis completed but response parsing failed.",
            "details": {},
            "factors_positive": [],
            "factors_negative": ["Unable to parse structured response"]
        }

    return {"traffic_report": report}


# --- Standalone test ---
if __name__ == "__main__":
    test_state = {
        "query": "coffee shop in downtown Kitchener",
        "business_type": "coffee_shop",
        "lat": 43.4516,
        "lng": -80.4925,
        "radius_km": 2.0,
        "agents_to_run": ["traffic"],
    }

    print("Running traffic agent...")
    print(f"Location: lat={test_state['lat']}, lng={test_state['lng']}")
    print(f"Business: {test_state['business_type']}")
    print(f"Radius: {test_state['radius_km']}km")
    print("-" * 50)

    result = run_traffic_agent(test_state)
    report = result["traffic_report"]

    print(f"\nScore: {report['score']}/100")
    print(f"Summary: {report['summary']}")
    print(f"\nPositive factors:")
    for f in report.get("factors_positive", []):
        print(f"  + {f}")
    print(f"\nNegative factors:")
    for f in report.get("factors_negative", []):
        print(f"  - {f}")
    print(f"\nDetails: {json.dumps(report.get('details', {}), indent=2)}")
