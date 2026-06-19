"""
Chat Service — orchestrates session management + LangGraph agent execution.
"""

from typing import Dict, List

from app.agents.graph import agent_graph
from app.services.session_service import session_service
from app.utils.logger import get_logger

logger = get_logger("chat_service")


class ChatService:
    def __init__(self):
        pass

    async def get_faq_response(self, query: str, unique_id: str) -> str:
        """
        Process a chat query end-to-end:
        1. Manage session in Redis
        2. Run LangGraph (router → agent → fallback if needed)
        3. Store response in session
        4. Return answer
        """
        logger.info(f"Processing query for uniqueId={unique_id}: {query[:80]!r}")

        # 1. Get or create session in Redis
        session_service.get_or_create_session(unique_id)

        # 2. Add user message to session
        session_service.add_message(unique_id, role="user", content=query)

        # 3. Get chat history
        chat_history = self._get_chat_history(unique_id)

        # 4. Run LangGraph
        initial_state = {
            "query": query,
            "chat_history": chat_history,
            "unique_id": unique_id,
            "intent": "",
            "response": "",
            "can_answer": False,
            "follow_up_questions": [],
            "metadata": {},
            "attempted_agents": [],
        }

        result = await agent_graph.ainvoke(initial_state)

        response = result.get("response", "Sorry, I couldn't process your request.")

        # 5. Add assistant response to session
        session_service.add_message(unique_id, role="assistant", content=response)

        logger.info(
            f"Response generated for uniqueId={unique_id} | "
            f"intent={result.get('intent')} | "
            f"can_answer={result.get('can_answer')} | "
            f"agents_tried={result.get('attempted_agents')}"
        )

        return response

    def _get_chat_history(self, unique_id: str) -> List[Dict[str, str]]:
        """Get chat history from Redis session (excluding the just-added user message)."""
        messages = session_service.get_messages(unique_id)
        # Return all but the last message (which is the current user query we just added)
        return [{"role": m.role, "content": m.content} for m in messages[:-1]]
