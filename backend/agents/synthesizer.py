"""
Synthesizer Node — final node in the GeoAgent LangGraph.

Collects all sub-agent reports, calculates an overall score,
and uses Claude to produce a clear, actionable recommendation.
"""

import json
import os
import sys
import anthropic
from dotenv import load_dotenv
from .state import GeoAgentState

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are a senior location intelligence analyst synthesizing multiple sub-agent reports
into a final recommendation for the user.

Provide a clear, actionable response with:
1. Overall score (0-100) — weighted average of sub-scores
2. Recommendation: "Go" (score 70+), "Caution" (40-69), "Avoid" (<40)
3. Top 3 positive factors across all reports
4. Top 3 risks across all reports
5. A clear, actionable 2-3 paragraph summary

Be specific. Cite numbers from the reports. Make it useful for someone deciding
whether to open a business at this location. Do NOT use markdown headers or bullet
points — write in clear prose paragraphs with the key data points embedded."""


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

    # Calculate overall score as weighted average
    scores = [r.get("score", 50) for r in reports.values()]
    overall = int(sum(scores) / len(scores)) if scores else 50
    recommendation = "Go" if overall >= 70 else "Caution" if overall >= 40 else "Avoid"

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f"Original question: {state['query']}\n"
                f"Business type: {state.get('business_type', 'unknown')}\n"
                f"Location: ({state.get('lat')}, {state.get('lng')})\n"
                f"Overall score: {overall}/100\n"
                f"Recommendation: {recommendation}\n\n"
                f"Sub-agent reports:\n{json.dumps(reports, indent=2)}\n\n"
                f"Synthesize these into a final recommendation."
            )
        }]
    )

    answer = response.content[0].text

    return {
        "overall_score": overall,
        "recommendation": recommendation,
        "final_answer": answer,
    }


# --- Standalone test ---
if __name__ == "__main__":
    # Test with mock sub-agent reports (no API calls to sub-agents needed)
    mock_state = {
        "query": "Where should I open a coffee shop in downtown Kitchener?",
        "business_type": "coffee_shop",
        "lat": 43.4516,
        "lng": -80.4925,
        "radius_km": 2.0,
        "agents_to_run": ["demographics", "competition", "traffic", "zoning"],
        "demographics_report": {
            "score": 88,
            "summary": "Strong population (40,885) and good income ($72,709).",
            "details": {"population": 40885, "avg_median_income": 72709},
            "factors_positive": ["Large population base", "Above-average income"],
            "factors_negative": ["Some income variance across areas"],
        },
        "competition_report": {
            "score": 15,
            "summary": "Highly saturated market with 20 coffee shops within 2km.",
            "details": {"direct_competitors": 20, "nearest_competitor_m": 65},
            "factors_positive": ["Proven demand"],
            "factors_negative": ["20 direct competitors", "Starbucks 65m away"],
        },
        "traffic_report": {
            "score": 98,
            "summary": "Excellent access — King St arterial + LRT + bus terminal.",
            "details": {"nearest_arterial_km": 0.064, "transit_stops": 14},
            "factors_positive": ["Major arterial 64m away", "LRT station 201m", "14 transit stops"],
            "factors_negative": [],
        },
        "zoning_report": {
            "score": 90,
            "summary": "Commercial zone, coffee shop explicitly permitted.",
            "details": {"zone_type": "commercial", "is_permitted": True},
            "factors_positive": ["Explicitly permitted use", "Commercial zone"],
            "factors_negative": ["Mixed zone boundaries nearby"],
        },
    }

    print("Running synthesizer with mock reports...")
    print(f"Scores: demo={mock_state['demographics_report']['score']}, "
          f"comp={mock_state['competition_report']['score']}, "
          f"traffic={mock_state['traffic_report']['score']}, "
          f"zoning={mock_state['zoning_report']['score']}")
    print("-" * 60)

    result = synthesize(mock_state)

    print(f"\nOverall Score: {result['overall_score']}/100")
    print(f"Recommendation: {result['recommendation']}")
    print(f"\nFinal Answer:\n{result['final_answer']}")
