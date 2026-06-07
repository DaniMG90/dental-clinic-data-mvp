from dataclasses import dataclass

from src.core.config import Settings, get_settings
from src.database.connection import get_database
from src.repositories.database_metadata_repository import DatabaseMetadataRepository
from src.services.database_status_service import DatabaseStatus, DatabaseStatusService


@dataclass(frozen=True)
class AdminSystemStatus:
    database: DatabaseStatus
    document_counts: dict[str, int]
    app_env: str
    demo_mode: bool
    last_backup: str


class AdminService:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def get_system_status(self) -> AdminSystemStatus:
        database_status = DatabaseStatusService(self._settings).get_status()
        document_counts: dict[str, int] = {}

        if database_status.connected:
            database = get_database(self._settings)
            repository = DatabaseMetadataRepository(database)
            document_counts = repository.count_documents_by_collection(database_status.collections)

        return AdminSystemStatus(
            database=database_status,
            document_counts=document_counts,
            app_env=self._settings.app_env,
            demo_mode=self._settings.mongo_active_db == self._settings.mongo_demo_db,
            last_backup="Not configured in MVP",
        )
