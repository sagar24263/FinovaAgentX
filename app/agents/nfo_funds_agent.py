"""
NFO/Funds Agent — handles NFO and fund-specific queries.
Uses Gemini LLM with NFO/Funds system prompt.
"""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.state import AgentState
from app.prompts.nfo_funds_prompt import NFO_FUNDS_AGENT_SYSTEM_PROMPT
from app.services.llm_service import get_llm_service
from app.utils.logger import get_logger

logger = get_logger("nfo_funds_agent")


async def run_nfo_funds_agent(state: AgentState) -> AgentState:
    """
    LangGraph node: run the NFO/Funds agent.
    """
    query = state["query"]
    chat_history = state.get("chat_history", [])

    logger.info(f"NFO/Funds Agent processing: {query[:80]!r}")

    # Track attempt
    attempted = state.get("attempted_agents", [])
    attempted.append("nfo_funds")
    state["attempted_agents"] = attempted

    try:
        llm = get_llm_service().get_llm(
            model="gemini-3.1-flash-lite",
            temperature=0.3,
            max_tokens=4000,
        )

        # Build messages
        messages = [SystemMessage(content=NFO_FUNDS_AGENT_SYSTEM_PROMPT)]

        # Add chat history
        for msg in chat_history[-10:]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        # Add current query
        messages.append(HumanMessage(content=query))

        # Call LLM
        response = await llm.ainvoke(messages)

        # Handle content as list of blocks (langchain-google-genai 4.x)
        raw_content = response.content
        if isinstance(raw_content, list):
            response_content = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in raw_content
            ).strip()
        else:
            response_content = raw_content

        # Confidence check
        can_answer = True
        uncertainty_markers = [
            "i don't have information",
            "i cannot answer",
            "i'm not sure",
            "outside my knowledge",
            "i don't know",
            "i don't have details on general investment",
        ]
        if any(marker in response_content.lower() for marker in uncertainty_markers):
            can_answer = False

        state["response"] = response_content
        state["can_answer"] = can_answer
        state["follow_up_questions"] = []
        state["metadata"] = {
            "agent_type": "nfo_funds",
            "tools_used": [],
        }

        logger.info(f"NFO/Funds Agent done. can_answer={can_answer}")

    except Exception as e:
        logger.error(f"NFO/Funds Agent error: {e}")
        state["response"] = "Something went wrong while processing your request."
        state["can_answer"] = False
        state["follow_up_questions"] = []
        state["metadata"] = {"agent_type": "nfo_funds", "error": str(e)}

    return state
