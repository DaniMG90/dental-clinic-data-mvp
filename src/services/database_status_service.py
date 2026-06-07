from dataclasses import dataclass

from src.core.config import Settings, get_settings
from src.database.connection import get_database
from src.repositories.database_metadata_repository import DatabaseMetadataRepository


@dataclass(frozen=True)
class DatabaseStatus:
    connected: bool
    database_name: str
    collections: list[str]
    error: str | None = None


class DatabaseStatusService:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def get_status(self) -> DatabaseStatus:
        try:
            database = get_database(self._settings)
            repository = DatabaseMetadataRepository(database)
            repository.ping()

            return DatabaseStatus(
                connected=True,
                database_name=self._settings.mongo_active_db,
                collections=repository.list_collections(),
            )
        except Exception as exc:
            return DatabaseStatus(
                connected=False,
                database_name=self._settings.mongo_active_db,
                collections=[],
                error=str(exc),
            )
