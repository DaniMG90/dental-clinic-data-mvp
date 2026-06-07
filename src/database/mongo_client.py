import time

from pymongo import MongoClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

from src.core.config import Settings, get_settings


def build_mongo_uri(settings: Settings | None = None) -> str:
    resolved_settings = settings or get_settings()

    return (
        f"mongodb://{resolved_settings.mongo_username}:{resolved_settings.mongo_password}"
        f"@{resolved_settings.mongo_host}:{resolved_settings.mongo_port}/"
        f"?authSource=admin"
    )


def get_mongo_client(
    settings: Settings | None = None,
    max_retries: int | None = None,
    retry_delay_seconds: int | None = None,
) -> MongoClient:
    resolved_settings = settings or get_settings()
    uri = build_mongo_uri(resolved_settings)
    resolved_max_retries = max_retries or resolved_settings.mongo_connect_max_retries
    resolved_retry_delay = (
        retry_delay_seconds
        if retry_delay_seconds is not None
        else resolved_settings.mongo_retry_delay_seconds
    )
    last_error: PyMongoError | None = None

    for attempt in range(1, resolved_max_retries + 1):
        try:
            client = MongoClient(
                uri,
                serverSelectionTimeoutMS=resolved_settings.mongo_timeout_ms,
                connectTimeoutMS=resolved_settings.mongo_timeout_ms,
                socketTimeoutMS=resolved_settings.mongo_timeout_ms,
            )
            client.admin.command("ping")
            return client
        except ServerSelectionTimeoutError as exc:
            last_error = exc
            print(
                f"[MongoDB] Connection attempt {attempt}/{resolved_max_retries} failed. "
                f"Retrying in {resolved_retry_delay}s..."
            )
            if attempt < resolved_max_retries:
                time.sleep(resolved_retry_delay)

    raise RuntimeError("MongoDB is not available after several retries.") from last_error
