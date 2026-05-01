"""
GeoAgent State — the TypedDict that flows through the entire LangGraph.

Every node in the graph receives this state and returns updates to it.
Fields get populated as the graph executes:

  1. Intent parser fills: lat, lng, business_type, radius_km, agents_to_run
  2. Sub-agents fill: demographics_report, competition_report, traffic_report, zoning_report
  3. Synthesizer fills: overall_score, recommendation, final_answer
"""

from typing import TypedDict, Optional


class SubAgentReport(TypedDict):
    """Standardized output from each sub-agent."""
    score: int              # 0-100
    summary: str            # 1-2 sentence summary
    details: dict           # raw data from tools
    factors_positive: list  # what's good about this location
    factors_negative: list  # what's risky about this location


class GeoAgentState(TypedDict):
    # --- Input (set by the user / API) ---
    query: str

    # --- Parsed intent (set by intent_parser node) ---
    lat: float
    lng: float
    business_type: str
    radius_km: float

    # --- Routing (set by intent_parser node) ---
    agents_to_run: list  # e.g. ["demographics", "competition", "traffic", "zoning"]

    # --- Sub-agent reports (each set by its respective agent node) ---
    demographics_report: Optional[SubAgentReport]
    competition_report: Optional[SubAgentReport]
    traffic_report: Optional[SubAgentReport]
    zoning_report: Optional[SubAgentReport]

    # --- Final output (set by synthesizer node) ---
    overall_score: Optional[int]
    recommendation: Optional[str]   # "Go" / "Caution" / "Avoid"
    final_answer: Optional[str]
