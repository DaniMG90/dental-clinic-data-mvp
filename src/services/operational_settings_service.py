from copy import deepcopy
from datetime import time
from typing import Any

from pydantic import ValidationError

from src.database.connection import get_database
from src.models.appointment import AppointmentStatus
from src.models.base import utc_now
from src.models.operational_settings import (
    AgendaSettings,
    AnalyticsSettings,
    ChairSetting,
    ClinicSetting,
    DayScheduleSetting,
    OperationalSettings,
    ProfessionalSetting,
    SecuritySettings,
    TimeBlockSetting,
    TreatmentSettings,
    WeeklyScheduleSetting,
)
from src.repositories.operational_settings_repository import OperationalSettingsRepository


class OperationalSettingsServiceError(ValueError):
    pass


DEFAULT_TREATMENT_CATEGORIES = [
    "Orthodontics",
    "Surgery",
    "Preventive",
    "Aesthetic",
    "General",
]


class OperationalSettingsService:
    def __init__(
        self,
        settings_repository: OperationalSettingsRepository | None = None,
    ):
        database = None
        if settings_repository is None:
            database = get_database()
        self._settings = settings_repository or OperationalSettingsRepository(database)

    def get_settings(self) -> OperationalSettings:
        existing = self._settings.get_main_settings()
        if existing is None:
            return self._settings.save_main_settings(default_operational_settings())

        merged = merge_with_defaults(existing)
        if merged.model_dump() != existing.model_dump():
            return self._settings.save_main_settings(merged)
        return existing

    def update_settings(self, changes: dict[str, Any]) -> OperationalSettings:
        current = self.get_settings()
        payload = current.model_dump(by_alias=True, exclude_none=False)
        payload.pop("_id", None)
        _deep_update(payload, changes)
        payload["settings_key"] = "default"
        payload["updated_at"] = utc_now()
        try:
            updated = OperationalSettings.model_validate(payload)
        except ValidationError as exc:
            raise OperationalSettingsServiceError(_validation_message(exc)) from exc
        return self._settings.save_main_settings(updated)

    def active_clinic_names(self) -> list[str]:
        return [clinic.name for clinic in self.get_settings().clinics if clinic.active]

    def active_chair_names(self, clinic_name: str | None = None) -> list[str]:
        settings = self.get_settings()
        clinic_codes_by_name = {clinic.name: clinic.code for clinic in settings.clinics}
        selected_code = clinic_codes_by_name.get(clinic_name) if clinic_name else None
        return [
            chair.name
            for chair in settings.chairs
            if chair.active and (selected_code is None or chair.clinic_code == selected_code)
        ]

    def active_professional_names(self) -> list[str]:
        return [professional.name for professional in self.get_settings().professionals if professional.active]

    def treatment_categories(self) -> list[str]:
        return self.get_settings().treatments.categories

    def agenda_hours(self) -> tuple[int, int]:
        agenda = self.get_settings().agenda
        return agenda.default_start_hour, agenda.default_end_hour

    def default_appointment_minutes(self) -> int:
        return self.get_settings().agenda.default_appointment_minutes

    def analytics_default_period(self) -> str:
        return self.get_settings().analytics.default_period

    def inactive_patient_days(self) -> int:
        return self.get_settings().analytics.inactive_patient_days


def default_operational_settings() -> OperationalSettings:
    clinic_centro = ClinicSetting(name="Clinic Centro", code="CLINIC_CENTRO", active=True)
    clinic_norte = ClinicSetting(name="Clinic Norte", code="CLINIC_NORTE", active=True)
    return OperationalSettings(
        business_name="Dental Operations Platform",
        internal_identifier="LOCAL-CLINIC",
        data_mode="demo",
        timezone="Europe/Madrid",
        clinics=[clinic_centro, clinic_norte],
        chairs=[
            ChairSetting(name="Gabinete 1", code="CENTRO_GAB_1", clinic_code=clinic_centro.code, active=True),
            ChairSetting(name="Gabinete 2", code="CENTRO_GAB_2", clinic_code=clinic_centro.code, active=True),
            ChairSetting(name="Gabinete 1", code="NORTE_GAB_1", clinic_code=clinic_norte.code, active=True),
            ChairSetting(name="Gabinete 2", code="NORTE_GAB_2", clinic_code=clinic_norte.code, active=True),
        ],
        professionals=[
            ProfessionalSetting(name="Dr. Alvarez", role="Odontologo", active=True),
            ProfessionalSetting(name="Dr. Rivera", role="Odontologo", active=True),
        ],
        weekly_schedule={
            clinic_centro.code: default_weekly_schedule(),
            clinic_norte.code: default_weekly_schedule(),
        },
        agenda=AgendaSettings(),
        analytics=AnalyticsSettings(default_period="weekly", inactive_patient_days=180),
        treatments=TreatmentSettings(
            categories=DEFAULT_TREATMENT_CATEGORIES,
            default_duration_minutes=45,
        ),
        security=SecuritySettings(),
    )


def default_weekly_schedule() -> WeeklyScheduleSetting:
    open_day = DayScheduleSetting(
        closed=False,
        blocks=[
            TimeBlockSetting(start="09:00", end="14:00"),
            TimeBlockSetting(start="16:00", end="20:00"),
        ],
    )
    return WeeklyScheduleSetting(
        monday=deepcopy(open_day),
        tuesday=deepcopy(open_day),
        wednesday=deepcopy(open_day),
        thursday=deepcopy(open_day),
        friday=deepcopy(open_day),
        saturday=DayScheduleSetting(closed=True, blocks=[]),
        sunday=DayScheduleSetting(closed=True, blocks=[]),
    )


def merge_with_defaults(settings: OperationalSettings) -> OperationalSettings:
    default = default_operational_settings().model_dump(by_alias=True, exclude_none=False)
    current = settings.model_dump(by_alias=True, exclude_none=False)
    _deep_update(default, current)
    default["settings_key"] = "default"
    default["updated_at"] = utc_now()
    return OperationalSettings.model_validate(default)


def parse_time_value(value: str) -> time:
    hour, minute = value.split(":", 1)
    return time(int(hour), int(minute))


def _deep_update(target: dict[str, Any], changes: dict[str, Any]) -> None:
    for key, value in changes.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = value


def _validation_message(exc: ValidationError) -> str:
    first_error = exc.errors()[0]
    location = ".".join(str(part) for part in first_error.get("loc", []))
    message = first_error.get("msg", "Configuracion no valida")
    return f"{location}: {message}" if location else message
