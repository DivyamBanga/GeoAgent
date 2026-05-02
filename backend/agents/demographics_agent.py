"""
Demographics Sub-Agent — analyzes population and income data for a location.

Uses the get_population and get_median_income tools to gather real census data,
then has Claude evaluate how well the demographics support the given business type.

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
from tools import get_population, get_median_income

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = anthropic.Anthropic()

TOOLS = [
    {
        "name": "get_population",
        "description": "Get population within radius of a point. Returns population count, average median income, average age, and number of census areas covered.",
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
        "name": "get_median_income",
        "description": "Get median household income from the nearest census dissemination area. Returns income, population, and average age for that area.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "Latitude of the point"},
                "lng": {"type": "number", "description": "Longitude of the point"}
            },
            "required": ["lat", "lng"]
        }
    }
]

TOOL_FNS = {
    "get_population": get_population,
    "get_median_income": get_median_income,
}

SYSTEM_PROMPT = """You are a demographics analyst sub-agent for a location intelligence system.
Your job: use your tools to gather population and income data, then evaluate how well
the demographics support the given business type at the given location.

After gathering data, return ONLY valid JSON with this structure:
{
    "score": <0-100 integer>,
    "summary": "<1-2 sentence evaluation>",
    "details": {<raw data you collected>},
    "factors_positive": ["<list of demographic strengths>"],
    "factors_negative": ["<list of demographic weaknesses>"]
}

Scoring guidelines:
- Population > 20,000 in radius: strong positive
- Population 10,000-20,000: moderate
- Population < 5,000: weak
- High median income (>$70k): positive for premium businesses
- Low median income (<$40k): negative for premium, positive for budget businesses
- Consider how the business type matches the demographics"""


def run_demographics_agent(state: GeoAgentState) -> dict:
    """Demographics sub-agent: analyzes population and income for the location."""
    messages = [{
        "role": "user",
        "content": (
            f"Analyze the demographics for a {state['business_type']} at "
            f"lat={state['lat']}, lng={state['lng']}, radius={state['radius_km']}km. "
            f"Use your tools to get population and income data, then evaluate the location."
        )
    }]

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=messages
    )

    # Tool-use loop — keep calling tools until Claude gives a final text answer
    while response.stop_reason == "tool_use":
        # Process ALL tool calls in this response
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
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

    # Extract the final text response and parse as JSON
    text = next(b.text for b in response.content if hasattr(b, "text"))

    # Handle markdown fences if present
    clean = text.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1]
        clean = clean.rsplit("```", 1)[0]
        clean = clean.strip()

    report = json.loads(clean)

    return {"demographics_report": report}


# --- Standalone test ---
if __name__ == "__main__":
    test_state = {
        "query": "coffee shop in downtown Kitchener",
        "business_type": "coffee_shop",
        "lat": 43.45,
        "lng": -80.49,
        "radius_km": 2.0,
        "agents_to_run": ["demographics"],
    }

    print("Running demographics agent...")
    print(f"Location: lat={test_state['lat']}, lng={test_state['lng']}")
    print(f"Business: {test_state['business_type']}")
    print(f"Radius: {test_state['radius_km']}km")
    print("-" * 50)

    result = run_demographics_agent(test_state)
    report = result["demographics_report"]

    print(f"\nScore: {report['score']}/100")
    print(f"Summary: {report['summary']}")
    print(f"\nPositive factors:")
    for f in report.get("factors_positive", []):
        print(f"  + {f}")
    print(f"\nNegative factors:")
    for f in report.get("factors_negative", []):
        print(f"  - {f}")
    print(f"\nRaw details: {json.dumps(report.get('details', {}), indent=2)}")
