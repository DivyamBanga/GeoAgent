"""
GeoAgent LangGraph — conditional routing with fan-out/fan-in.

Flow:
  parse_intent → [conditional routing] → only selected sub-agents → synthesize → END

The intent parser decides which agents to run. The graph uses conditional edges
to fan-out only to relevant sub-agents, then fans back in to the synthesizer.
Agents not selected are never called (no wasted API calls).
"""

from langgraph.graph import StateGraph, END
from .state import GeoAgentState
from .intent_parser import parse_intent
from .demographics_agent import run_demographics_agent
from .competition_agent import run_competition_agent
from .traffic_agent import run_traffic_agent
from .zoning_agent import run_zoning_agent
from .synthesizer import synthesize


# --- Router: decides which sub-agents to run ---

VALID_AGENTS = ["demographics", "competition", "traffic", "zoning"]


def route_after_parse(state: GeoAgentState) -> list[str]:
    """Return list of agent nodes to run based on intent parsing."""
    agents = state.get("agents_to_run", [])
    selected = [a for a in agents if a in VALID_AGENTS]
    if not selected:
        # If no agents selected, skip straight to synthesize
        return ["synthesize"]
    return selected


# --- Build the graph ---

graph = StateGraph(GeoAgentState)

# Register nodes
graph.add_node("parse_intent", parse_intent)
graph.add_node("demographics", run_demographics_agent)
graph.add_node("competition", run_competition_agent)
graph.add_node("traffic", run_traffic_agent)
graph.add_node("zoning", run_zoning_agent)
graph.add_node("synthesize", synthesize)

# Entry point
graph.set_entry_point("parse_intent")

# Conditional fan-out: parse_intent routes to selected sub-agents (or directly to synthesize)
graph.add_conditional_edges(
    "parse_intent",
    route_after_parse,
    ["demographics", "competition", "traffic", "zoning", "synthesize"],
)

# Fan-in: all sub-agents feed into synthesize
graph.add_edge("demographics", "synthesize")
graph.add_edge("competition", "synthesize")
graph.add_edge("traffic", "synthesize")
graph.add_edge("zoning", "synthesize")

# Synthesize → done
graph.add_edge("synthesize", END)

# Compile into a runnable app
geoagent_app = graph.compile()


def run_geoagent(query: str) -> dict:
    """Run the full multi-agent analysis pipeline."""
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


# --- Standalone test ---
if __name__ == "__main__":
    import json
    import time

    tests = [
        ("Full analysis", "Best area for a coffee shop in downtown Kitchener"),
        ("Zoning only", "Is uptown Waterloo zoned for commercial use?"),
        ("Competition only", "What's the competition like for bakeries near King Street?"),
    ]

    for label, query in tests:
        print(f"\n{'='*60}")
        print(f"  TEST: {label}")
        print(f"  Query: \"{query}\"")
        print(f"{'='*60}")

        start = time.time()
        result = run_geoagent(query)
        elapsed = time.time() - start

        print(f"\n  Score: {result['overall_score']}/100 | {result['recommendation']}")
        print(f"  Time: {elapsed:.1f}s")
        print(f"  Agents that ran:")
        if result["demographics"]:
            print(f"    Demographics: {result['demographics'].get('score')}/100")
        if result["competition"]:
            print(f"    Competition:  {result['competition'].get('score')}/100")
        if result["traffic"]:
            print(f"    Traffic:      {result['traffic'].get('score')}/100")
        if result["zoning"]:
            print(f"    Zoning:       {result['zoning'].get('score')}/100")

        skipped = []
        if not result["demographics"]:
            skipped.append("demographics")
        if not result["competition"]:
            skipped.append("competition")
        if not result["traffic"]:
            skipped.append("traffic")
        if not result["zoning"]:
            skipped.append("zoning")
        if skipped:
            print(f"  Skipped: {skipped}")
