import uuid
from typing import List
from app.config.mongo import get_collection
from app.config.redis import get_redis_client
from app.models.customer import CustomerProfileRequest, MessageRecord
from app.utils.logger import get_logger

_logger = get_logger("onboarding_service")

USERS_COLLECTION = "users"


class OnboardingService:
    def __init__(self):
        self.redis_client = get_redis_client()
        self.profile_ttl = 7200  # 2 hours
        self.profile_prefix = "finovaAgentX:profile:"

        if self.redis_client:
            _logger.info("OnboardingService initialized with Redis")
        else:
            _logger.warning("Redis not available - session caching disabled")

    async def onboard_customer(self, request: CustomerProfileRequest) -> tuple[str, List[MessageRecord]]:
        _logger.info(f"Onboarding customer UserId={request.UserId!r}, UserType={request.UserType!r}, ProductID={request.ProductID}")

        redis_key = f"{self.profile_prefix}{request.UserId}:{request.ProductID}"

        if self.redis_client:
            cached_uuid = self.redis_client.get(redis_key)
            if cached_uuid:
                _logger.info(f"Session exists for UserId={request.UserId!r}, ProductID={request.ProductID} — refreshing TTL")
                self.redis_client.expire(redis_key, self.profile_ttl)
                messages = self.getMessagesByUniqueId(cached_uuid)
                return cached_uuid, messages

        user_exists = await self.checkIfUserExist(request)
        if user_exists:
            _logger.info(f"User already exists in DB for UserId={request.UserId!r}")
        else:
            await self.saveUserData(request)

        profile_uuid = str(uuid.uuid4())
        if self.redis_client:
            self.redis_client.setex(redis_key, self.profile_ttl, profile_uuid)
            _logger.info(f"Session cached in Redis for UserId={request.UserId!r}")

        messages = self.getMessagesByUniqueId(profile_uuid)
        return profile_uuid, messages

    async def checkIfUserExist(self, request: CustomerProfileRequest) -> bool:
        collection = get_collection(collection_name=USERS_COLLECTION)
        if collection is None:
            _logger.warning("MongoDB unavailable — skipping user existence check")
            return False

        user = collection.find_one(
            {"UserId": request.UserId, "ProductID": request.ProductID},
            {"_id": 1},
        )
        return user is not None

    def getMessagesByUniqueId(self, unique_id: str) -> List[MessageRecord]:
        collection = get_collection(collection_name="userMessages")
        if collection is None:
            _logger.warning("MongoDB unavailable — cannot fetch messages")
            return []
        docs = list(collection.find(
            {"unique_id": unique_id},
            {"_id": 0},
            sort=[("timestamp", 1)],
        ))
        messages = []
        for doc in docs:
            messages.append(MessageRecord(
                role=doc.get("role", ""),
                content=doc.get("content", ""),
                timestamp=doc.get("timestamp").isoformat() + "Z" if doc.get("timestamp") else "",
            ))
        return messages

    async def saveUserData(self, request: CustomerProfileRequest) -> None:
        collection = get_collection(collection_name=USERS_COLLECTION)
        if collection is None:
            _logger.warning("MongoDB unavailable — skipping user save")
            return

        doc = {
            "UserId": request.UserId,
            "UserType": request.UserType,
            "UserSource": request.UserSource,
            "ProductID": request.ProductID,
        }
        collection.insert_one(doc)
        _logger.info(f"User saved to MongoDB UserId={request.UserId!r}")
