from datetime import datetime
from typing import Any

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING

from src.models.treatment_event import TreatmentEvent
from src.repositories.base_repository import BaseMongoRepository


class TreatmentEventRepository(BaseMongoRepository[TreatmentEvent]):
    collection_name = "treatment_events"
    model_class = TreatmentEvent

    def find_by_patient_id(self, patient_id: ObjectId | str, limit: int = 100) -> list[TreatmentEvent]:
        return self._find_by_reference("patient_id", patient_id, limit)

    def find_by_treatment_id(
        self,
        treatment_id: ObjectId | str,
        limit: int = 100,
    ) -> list[TreatmentEvent]:
        return self._find_by_reference("treatment_id", treatment_id, limit)

    def find_by_appointment_id(
        self,
        appointment_id: ObjectId | str,
        limit: int = 100,
    ) -> list[TreatmentEvent]:
        return self._find_by_reference("appointment_id", appointment_id, limit)

    def get_treatment_activity_evolution(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        pipeline = [
            {"$match": self._date_range_filter(start_date, end_date)},
            {
                "$group": {
                    "_id": {
                        "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$event_date"}},
                        "event_type": "$event_type",
                    },
                    "count": {"$sum": 1},
                },
            },
            {
                "$project": {
                    "_id": 0,
                    "date": "$_id.date",
                    "event_type": "$_id.event_type",
                    "count": 1,
                },
            },
            {"$sort": {"date": ASCENDING, "event_type": ASCENDING}},
        ]
        return list(self._collection.aggregate(pipeline))

    def get_treatment_frequency(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        filters = self._optional_date_range_filter(start_date, end_date)
        pipeline: list[dict[str, Any]] = []
        if filters:
            pipeline.append({"$match": filters})
        pipeline.extend(
            [
                {"$group": {"_id": "$event_type", "count": {"$sum": 1}}},
                {"$project": {"_id": 0, "event_type": "$_id", "count": 1}},
                {"$sort": {"count": DESCENDING, "event_type": ASCENDING}},
                {"$limit": limit},
            ],
        )
        return list(self._collection.aggregate(pipeline))

    def _find_by_reference(
        self,
        field_name: str,
        document_id: ObjectId | str,
        limit: int,
    ) -> list[TreatmentEvent]:
        return self.find_many(
            {field_name: self._as_object_id(document_id)},
            limit=limit,
            sort=[("event_date", ASCENDING)],
        )

    def _date_range_filter(self, start_date: datetime, end_date: datetime) -> dict[str, Any]:
        return {"event_date": {"$gte": start_date, "$lt": end_date}}

    def _optional_date_range_filter(
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
            filters["event_date"] = date_filter
        return filters
