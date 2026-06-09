from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator, model_validator

from src.models.appointment import AppointmentStatus
from src.models.base import MongoModel, utc_now


class ClinicSetting(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=64)
    active: bool = True


class ChairSetting(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=64)
    clinic_code: str = Field(min_length=1, max_length=64)
    active: bool = True


class ProfessionalSetting(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(default="Odontologo", min_length=1, max_length=80)
    active: bool = True


class TimeBlockSetting(BaseModel):
    start: str = Field(pattern=r"^\d{2}:\d{2}$")
    end: str = Field(pattern=r"^\d{2}:\d{2}$")

    @model_validator(mode="after")
    def validate_time_order(self):
        if self.start >= self.end:
            raise ValueError("block start time must be before end time")
        return self


class DayScheduleSetting(BaseModel):
    closed: bool = False
    blocks: list[TimeBlockSetting] = Field(default_factory=list)


class WeeklyScheduleSetting(BaseModel):
    monday: DayScheduleSetting = Field(default_factory=DayScheduleSetting)
    tuesday: DayScheduleSetting = Field(default_factory=DayScheduleSetting)
    wednesday: DayScheduleSetting = Field(default_factory=DayScheduleSetting)
    thursday: DayScheduleSetting = Field(default_factory=DayScheduleSetting)
    friday: DayScheduleSetting = Field(default_factory=DayScheduleSetting)
    saturday: DayScheduleSetting = Field(default_factory=lambda: DayScheduleSetting(closed=True))
    sunday: DayScheduleSetting = Field(default_factory=lambda: DayScheduleSetting(closed=True))


class AgendaSettings(BaseModel):
    default_appointment_minutes: int = Field(default=45, ge=5, le=240)
    visual_interval_minutes: int = Field(default=30, ge=5, le=120)
    default_start_hour: int = Field(default=8, ge=0, le=23)
    default_end_hour: int = Field(default=21, ge=1, le=24)
    allow_overlaps: bool = True
    overlap_warning_enabled: bool = True
    enabled_statuses: list[AppointmentStatus] = Field(
        default_factory=lambda: list(AppointmentStatus),
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_hours(self):
        if self.default_start_hour >= self.default_end_hour:
            raise ValueError("agenda start hour must be before end hour")
        return self


class AnalyticsSettings(BaseModel):
    default_period: Literal["weekly", "monthly", "last_30_days", "last_90_days"] = "weekly"
    inactive_patient_days: int = Field(default=180, ge=1, le=3650)


class TreatmentSettings(BaseModel):
    categories: list[str] = Field(default_factory=list)
    default_duration_minutes: int = Field(default=45, ge=5, le=240)


class SecuritySettings(BaseModel):
    demo_mode_visible: bool = True
    confirm_sensitive_operations: bool = True


class OperationalSettings(MongoModel):
    settings_key: str = Field(default="default", min_length=1, max_length=64)
    schema_version: int = Field(default=1, ge=1)

    business_name: str = Field(default="Dental Operations Platform", min_length=1, max_length=160)
    internal_identifier: str = Field(default="LOCAL-CLINIC", min_length=1, max_length=80)
    data_mode: Literal["demo", "real"] = "demo"
    timezone: str = "Europe/Madrid"

    clinics: list[ClinicSetting] = Field(default_factory=list)
    chairs: list[ChairSetting] = Field(default_factory=list)
    professionals: list[ProfessionalSetting] = Field(default_factory=list)
    weekly_schedule: dict[str, WeeklyScheduleSetting] = Field(default_factory=dict)
    agenda: AgendaSettings = Field(default_factory=AgendaSettings)
    analytics: AnalyticsSettings = Field(default_factory=AnalyticsSettings)
    treatments: TreatmentSettings = Field(default_factory=TreatmentSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("timezone is not valid") from exc
        return value

    @model_validator(mode="after")
    def validate_operational_references(self):
        clinic_codes = {clinic.code for clinic in self.clinics}
        if len(clinic_codes) != len(self.clinics):
            raise ValueError("clinic codes must be unique")

        chair_codes = {chair.code for chair in self.chairs}
        if len(chair_codes) != len(self.chairs):
            raise ValueError("chair codes must be unique")

        for chair in self.chairs:
            if chair.clinic_code not in clinic_codes:
                raise ValueError(f"chair {chair.code} references an unknown clinic")

        active_clinic_codes = {clinic.code for clinic in self.clinics if clinic.active}
        for chair in self.chairs:
            if chair.active and chair.clinic_code not in active_clinic_codes:
                raise ValueError("active chairs must belong to an active clinic")

        for clinic_code in self.weekly_schedule:
            if clinic_code not in clinic_codes:
                raise ValueError("weekly schedule references an unknown clinic")

        if not self.agenda.enabled_statuses:
            raise ValueError("at least one appointment status must be enabled")

        return self
