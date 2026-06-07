from typing import Any

from pymongo import ASCENDING

from src.models.patient import Patient, PatientStatus
from src.repositories.base_repository import BaseMongoRepository


class PatientRepository(BaseMongoRepository[Patient]):
    collection_name = "patients"
    model_class = Patient

    def find_active_patients(self, limit: int = 100) -> list[Patient]:
        return self.find_many(
            {"status": PatientStatus.ACTIVE},
            limit=limit,
            sort=[("last_name", ASCENDING), ("first_name", ASCENDING)],
        )

    def find_inactive_patients(self, limit: int = 100) -> list[Patient]:
        return self.find_many(
            {"status": {"$in": [PatientStatus.INACTIVE, PatientStatus.ARCHIVED]}},
            limit=limit,
            sort=[("last_name", ASCENDING), ("first_name", ASCENDING)],
        )

    def search_by_name_or_phone(self, search_text: str, limit: int = 50) -> list[Patient]:
        normalized_text = search_text.strip()
        if not normalized_text:
            return []

        filters: dict[str, Any] = {
            "$or": [
                {"first_name": {"$regex": normalized_text, "$options": "i"}},
                {"last_name": {"$regex": normalized_text, "$options": "i"}},
                {"phone": {"$regex": normalized_text, "$options": "i"}},
            ],
        }
        return self.find_many(
            filters,
            limit=limit,
            sort=[("last_name", ASCENDING), ("first_name", ASCENDING)],
        )
