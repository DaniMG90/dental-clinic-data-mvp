from datetime import datetime
from enum import StrEnum

from pydantic import Field

from src.models.base import MongoModel, PyObjectId, utc_now


class TreatmentStatus(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    POSTPONED = "postponed"


class Treatment(MongoModel):
    treatment_code: str = Field(min_length=1, max_length=64)
    external_treatment_id: str | None = Field(default=None, max_length=128)
    import_source_id: PyObjectId | None = None

    patient_id: PyObjectId
    appointment_id: PyObjectId | None = None

    treatment_type: str = Field(min_length=1, max_length=120)
    description: str | None = None

    status: TreatmentStatus = TreatmentStatus.PLANNED

    planned_date: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    estimated_price: float | None = Field(default=None, ge=0)
    final_price: float | None = Field(default=None, ge=0)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    notes: str | None = None
