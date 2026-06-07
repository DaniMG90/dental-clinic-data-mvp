from datetime import datetime
from enum import StrEnum

from pydantic import Field

from src.models.base import MongoModel, PyObjectId, utc_now


class PatientStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class Patient(MongoModel):
    patient_code: str = Field(min_length=1, max_length=64)
    external_patient_id: str | None = Field(default=None, max_length=128)
    import_source_id: PyObjectId | None = None

    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    birth_date: datetime | None = None
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    status: PatientStatus = PatientStatus.ACTIVE
    tags: list[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    notes: str | None = None
