"""
Intent Parser Node — first node in the GeoAgent LangGraph.

Takes the raw user question and uses Claude to extract structured intent:
  - business_type: what kind of business (e.g. "coffee_shop")
  - lat/lng: geographic coordinates for the analysis
  - radius_km: how far to search around the point
  - agents_to_run: which sub-agents are relevant to the query
"""

import json
import os
import anthropic
from dotenv import load_dotenv
from .state import GeoAgentState

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = anthropic.Anthropic()

INTENT_SYSTEM_PROMPT = """Extract structured info from the user's location question.
Return JSON with:
- business_type: what kind of business (e.g. "coffee_shop", "restaurant", "gym", "retail")
- lat: latitude (if mentioned or inferable, else null)
- lng: longitude (if mentioned or inferable, else null)
- radius_km: analysis radius in kilometers (default 2.0)
- agents_needed: list from ["demographics", "competition", "traffic", "zoning"]
  Choose which agents are relevant to the question. Guidelines:
  - demographics: always include — population and income matter for any business
  - competition: include when the user cares about nearby competitors or saturation
  - traffic: include when foot traffic, road access, or visibility matters
  - zoning: include when the user is asking about opening a NEW business (need to check if allowed)

Known locations in Kitchener-Waterloo:
- Downtown Kitchener: 43.4516, -80.4925
- Uptown Waterloo: 43.4643, -80.5204
- King Street Kitchener: 43.4530, -80.4930
- University of Waterloo area: 43.4723, -80.5449
- Fairview Park Mall area: 43.4255, -80.4370
- Stanley Park area: 43.4480, -80.4720
- Belmont Village: 43.4525, -80.4815

Return ONLY valid JSON, no other text."""


def parse_intent(state: GeoAgentState) -> dict:
    """
    Extract business type, location, and which agents to run from the user's query.

    This is a LangGraph node — it receives the full state and returns
    a dict of fields to update.
    """
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        system=INTENT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": state["query"]}],
    )

    raw_text = response.content[0].text

    # Parse the JSON response, stripping markdown fences if present
    clean = raw_text.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1]  # remove opening fence line
        clean = clean.rsplit("```", 1)[0]  # remove closing fence
        clean = clean.strip()

    parsed = json.loads(clean)

    return {
        "business_type": parsed.get("business_type", "retail"),
        "lat": parsed.get("lat") or 43.45,
        "lng": parsed.get("lng") or -80.49,
        "radius_km": parsed.get("radius_km") or 2.0,
        "agents_to_run": parsed.get("agents_needed", ["demographics", "competition"]),
    }


# --- Standalone test ---
if __name__ == "__main__":
    test_queries = [
        "Where should I open a coffee shop in downtown Kitchener?",
        "Is uptown Waterloo a good spot for a gym?",
        "What's the population near the University of Waterloo?",
    ]

    for q in test_queries:
        print(f"\nQuery: {q}")
        result = parse_intent({"query": q})
        print(json.dumps(result, indent=2))
