from typing import Dict, List

from app.services.session_service import session_service
from app.utils.logger import get_logger

logger = get_logger("chat_service")


class ChatService:
    def __init__(self):
        pass

    async def get_faq_response(self, query: str, unique_id: str) -> str:
        """
        Process FAQ query and return an answer.

        Args:
            query: The user's question
            unique_id: Unique session/customer identifier

        Returns:
            str: The answer to the FAQ query
        """
        logger.info(f"Processing FAQ query for uniqueId={unique_id}: {query}")

        # 1. Get or create session in Redis
        session = session_service.get_or_create_session(unique_id)
        if not session:
            logger.warning(f"Could not create session for uniqueId={unique_id}")

        # 2. Add user message to session
        session_service.add_message(unique_id, role="user", content=query)

        # 3. Prepare chat history from session
        chat_history = self._get_chat_history(unique_id)

        # 4. Get answer (TODO: plug in vector search / LLM)
        answer = f"This is a placeholder answer for: {query}"

        # 5. Add assistant response to session
        session_service.add_message(unique_id, role="assistant", content=answer)

        logger.info(f"FAQ response generated for uniqueId={unique_id}")
        return answer

    def _get_chat_history(self, unique_id: str) -> List[Dict[str, str]]:
        """Get chat history from Redis session as list of {role, content} dicts."""
        messages = session_service.get_messages(unique_id)
        return [{"role": m.role, "content": m.content} for m in messages]
