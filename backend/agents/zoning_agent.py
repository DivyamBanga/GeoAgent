"""
Zoning Sub-Agent — checks whether a business type is permitted at a location.

Uses the check_zoning tool to query land-use data and determine if the proposed
business is allowed under local zoning rules.

Returns a standardized SubAgentReport with score, summary, and factors.
"""

import json
import os
import sys
import anthropic
from dotenv import load_dotenv
from .state import GeoAgentState, SubAgentReport

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tools import check_zoning

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = anthropic.Anthropic()

TOOLS = [
    {
        "name": "check_zoning",
        "description": "Check the zoning classification at a location and whether a specific business type is permitted. Returns zone code, zone type, permitted uses, and whether the business is allowed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "Latitude of the location"},
                "lng": {"type": "number", "description": "Longitude of the location"},
                "business_type": {
                    "type": "string",
                    "description": "Type of business to check (e.g. 'coffee_shop', 'restaurant', 'gym', 'bakery')"
                }
            },
            "required": ["lat", "lng", "business_type"]
        }
    }
]

TOOL_FNS = {
    "check_zoning": check_zoning,
}

SYSTEM_PROMPT = """You are a zoning and land-use analyst sub-agent for a location intelligence system.
Your job: use the check_zoning tool to determine if the proposed business is permitted at the
target location under local zoning regulations.

After gathering data, return ONLY valid JSON with this structure:
{
    "score": <0-100 integer>,
    "summary": "<1-2 sentence evaluation of zoning suitability>",
    "details": {<raw zoning data>},
    "factors_positive": ["<list of zoning advantages>"],
    "factors_negative": ["<list of zoning risks or restrictions>"]
}

Scoring guidelines:
- Business explicitly permitted in zone: 85-95
- Zone is commercial/mixed but business not explicitly listed: 60-75 (likely OK with permit)
- Zone is residential: 10-25 (very unlikely to be permitted)
- Zone is industrial: 15-30 (wrong area for most retail)
- Mixed-use zones are generally positive for retail/food businesses
- Note: zoning data comes from OpenStreetMap land-use which is approximate.
  If the area has mixed zone types nearby, acknowledge the uncertainty."""


def run_zoning_agent(state: GeoAgentState) -> dict:
    """Zoning sub-agent: checks if business type is permitted at location."""
    messages = [{
        "role": "user",
        "content": (
            f"Check the zoning for a {state['business_type']} at "
            f"lat={state['lat']}, lng={state['lng']}. "
            f"Determine if this business type is permitted at this location."
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
            "summary": text[:200] if text else "Zoning analysis completed but response parsing failed.",
            "details": {},
            "factors_positive": [],
            "factors_negative": ["Unable to parse structured response"]
        }

    return {"zoning_report": report}


# --- Standalone test ---
if __name__ == "__main__":
    test_state = {
        "query": "coffee shop in downtown Kitchener",
        "business_type": "coffee_shop",
        "lat": 43.4516,
        "lng": -80.4925,
        "radius_km": 2.0,
        "agents_to_run": ["zoning"],
    }

    print("Running zoning agent...")
    print(f"Location: lat={test_state['lat']}, lng={test_state['lng']}")
    print(f"Business: {test_state['business_type']}")
    print("-" * 50)

    result = run_zoning_agent(test_state)
    report = result["zoning_report"]

    print(f"\nScore: {report['score']}/100")
    print(f"Summary: {report['summary']}")
    print(f"\nPositive factors:")
    for f in report.get("factors_positive", []):
        print(f"  + {f}")
    print(f"\nNegative factors:")
    for f in report.get("factors_negative", []):
        print(f"  - {f}")
    print(f"\nDetails: {json.dumps(report.get('details', {}), indent=2)}")
