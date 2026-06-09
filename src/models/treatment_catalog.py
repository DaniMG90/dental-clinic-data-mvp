from datetime import datetime

from pydantic import Field

from src.models.base import MongoModel, utc_now


class TreatmentCatalogItem(MongoModel):
    catalog_code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    category: str | None = Field(default=None, max_length=120)
    default_duration_minutes: int | None = Field(default=None, gt=0, le=24 * 60)
    base_price: float | None = Field(default=None, ge=0)
    active: bool = True
    notes: str | None = None

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
