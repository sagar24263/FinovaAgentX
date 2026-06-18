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

        # TODO: Implement actual FAQ logic (vector search, LLM call, etc.)
        answer = f"This is a placeholder answer for: {query}"

        logger.info(f"FAQ response generated for uniqueId={unique_id}")
        return answer
