import re
from typing import Any

from pymongo import ASCENDING

from src.models.base import utc_now
from src.models.treatment_catalog import TreatmentCatalogItem
from src.repositories.base_repository import BaseMongoRepository


class TreatmentCatalogRepository(BaseMongoRepository[TreatmentCatalogItem]):
    collection_name = "treatment_catalog"
    model_class = TreatmentCatalogItem

    def list_items(self, include_inactive: bool = True, limit: int = 200) -> list[TreatmentCatalogItem]:
        filters = {} if include_inactive else {"active": True}
        return self.find_many(filters, limit=limit, sort=[("name", ASCENDING)])

    def search(self, search_text: str, include_inactive: bool = True, limit: int = 100) -> list[TreatmentCatalogItem]:
        tokens = [token for token in search_text.strip().split() if token]
        if not tokens:
            return self.list_items(include_inactive=include_inactive, limit=limit)

        filters: dict[str, Any] = {
            "$and": [
                {
                    "$or": [
                        {"name": {"$regex": re.escape(token), "$options": "i"}},
                        {"category": {"$regex": re.escape(token), "$options": "i"}},
                        {"catalog_code": {"$regex": re.escape(token), "$options": "i"}},
                        {"notes": {"$regex": re.escape(token), "$options": "i"}},
                    ],
                }
                for token in tokens
            ],
        }
        if not include_inactive:
            filters = {"$and": [filters, {"active": True}]}
        return self.find_many(filters, limit=limit, sort=[("name", ASCENDING)])

    def update_catalog_fields(self, item_id: Any, changes: dict[str, Any]) -> TreatmentCatalogItem | None:
        if not changes:
            return self.find_by_id(item_id)
        payload = dict(changes)
        payload["updated_at"] = utc_now()
        self._collection.update_one(
            {"_id": self._as_object_id(item_id)},
            {"$set": payload},
        )
        return self.find_by_id(item_id)
