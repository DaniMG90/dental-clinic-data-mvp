import re
from typing import Any

from pymongo import ASCENDING

from src.models.base import utc_now
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

    def update_patient_fields(self, patient_id: Any, changes: dict[str, Any]) -> Patient | None:
        if not changes:
            return self.find_by_id(patient_id)
        payload = dict(changes)
        payload["updated_at"] = utc_now()
        self._collection.update_one(
            {"_id": self._as_object_id(patient_id)},
            {"$set": payload},
        )
        return self.find_by_id(patient_id)

    def search_by_name_or_phone(self, search_text: str, limit: int = 50) -> list[Patient]:
        tokens = [token for token in search_text.strip().split() if token]
        if not tokens:
            return []

        filters: dict[str, Any] = {
            "$and": [
                {
                    "$or": [
                        {"first_name": {"$regex": re.escape(token), "$options": "i"}},
                        {"last_name": {"$regex": re.escape(token), "$options": "i"}},
                        {"phone": {"$regex": re.escape(token), "$options": "i"}},
                        {"email": {"$regex": re.escape(token), "$options": "i"}},
                        {"patient_code": {"$regex": re.escape(token), "$options": "i"}},
                        {"notes": {"$regex": re.escape(token), "$options": "i"}},
                    ],
                }
                for token in tokens
            ],
        }
        return self.find_many(
            filters,
            limit=limit,
            sort=[("last_name", ASCENDING), ("first_name", ASCENDING)],
        )
