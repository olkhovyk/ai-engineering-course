from langgraph.graph import END, StateGraph

from src.agent.nodes import decompose, explain, initialize, should_continue
from src.agent.state import AgentState


def build_graph() -> StateGraph:
    """Build the LangGraph workflow for concept decomposition."""
    graph = StateGraph(AgentState)

    graph.add_node("initialize", initialize)
    graph.add_node("decompose", decompose)
    graph.add_node("explain", explain)

    graph.set_entry_point("initialize")
    graph.add_edge("initialize", "decompose")
    graph.add_edge("decompose", "explain")

    graph.add_conditional_edges(
        "explain",
        should_continue,
        {
            "continue": "decompose",
            "done": END,
        },
    )

    return graph.compile()


def run_decomposition(topic: str, user_level: str = "beginner", max_depth: int = 3) -> AgentState:
    """Run the full decomposition pipeline."""
    app = build_graph()
    result = app.invoke({
        "topic": topic,
        "user_level": user_level,
        "max_depth": max_depth,
        "knowledge_graph": None,
        "current_concept_id": "",
        "pending_concept_ids": [],
        "messages": [],
    })
    return result


def expand_concept(state: AgentState, concept_id: str) -> AgentState:
    """Expand a single concept node (drill-down)."""
    app = build_graph()
    kg = state["knowledge_graph"]
    # Reset pending to just this concept
    state["pending_concept_ids"] = [concept_id]
    # Skip initialize — go directly to decompose
    graph = StateGraph(AgentState)
    graph.add_node("decompose", decompose)
    graph.add_node("explain", explain)
    graph.set_entry_point("decompose")
    graph.add_edge("decompose", "explain")
    graph.add_conditional_edges(
        "explain",
        should_continue,
        {"continue": "decompose", "done": "__end__"},
    )
    expand_app = graph.compile()
    return expand_app.invoke(state)
