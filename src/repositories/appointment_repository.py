from datetime import datetime
from typing import Any

from bson import ObjectId
from pymongo import ASCENDING

from src.models.appointment import Appointment, AppointmentStatus
from src.repositories.base_repository import BaseMongoRepository


class AppointmentRepository(BaseMongoRepository[Appointment]):
    collection_name = "appointments"
    model_class = Appointment

    def find_by_patient_id(self, patient_id: ObjectId | str, limit: int = 100) -> list[Appointment]:
        return self.find_many(
            {"patient_id": self._as_object_id(patient_id)},
            limit=limit,
            sort=[("scheduled_start", ASCENDING)],
        )

    def find_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 500,
    ) -> list[Appointment]:
        return self.find_many(
            self._date_range_filter(start_date, end_date),
            limit=limit,
            sort=[("scheduled_start", ASCENDING)],
        )

    def find_overlapping(
        self,
        scheduled_start: datetime,
        scheduled_end: datetime,
        appointment_id_to_exclude: ObjectId | str | None = None,
        limit: int = 20,
    ) -> list[Appointment]:
        filters: dict[str, Any] = {
            "scheduled_start": {"$lt": scheduled_end},
            "scheduled_end": {"$gt": scheduled_start},
            "status": {"$in": [AppointmentStatus.SCHEDULED, AppointmentStatus.RESCHEDULED]},
        }
        if appointment_id_to_exclude is not None:
            filters["_id"] = {"$ne": self._as_object_id(appointment_id_to_exclude)}
        return self.find_many(filters, limit=limit, sort=[("scheduled_start", ASCENDING)])

    def count_by_status(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        filters = self._optional_date_range_filter(start_date, end_date)
        pipeline: list[dict[str, Any]] = []
        if filters:
            pipeline.append({"$match": filters})
        pipeline.extend(
            [
                {"$group": {"_id": "$status", "count": {"$sum": 1}}},
                {"$project": {"_id": 0, "status": "$_id", "count": 1}},
                {"$sort": {"status": 1}},
            ],
        )
        return list(self._collection.aggregate(pipeline))

    def get_agenda_occupation(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        pipeline = [
            {"$match": self._date_range_filter(start_date, end_date)},
            {
                "$group": {
                    "_id": {
                        "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$scheduled_start"}},
                        "status": "$status",
                    },
                    "appointments": {"$sum": 1},
                    "minutes": {"$sum": "$duration_minutes"},
                },
            },
            {
                "$project": {
                    "_id": 0,
                    "date": "$_id.date",
                    "status": "$_id.status",
                    "appointments": 1,
                    "minutes": 1,
                },
            },
            {"$sort": {"date": 1, "status": 1}},
        ]
        return list(self._collection.aggregate(pipeline))

    def _date_range_filter(self, start_date: datetime, end_date: datetime) -> dict[str, Any]:
        return {"scheduled_start": {"$gte": start_date, "$lt": end_date}}

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
            filters["scheduled_start"] = date_filter
        return filters
