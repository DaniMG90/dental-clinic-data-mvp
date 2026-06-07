from pymongo.database import Database


class DatabaseMetadataRepository:
    def __init__(self, database: Database):
        self._database = database

    def ping(self) -> None:
        self._database.client.admin.command("ping")

    def list_collections(self) -> list[str]:
        return sorted(self._database.list_collection_names())
