"""
Generic Investment Agent — handles general investment queries.
Uses langgraph's prebuilt react agent for plan, insurer, and calculation tools.
"""

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.prebuilt import create_react_agent

from app.agents.state import AgentState
from app.prompts.generic_prompt import GENERIC_AGENT_SYSTEM_PROMPT
from app.services.llm_service import get_llm_service
from app.tools.calculation_tools import GetFutureValueTool, GetRequiredInvestmentTool
from app.tools.insurer_tools import GetInsurerInfoTool
from app.tools.plan_tools import (
    ComparePlansTool,
    GetPlanDetailsTool,
    GetPlansByInsurerTool,
    GetTopPlansTool,
)
from app.utils.logger import get_logger

logger = get_logger("generic_agent")

tools = [
    GetTopPlansTool(),
    GetPlanDetailsTool(),
    GetInsurerInfoTool(),
    ComparePlansTool(),
    GetPlansByInsurerTool(),
    GetRequiredInvestmentTool(),
    GetFutureValueTool(),
]


def _build_react_agent():
    llm = get_llm_service().get_llm(
        model="gemini-3.1-flash-lite",
        temperature=0.35,
        max_tokens=4000,
    )
    return create_react_agent(llm, tools, prompt=GENERIC_AGENT_SYSTEM_PROMPT)


async def run_generic_agent(state: AgentState) -> AgentState:
    """LangGraph node: run the generic investment agent."""
    query = state["query"]
    chat_history = state.get("chat_history", [])

    logger.info(f"Generic Agent processing: {query[:80]!r}")

    attempted = state.get("attempted_agents", [])
    attempted.append("generic_investment")
    state["attempted_agents"] = attempted

    try:
        agent = _build_react_agent()

        messages = []
        for msg in chat_history[-10:]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=query))

        result = await agent.ainvoke({"messages": messages})

        final_messages = result.get("messages", [])
        response_content = ""
        tools_used = []

        for msg in final_messages:
            if getattr(msg, "type", None) == "tool" and getattr(msg, "name", None):
                tools_used.append(msg.name)

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

        can_answer = "[CANNOT_ANSWER]" not in response_content
        if not can_answer:
            response_content = response_content.replace("[CANNOT_ANSWER]", "").strip()

        state["response"] = response_content
        state["can_answer"] = can_answer
        state["follow_up_questions"] = []
        state["metadata"] = {
            "agent_type": "generic_investment",
            "tools_used": list(dict.fromkeys(tools_used)),
        }

        logger.info(f"Generic Agent done. can_answer={can_answer}")

    except Exception as e:
        logger.error(f"Generic Agent error: {e}")
        state["response"] = "Something went wrong while processing your request."
        state["can_answer"] = False
        state["follow_up_questions"] = []
        state["metadata"] = {"agent_type": "generic_investment", "error": str(e)}

    return state
