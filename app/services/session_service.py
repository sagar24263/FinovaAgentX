import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.config.redis import get_redis_client
from app.models.session import ChatMessage, ChatSession
from app.utils.logger import get_logger

logger = get_logger("session_service")


class SessionService:
    def __init__(self):
        self.redis_client = get_redis_client()

        # Redis key prefixes
        self.session_prefix = "finovaAgentX:session:"
        self.messages_prefix = "finovaAgentX:messages:"

        # TTL settings (seconds)
        self.session_ttl = 7200  # 2 hours
        self.message_ttl = 86400 * 30  # 30 days

        if self.redis_client:
            logger.info("Session service initialized with Redis")
        else:
            logger.warning("Redis not available - session service will not work")

    # ------------------------------------------------------------------
    # Keys
    # ------------------------------------------------------------------

    def _session_key(self, unique_id: str) -> str:
        return f"{self.session_prefix}{unique_id}"

    def _messages_key(self, unique_id: str) -> str:
        return f"{self.messages_prefix}{unique_id}"

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def _serialize_session(self, session: ChatSession) -> str:
        data = session.model_dump()
        data["created_at"] = session.created_at.isoformat()
        data["updated_at"] = session.updated_at.isoformat()
        if session.expires_at:
            data["expires_at"] = session.expires_at.isoformat()

        messages = []
        for msg in session.messages:
            m = msg.model_dump()
            m["timestamp"] = msg.timestamp.isoformat()
            messages.append(m)
        data["messages"] = messages
        return json.dumps(data)

    def _deserialize_session(self, raw: str) -> ChatSession:
        data = json.loads(raw)
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        if data.get("expires_at"):
            data["expires_at"] = datetime.fromisoformat(data["expires_at"])

        messages = []
        for m in data.get("messages", []):
            m["timestamp"] = datetime.fromisoformat(m["timestamp"])
            messages.append(ChatMessage(**m))
        data["messages"] = messages
        return ChatSession(**data)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_or_create_session(
        self,
        unique_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[ChatSession]:
        """Get existing session or create a new one."""
        session = self.get_session(unique_id)
        if session:
            return session
        return self.create_session(unique_id, metadata)

    def create_session(
        self,
        unique_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[ChatSession]:
        """Create a new session in Redis."""
        if not self.redis_client:
            logger.error("Redis not available - cannot create session")
            return None

        try:
            session = ChatSession(
                unique_id=unique_id,
                metadata=metadata or {},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                is_active=True,
                messages=[],
                expires_at=datetime.utcnow() + timedelta(seconds=self.session_ttl),
            )

            key = self._session_key(unique_id)
            self.redis_client.setex(key, self.session_ttl, self._serialize_session(session))
            logger.info(f"Created session for uniqueId={unique_id}")
            return session
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return None

    def get_session(self, unique_id: str) -> Optional[ChatSession]:
        """Get session from Redis."""
        if not self.redis_client:
            return None

        try:
            key = self._session_key(unique_id)
            raw = self.redis_client.get(key)
            if not raw:
                return None

            session = self._deserialize_session(raw)
            # Refresh TTL on access
            self.redis_client.expire(key, self.session_ttl)
            return session
        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            return None

    def add_message(
        self,
        unique_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[ChatMessage]:
        """Add a message to the session."""
        if not self.redis_client:
            return None

        try:
            session = self.get_session(unique_id)
            if not session:
                logger.warning(f"Session not found for uniqueId={unique_id}")
                return None

            message = ChatMessage(
                role=role,
                content=content,
                timestamp=datetime.utcnow(),
                metadata=metadata or {},
            )

            session.messages.append(message)
            session.updated_at = datetime.utcnow()

            key = self._session_key(unique_id)
            self.redis_client.setex(key, self.session_ttl, self._serialize_session(session))
            return message
        except Exception as e:
            logger.error(f"Failed to add message: {e}")
            return None

    def get_messages(self, unique_id: str) -> List[ChatMessage]:
        """Get all messages for a session."""
        session = self.get_session(unique_id)
        if not session:
            return []
        return session.messages

    def delete_session(self, unique_id: str) -> bool:
        """Delete a session."""
        if not self.redis_client:
            return False

        try:
            key = self._session_key(unique_id)
            self.redis_client.delete(key)
            logger.info(f"Deleted session for uniqueId={unique_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False


# Singleton
session_service = SessionService()
