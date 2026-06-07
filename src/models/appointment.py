from datetime import datetime
from enum import StrEnum

from pydantic import Field, model_validator

from src.models.base import MongoModel, PyObjectId, utc_now


class AppointmentStatus(StrEnum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    RESCHEDULED = "rescheduled"


class Appointment(MongoModel):
    appointment_code: str = Field(min_length=1, max_length=64)
    external_appointment_id: str | None = Field(default=None, max_length=128)
    import_source_id: PyObjectId | None = None

    patient_id: PyObjectId

    scheduled_start: datetime
    scheduled_end: datetime
    duration_minutes: int = Field(gt=0, le=24 * 60)

    status: AppointmentStatus = AppointmentStatus.SCHEDULED

    reason: str | None = Field(default=None, max_length=300)

    chair: str | None = Field(default=None, max_length=80)
    professional: str | None = Field(default=None, max_length=120)

    cancelled_at: datetime | None = None
    cancellation_reason: str | None = Field(default=None, max_length=300)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    notes: str | None = None

    @model_validator(mode="after")
    def validate_schedule(self) -> "Appointment":
        if self.scheduled_end <= self.scheduled_start:
            raise ValueError("scheduled_end must be later than scheduled_start")
        return self
