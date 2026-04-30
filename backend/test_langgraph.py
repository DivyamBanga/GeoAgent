"""
LangGraph Hello World — Phase 6.1

Tests the 3 core concepts:
  1. State:  A TypedDict that flows through the graph. Every node reads/writes to it.
  2. Nodes:  Python functions that take state, do work, return updated state.
  3. Edges:  Define which node runs after which. Can be conditional.

Run: python test_langgraph.py
"""

from langgraph.graph import StateGraph
from typing import TypedDict


# --- 1. STATE ---
# This is just a Python dict with type hints.
# Every node in the graph receives this and returns updates to it.
class State(TypedDict):
    message: str
    steps_completed: int


# --- 2. NODES ---
# Each node is a plain function: takes state in, returns a dict of updates.
def step_one(state: State) -> dict:
    print(f"  [step_one] Received: '{state['message']}'")
    return {
        "message": state["message"] + " -> step one done",
        "steps_completed": state["steps_completed"] + 1,
    }


def step_two(state: State) -> dict:
    print(f"  [step_two] Received: '{state['message']}'")
    return {
        "message": state["message"] + " -> step two done",
        "steps_completed": state["steps_completed"] + 1,
    }


# --- 3. BUILD THE GRAPH (EDGES) ---
graph = StateGraph(State)

# Register nodes
graph.add_node("step_one", step_one)
graph.add_node("step_two", step_two)

# Wire edges: step_one -> step_two
graph.add_edge("step_one", "step_two")

# Set entry and finish
graph.set_entry_point("step_one")
graph.set_finish_point("step_two")

# Compile into a runnable app
app = graph.compile()

# --- RUN IT ---
if __name__ == "__main__":
    print("Running LangGraph hello-world...\n")

    result = app.invoke({"message": "start", "steps_completed": 0})

    print(f"\nFinal state:")
    print(f"  message:         '{result['message']}'")
    print(f"  steps_completed: {result['steps_completed']}")

    # Verify correctness
    expected_message = "start -> step one done -> step two done"
    expected_steps = 2
    assert result["message"] == expected_message, f"Expected '{expected_message}', got '{result['message']}'"
    assert result["steps_completed"] == expected_steps, f"Expected {expected_steps}, got {result['steps_completed']}"

    print("\nAll assertions passed. LangGraph is working!")
