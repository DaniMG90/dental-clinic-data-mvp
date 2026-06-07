from datetime import datetime
from enum import StrEnum

from pydantic import Field

from src.models.base import MongoModel, PyObjectId, utc_now
from src.models.treatment import TreatmentStatus


class TreatmentEventType(StrEnum):
    CREATED = "created"
    STATUS_CHANGED = "status_changed"
    PRICE_UPDATED = "price_updated"
    APPOINTMENT_LINKED = "appointment_linked"
    APPOINTMENT_UNLINKED = "appointment_unlinked"
    NOTE_ADDED = "note_added"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    POSTPONED = "postponed"


class TreatmentEvent(MongoModel):
    treatment_id: PyObjectId
    patient_id: PyObjectId
    appointment_id: PyObjectId | None = None

    event_type: TreatmentEventType
    event_date: datetime

    previous_status: TreatmentStatus | None = None
    new_status: TreatmentStatus | None = None

    description: str | None = None

    created_by: str | None = Field(default=None, max_length=120)
    created_at: datetime = Field(default_factory=utc_now)
