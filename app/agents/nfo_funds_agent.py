"""
NFO/Funds Agent — handles NFO and fund-specific queries.
Uses langgraph's prebuilt react agent for automatic tool calling.
"""

from langgraph.prebuilt import create_react_agent

from app.agents.state import AgentState
from app.prompts.nfo_funds_prompt import NFO_FUNDS_AGENT_SYSTEM_PROMPT
from app.services.llm_service import get_llm_service
from app.tools.nfo import GetActiveNfosTool, GetNfoTimelineTool, GetNfoListingReturnsTool, GetClosedFundsTool
from app.tools.funds import (
    GetFundDetailsTool,
    GetPlanFundPerformanceTool,
    GetFundAssetClassBreakupTool,
    GetFundHoldingSectorBreakupTool,
    GetInsurerTopFundsTool,
    GetPlanFundsSplitByTypeTool,
    CompareFundsTool,
)
from app.tools.insurer import GetInsurerInfoTool
from app.utils.logger import get_logger

logger = get_logger("nfo_funds_agent")

# Tools available to this agent
tools = [
    GetActiveNfosTool(),
    GetNfoTimelineTool(),
    GetNfoListingReturnsTool(),
    GetClosedFundsTool(),
    GetFundDetailsTool(),
    GetPlanFundPerformanceTool(),
    GetFundAssetClassBreakupTool(),
    GetFundHoldingSectorBreakupTool(),
    GetInsurerInfoTool(),
    GetInsurerTopFundsTool(),
    GetPlanFundsSplitByTypeTool(),
    CompareFundsTool(),
]


def _build_react_agent():
    """Build a react agent that handles tool calling automatically."""
    llm = get_llm_service().get_llm(
        model="gemini-3.1-flash-lite",
        temperature=0.3,
        max_tokens=4000,
    )
    return create_react_agent(llm, tools, prompt=NFO_FUNDS_AGENT_SYSTEM_PROMPT)


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
        agent = _build_react_agent()

        # Build input messages
        from langchain_core.messages import AIMessage, HumanMessage
        messages = []
        for msg in chat_history[-10:]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=query))

        # Invoke — tool calling loop is handled automatically
        result = await agent.ainvoke({"messages": messages})

        # Extract final response from the last AI message
        final_messages = result.get("messages", [])
        response_content = ""
        for msg in reversed(final_messages):
            if hasattr(msg, "content") and msg.type == "ai" and msg.content:
                raw_content = msg.content
                if isinstance(raw_content, list):
                    response_content = "".join(
                        block.get("text", "") if isinstance(block, dict) else str(block)
                        for block in raw_content
                    ).strip()
                else:
                    response_content = raw_content
                break

        # Confidence check — LLM signals with [CANNOT_ANSWER] tag
        can_answer = "[CANNOT_ANSWER]" not in response_content
        if not can_answer:
            # Strip the tag from the response
            response_content = response_content.replace("[CANNOT_ANSWER]", "").strip()

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
