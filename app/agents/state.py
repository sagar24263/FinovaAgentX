"""
Shared graph state for the LangGraph agent workflow.
"""

from typing import Any, Dict, List
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """State that flows through the LangGraph."""
    # Input
    query: str
    chat_history: List[Dict[str, str]]
    unique_id: str

    # Router decision
    intent: str  # "generic_investment" or "nfo_funds"

    # Agent output
    response: str
    can_answer: bool
    follow_up_questions: List[str]
    metadata: Dict[str, Any]

    # Fallback tracking
    attempted_agents: List[str]

    # Tool call details
    tool_calls: List[Dict[str, Any]]
