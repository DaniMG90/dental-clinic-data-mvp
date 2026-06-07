from datetime import datetime
from enum import StrEnum

from pydantic import Field

from src.models.base import MongoModel, utc_now


class ImportSourceType(StrEnum):
    MANUAL = "manual"
    DEMO = "demo"
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"
    API = "api"
    EXTERNAL_SYSTEM = "external_system"


class ImportSourceStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ImportSource(MongoModel):
    source_name: str = Field(min_length=1, max_length=120)
    source_type: ImportSourceType

    file_name: str | None = Field(default=None, max_length=255)
    file_hash: str | None = Field(default=None, max_length=128)

    imported_at: datetime = Field(default_factory=utc_now)

    status: ImportSourceStatus = ImportSourceStatus.COMPLETED

    records_total: int = Field(default=0, ge=0)
    records_inserted: int = Field(default=0, ge=0)
    records_rejected: int = Field(default=0, ge=0)

    notes: str | None = None
