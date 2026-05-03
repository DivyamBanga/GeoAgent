"""
GeoAgent LangGraph — wires all nodes together into a single executable graph.

Flow:
  parse_intent -> demographics -> competition -> traffic -> zoning -> synthesize -> END

Each sub-agent checks if it's in state["agents_to_run"] and skips gracefully if not.
"""

from langgraph.graph import StateGraph, END
from .state import GeoAgentState
from .intent_parser import parse_intent
from .demographics_agent import run_demographics_agent
from .competition_agent import run_competition_agent
from .traffic_agent import run_traffic_agent
from .zoning_agent import run_zoning_agent
from .synthesizer import synthesize


# --- Wrapper nodes that skip if not needed ---

def demographics_node(state: GeoAgentState) -> dict:
    if "demographics" not in state.get("agents_to_run", []):
        return {}
    return run_demographics_agent(state)


def competition_node(state: GeoAgentState) -> dict:
    if "competition" not in state.get("agents_to_run", []):
        return {}
    return run_competition_agent(state)


def traffic_node(state: GeoAgentState) -> dict:
    if "traffic" not in state.get("agents_to_run", []):
        return {}
    return run_traffic_agent(state)


def zoning_node(state: GeoAgentState) -> dict:
    if "zoning" not in state.get("agents_to_run", []):
        return {}
    return run_zoning_agent(state)


# --- Build the graph ---

graph = StateGraph(GeoAgentState)

# Register nodes
graph.add_node("parse_intent", parse_intent)
graph.add_node("demographics", demographics_node)
graph.add_node("competition", competition_node)
graph.add_node("traffic", traffic_node)
graph.add_node("zoning", zoning_node)
graph.add_node("synthesize", synthesize)

# Wire edges (linear sequence for now)
graph.set_entry_point("parse_intent")
graph.add_edge("parse_intent", "demographics")
graph.add_edge("demographics", "competition")
graph.add_edge("competition", "traffic")
graph.add_edge("traffic", "zoning")
graph.add_edge("zoning", "synthesize")
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

    query = "Best area for a coffee shop in downtown Kitchener"
    print(f"Query: \"{query}\"")
    print("=" * 60)
    print("Running GeoAgent graph...")
    print()

    result = run_geoagent(query)

    print(f"Score: {result['overall_score']}/100")
    print(f"Recommendation: {result['recommendation']}")
    print()
    print("Sub-agent scores:")
    if result["demographics"]:
        print(f"  Demographics: {result['demographics'].get('score')}/100")
    if result["competition"]:
        print(f"  Competition:  {result['competition'].get('score')}/100")
    if result["traffic"]:
        print(f"  Traffic:      {result['traffic'].get('score')}/100")
    if result["zoning"]:
        print(f"  Zoning:       {result['zoning'].get('score')}/100")
    print()
    print("Final Answer:")
    print(result["answer"])
