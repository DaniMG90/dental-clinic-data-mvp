from pymongo import MongoClient

from src.core.config import Settings, get_settings
from src.database.mongo_client import get_mongo_client as build_robust_mongo_client


def get_mongo_client(settings: Settings | None = None) -> MongoClient:
    return build_robust_mongo_client(settings)


def get_database(settings: Settings | None = None):
    resolved_settings = settings or get_settings()
    client = get_mongo_client(resolved_settings)
    return client[resolved_settings.mongo_active_db]
