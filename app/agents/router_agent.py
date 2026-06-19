"""
Router Agent — classifies user intent and routes to the appropriate sub-agent.
Uses Gemini Flash for fast, cheap classification.
"""

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from app.agents.state import AgentState
from app.prompts.router_prompt import ROUTER_SYSTEM_PROMPT
from app.services.llm_service import get_llm_service
from app.utils.logger import get_logger

logger = get_logger("router_agent")


async def classify_intent(state: AgentState) -> AgentState:
    """
    LangGraph node: classify user query intent.
    Updates state with 'intent' field.
    """
    query = state["query"]
    chat_history = state.get("chat_history", [])

    logger.info(f"Classifying intent for: {query[:80]!r}")

    llm = get_llm_service().get_llm(
        model="gemini-3.1-flash-lite",
        temperature=0,
        max_tokens=20,
    )

    # Build messages
    messages = [SystemMessage(content=ROUTER_SYSTEM_PROMPT)]

    # Add chat history for context
    for msg in chat_history[-4:]:  # Last 4 messages for context
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    # Add current query
    messages.append(HumanMessage(content=query))

    try:
        response = await llm.ainvoke(messages)
        intent = response.content.strip().lower()

        # Validate — only allow known intents
        if intent not in ("generic_investment", "nfo_funds"):
            logger.warning(f"Unknown intent '{intent}', defaulting to generic_investment")
            intent = "generic_investment"

        logger.info(f"Intent classified: {intent}")

    except Exception as e:
        logger.error(f"Intent classification failed: {e}, defaulting to generic_investment")
        intent = "generic_investment"

    state["intent"] = intent
    state["attempted_agents"] = []
    return state


def route_by_intent(state: AgentState) -> str:
    """
    LangGraph conditional edge: route to sub-agent based on intent.
    Returns the next node name.
    """
    intent = state.get("intent", "generic_investment")
    attempted = state.get("attempted_agents", [])

    # If this agent was already attempted (fallback scenario), go to the other one
    if intent == "generic_investment" and "generic_investment" in attempted:
        return "nfo_funds_agent"
    elif intent == "nfo_funds" and "nfo_funds" in attempted:
        return "generic_agent"

    # Normal routing
    if intent == "nfo_funds":
        return "nfo_funds_agent"
    return "generic_agent"


def should_fallback(state: AgentState) -> str:
    """
    LangGraph conditional edge: check if response is satisfactory or needs fallback.
    Returns 'end' or 'fallback'.
    """
    can_answer = state.get("can_answer", True)
    attempted = state.get("attempted_agents", [])

    # If agent couldn't answer and we haven't tried the other agent yet
    if not can_answer and len(attempted) < 2:
        logger.info(f"Agent couldn't answer, attempting fallback. Tried: {attempted}")
        return "fallback"

    return "end"
