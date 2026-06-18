from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from app.utils.logger import get_logger
from app.config.env import SAVINGS_DB_URI, SAVINGS_DB_NAME

logger = get_logger("mongo")

_client = None


def _mongo_client_options() -> dict:
    """Connection pool options."""
    return {
        "maxPoolSize": 50,
        "minPoolSize": 10,
        "maxIdleTimeMS": 30000,
        "waitQueueTimeoutMS": 2500,
        "serverSelectionTimeoutMS": 5000,
        "connectTimeoutMS": 10000,
        "socketTimeoutMS": 30000,
        "retryReads": True,
        "heartbeatFrequencyMS": 10000,
        "compressors": ["zlib"],
        "zlibCompressionLevel": 6,
    }


def get_mongo_client():
    """Get MongoDB client for Savings DB / DocumentDB (singleton)."""
    global _client
    if _client is None:
        try:
            _client = MongoClient(
                SAVINGS_DB_URI,
                retryWrites=False,
                **_mongo_client_options(),
            )
            _client.admin.command("ping")
            logger.info("Savings DB (DocumentDB) connection established")
        except ConnectionFailure as e:
            logger.warning(f"Savings DB connection failed: {e}")
            _client = None
        except Exception as e:
            logger.warning(f"Savings DB connection error: {e}")
            _client = None
    return _client


def get_database(name: str | None = None):
    client = get_mongo_client()
    if client is None:
        return None
    return client[name or SAVINGS_DB_NAME]


def get_collection(collection_name: str, db_name: str | None = None):
    db = get_database(db_name)
    if db is None:
        return None
    return db[collection_name]
