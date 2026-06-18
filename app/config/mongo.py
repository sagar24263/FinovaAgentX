from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from app.utils.logger import get_logger
from app.config.secret_manager import get_secret_manager

logger = get_logger("mongo")

_client = None  # Logs DB
_savings_client = None  # Savings DB


def _get_mongodb_uri() -> str:
    """Build MongoDB URI for Logs DB from secret manager."""
    sm = get_secret_manager()
    username = sm.get_secret_value("mongoDBUserName")
    password = sm.get_secret_value("mongoDBPassword")
    import os
    from app.config.settings import get_settings
    settings = get_settings(os.getenv("ENV", "dev"))
    return f"mongodb://{username}:{password}@{settings.mongodb_host}/investmentLogs?authSource=admin"


def _get_savings_db_uri() -> str:
    """Build DocumentDB URI for Savings DB from secret manager."""
    sm = get_secret_manager()
    username = sm.get_secret_value("documentDBUserName")
    password = sm.get_secret_value("documentDBPassword")
    import os
    from app.config.settings import get_settings
    settings = get_settings(os.getenv("ENV", "dev"))
    return f"mongodb://{username}:{password}@{settings.documentdb_host}/{settings.savings_db_name}?tls=true&tlsCAFile=global-bundle.pem&retryWrites=false"


def _mongo_client_options() -> dict:
    """Shared connection pool options."""
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


# ============================================================================
# Logs DB (MongoDB)
# ============================================================================

def get_mongo_client():
    """Get MongoDB client for Logs DB (singleton)."""
    global _client
    if _client is None:
        try:
            _client = MongoClient(
                _get_mongodb_uri(),
                retryWrites=True,
                **_mongo_client_options(),
            )
            _client.admin.command("ping")
            logger.info("MongoDB (Logs DB) connection established")
        except ConnectionFailure as e:
            logger.warning(f"MongoDB connection failed: {e}")
            _client = None
        except Exception as e:
            logger.warning(f"MongoDB connection error: {e}")
            _client = None
    return _client


def get_database(name: str = "investmentLogs"):
    client = get_mongo_client()
    if client is None:
        return None
    return client[name]


def get_collection(db_name: str = "investmentLogs", collection_name: str = "analytics"):
    db = get_database(db_name)
    if db is None:
        return None
    return db[collection_name]


# ============================================================================
# Savings DB (DocumentDB)
# ============================================================================

def get_savings_db_client():
    """Get MongoDB client for Savings DB / DocumentDB (singleton)."""
    global _savings_client
    if _savings_client is None:
        try:
            _savings_client = MongoClient(
                _get_savings_db_uri(),
                retryWrites=False,
                **_mongo_client_options(),
            )
            _savings_client.admin.command("ping")
            logger.info("Savings DB (DocumentDB) connection established")
        except ConnectionFailure as e:
            logger.warning(f"Savings DB connection failed: {e}")
            _savings_client = None
        except Exception as e:
            logger.warning(f"Savings DB connection error: {e}")
            _savings_client = None
    return _savings_client


def get_savings_database(name: str | None = None):
    client = get_savings_db_client()
    if client is None:
        return None
    import os
    from app.config.settings import get_settings
    settings = get_settings(os.getenv("ENV", "dev"))
    db_name = name or settings.savings_db_name
    return client[db_name]


def get_savings_collection(collection_name: str, db_name: str | None = None):
    db = get_savings_database(db_name)
    if db is None:
        return None
    return db[collection_name]
