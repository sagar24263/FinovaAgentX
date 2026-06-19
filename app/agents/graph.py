"""
LangGraph workflow — the main agent graph.

Flow:
  classify_intent → route → sub-agent → confidence check → (end | fallback → other agent → end)
"""

from langgraph.graph import END, StateGraph

from app.agents.state import AgentState
from app.agents.router_agent import classify_intent, route_by_intent, should_fallback
from app.agents.generic_agent import run_generic_agent
from app.agents.nfo_funds_agent import run_nfo_funds_agent
from app.utils.logger import get_logger

logger = get_logger("agent_graph")


def _route_after_check(state: AgentState) -> str:
    """After confidence check, decide end or fallback."""
    return should_fallback(state)


def _route_fallback(state: AgentState) -> str:
    """Route fallback to the other agent."""
    attempted = state.get("attempted_agents", [])

    if "generic_investment" not in attempted:
        return "generic_agent"
    elif "nfo_funds" not in attempted:
        return "nfo_funds_agent"

    # Both attempted, just end
    return "end_node"


def build_graph() -> StateGraph:
    """Build and compile the LangGraph agent workflow."""

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("classify", classify_intent)
    graph.add_node("generic_agent", run_generic_agent)
    graph.add_node("nfo_funds_agent", run_nfo_funds_agent)
    graph.add_node("end_node", lambda state: state)  # pass-through

    # Entry point
    graph.set_entry_point("classify")

    # After classification, route to the right agent
    graph.add_conditional_edges(
        "classify",
        route_by_intent,
        {
            "generic_agent": "generic_agent",
            "nfo_funds_agent": "nfo_funds_agent",
        },
    )

    # After each agent, check confidence
    graph.add_conditional_edges(
        "generic_agent",
        _route_after_check,
        {
            "end": END,
            "fallback": "nfo_funds_agent",
        },
    )

    graph.add_conditional_edges(
        "nfo_funds_agent",
        _route_after_check,
        {
            "end": END,
            "fallback": "generic_agent",
        },
    )

    # End node just terminates
    graph.add_edge("end_node", END)

    return graph.compile()


# Compiled graph — ready to invoke
agent_graph = build_graph()
