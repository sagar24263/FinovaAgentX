"""
NFO/Funds Agent — placeholder for now.
Will handle NFO and fund-specific queries.
"""

from app.agents.state import AgentState
from app.utils.logger import get_logger

logger = get_logger("nfo_funds_agent")


async def run_nfo_funds_agent(state: AgentState) -> AgentState:
    """
    LangGraph node: run the NFO/Funds agent.
    Placeholder — will be implemented next.
    """
    query = state["query"]
    logger.info(f"NFO/Funds Agent processing: {query[:80]!r}")

    # Track attempt
    attempted = state.get("attempted_agents", [])
    attempted.append("nfo_funds")
    state["attempted_agents"] = attempted

    # Placeholder response
    state["response"] = "NFO/Funds agent is not yet implemented. Please try a general investment question."
    state["can_answer"] = False
    state["follow_up_questions"] = []
    state["metadata"] = {"agent_type": "nfo_funds", "placeholder": True}

    return state
