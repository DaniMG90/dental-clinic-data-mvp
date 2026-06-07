from datetime import datetime
from typing import Any

from pymongo import ASCENDING, DESCENDING

from src.models.treatment import Treatment, TreatmentStatus
from src.repositories.base_repository import BaseMongoRepository


class TreatmentRepository(BaseMongoRepository[Treatment]):
    collection_name = "treatments"
    model_class = Treatment

    def find_active_treatments(self, limit: int = 100) -> list[Treatment]:
        return self.find_many(
            {"status": {"$in": [TreatmentStatus.PLANNED, TreatmentStatus.IN_PROGRESS]}},
            limit=limit,
            sort=[("planned_date", ASCENDING), ("created_at", ASCENDING)],
        )

    def find_by_category(self, category: str, limit: int = 100) -> list[Treatment]:
        return self.find_many(
            {"treatment_type": category},
            limit=limit,
            sort=[("planned_date", ASCENDING), ("created_at", ASCENDING)],
        )

    def find_most_used_treatments(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        filters = self._optional_activity_date_filter(start_date, end_date)
        pipeline: list[dict[str, Any]] = []
        if filters:
            pipeline.append({"$match": filters})
        pipeline.extend(
            [
                {"$group": {"_id": "$treatment_type", "count": {"$sum": 1}}},
                {"$project": {"_id": 0, "treatment_type": "$_id", "count": 1}},
                {"$sort": {"count": DESCENDING, "treatment_type": ASCENDING}},
                {"$limit": limit},
            ],
        )
        return list(self._collection.aggregate(pipeline))

    def _optional_activity_date_filter(
        self,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        date_filter: dict[str, datetime] = {}
        if start_date is not None:
            date_filter["$gte"] = start_date
        if end_date is not None:
            date_filter["$lt"] = end_date
        if date_filter:
            filters["$or"] = [
                {"completed_at": date_filter},
                {"planned_date": date_filter},
                {"created_at": date_filter},
            ]
        return filters
