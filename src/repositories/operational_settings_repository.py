from src.models.operational_settings import OperationalSettings
from src.repositories.base_repository import BaseMongoRepository


class OperationalSettingsRepository(BaseMongoRepository[OperationalSettings]):
    collection_name = "operational_settings"
    model_class = OperationalSettings

    def get_main_settings(self) -> OperationalSettings | None:
        document = self._collection.find_one({"settings_key": "default"})
        return self._to_model(document) if document else None

    def save_main_settings(self, settings: OperationalSettings) -> OperationalSettings:
        existing = self.get_main_settings()
        if existing is None:
            payload = settings.to_mongo(exclude_none=False)
            payload.pop("_id", None)
            return self.create(payload)
        changes = settings.to_mongo(exclude_none=False)
        changes.pop("_id", None)
        self._collection.update_one(
            {"settings_key": "default"},
            {"$set": changes},
        )
        updated = self.get_main_settings()
        if updated is None:
            raise RuntimeError("Operational settings could not be updated.")
        return updated
