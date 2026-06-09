from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from src.database.connection import get_database
from src.models.appointment import Appointment, AppointmentStatus
from src.models.operational_settings import OperationalSettings
from src.models.treatment_event import TreatmentEvent, TreatmentEventType
from src.repositories.appointment_repository import AppointmentRepository
from src.repositories.operational_settings_repository import OperationalSettingsRepository
from src.repositories.patient_repository import PatientRepository
from src.repositories.treatment_event_repository import TreatmentEventRepository
from src.repositories.treatment_repository import TreatmentRepository
from src.services.operational_settings_service import OperationalSettingsService


MVP_DAILY_AVAILABLE_MINUTES = 8 * 60


@dataclass(frozen=True)
class AnalyticsFilters:
    clinic: str | None = None
    chair: str | None = None
    professional: str | None = None
    status: AppointmentStatus | None = None


@dataclass(frozen=True)
class AnalyticsSummary:
    start_date: datetime
    end_date: datetime
    filters: AnalyticsFilters
    total_appointments: int
    completed_appointments: int
    cancelled_appointments: int
    no_show_appointments: int
    completion_rate: float
    cancellation_rate: float
    no_show_rate: float
    occupied_minutes: int
    available_minutes: int
    occupation_rate: float | None
    occupation_basis: str
    appointments_by_status: list[dict[str, Any]]
    appointments_by_day: list[dict[str, Any]]
    usage_by_clinic: list[dict[str, Any]]
    usage_by_chair: list[dict[str, Any]]
    usage_by_professional: list[dict[str, Any]]
    frequent_treatments: list[dict[str, Any]]
    treatment_evolution: list[dict[str, Any]]
    patients_with_recent_activity: int
    patients_without_recent_activity: int
    patients_with_upcoming_appointment: int
    recent_activity_days: int
    detail_rows: list[dict[str, Any]]


class AnalyticsService:
    def __init__(
        self,
        patient_repository: PatientRepository | None = None,
        appointment_repository: AppointmentRepository | None = None,
        treatment_repository: TreatmentRepository | None = None,
        treatment_event_repository: TreatmentEventRepository | None = None,
        operational_settings_service: OperationalSettingsService | None = None,
    ):
        database = None
        if any(
            repository is None
            for repository in [
                patient_repository,
                appointment_repository,
                treatment_repository,
                treatment_event_repository,
            ]
        ):
            database = get_database()

        self._patients = patient_repository or PatientRepository(database)
        self._appointments = appointment_repository or AppointmentRepository(database)
        self._treatments = treatment_repository or TreatmentRepository(database)
        self._events = treatment_event_repository or TreatmentEventRepository(database)
        self._settings_service = operational_settings_service
        if self._settings_service is None and database is not None:
            self._settings_service = OperationalSettingsService(OperationalSettingsRepository(database))

    def weekly_summary(
        self,
        reference_date: datetime | None = None,
        filters: AnalyticsFilters | None = None,
    ) -> AnalyticsSummary:
        reference = reference_date or datetime.now()
        start = reference - timedelta(days=reference.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
        return self.summary(start, end, filters=filters)

    def summary(
        self,
        start_date: datetime,
        end_date: datetime,
        filters: AnalyticsFilters | None = None,
    ) -> AnalyticsSummary:
        resolved_filters = filters or AnalyticsFilters()
        settings = self._settings_service.get_settings() if self._settings_service else None
        appointments = self._filter_appointments(
            self._appointments.find_by_date_range(start_date, end_date, limit=0),
            resolved_filters,
        )
        raw_events = self._events.find_many(
            {"event_date": {"$gte": start_date, "$lt": end_date}},
            limit=0,
            sort=[("event_date", 1)],
        )
        events = self._filter_events_by_appointments(
            raw_events,
            appointments,
            resolved_filters,
        )

        status_counts = Counter(appointment.status.value for appointment in appointments)
        total_appointments = len(appointments)
        cancelled = status_counts.get(AppointmentStatus.CANCELLED.value, 0)
        no_show = status_counts.get(AppointmentStatus.NO_SHOW.value, 0)
        completed = status_counts.get(AppointmentStatus.COMPLETED.value, 0)

        occupied_minutes = sum(
            appointment.duration_minutes
            for appointment in appointments
            if appointment.status
            not in {
                AppointmentStatus.CANCELLED,
                AppointmentStatus.NO_SHOW,
            }
        )
        available_minutes, occupation_basis = self._available_minutes(
            start_date,
            end_date,
            appointments,
            resolved_filters,
            settings,
        )
        occupation_rate = occupied_minutes / available_minutes if available_minutes else None

        patient_activity = self._patient_activity(
            start_date,
            end_date,
            resolved_filters,
            appointments,
            events,
            settings.analytics.inactive_patient_days if settings else 90,
        )

        return AnalyticsSummary(
            start_date=start_date,
            end_date=end_date,
            filters=resolved_filters,
            total_appointments=total_appointments,
            completed_appointments=completed,
            cancelled_appointments=cancelled,
            no_show_appointments=no_show,
            completion_rate=self._safe_ratio(completed, total_appointments),
            cancellation_rate=self._safe_ratio(cancelled, total_appointments),
            no_show_rate=self._safe_ratio(no_show, total_appointments),
            occupied_minutes=occupied_minutes,
            available_minutes=available_minutes,
            occupation_rate=occupation_rate,
            occupation_basis=occupation_basis,
            appointments_by_status=[
                {"status": status, "count": count}
                for status, count in sorted(status_counts.items())
            ],
            appointments_by_day=self._appointments_by_day(appointments),
            usage_by_clinic=self._usage_rows(appointments, "clinic", "Sin clinica"),
            usage_by_chair=self._usage_rows(appointments, "chair", "Sin gabinete"),
            usage_by_professional=self._usage_rows(
                appointments,
                "professional",
                "Sin profesional",
            ),
            frequent_treatments=self._frequent_treatments_from_events(events),
            treatment_evolution=self._treatment_evolution(events),
            patients_with_recent_activity=patient_activity["with_recent_activity"],
            patients_without_recent_activity=patient_activity["without_recent_activity"],
            patients_with_upcoming_appointment=patient_activity["with_upcoming_appointment"],
            recent_activity_days=patient_activity["recent_activity_days"],
            detail_rows=self._detail_rows(appointments),
        )

    def _filter_appointments(
        self,
        appointments: list[Appointment],
        filters: AnalyticsFilters,
    ) -> list[Appointment]:
        return [
            appointment
            for appointment in appointments
            if (filters.clinic is None or appointment.clinic == filters.clinic)
            and (filters.chair is None or appointment.chair == filters.chair)
            and (filters.professional is None or appointment.professional == filters.professional)
            and (filters.status is None or appointment.status == filters.status)
        ]

    def _filter_events_by_appointments(
        self,
        events: list[TreatmentEvent],
        appointments: list[Appointment],
        filters: AnalyticsFilters,
    ) -> list[TreatmentEvent]:
        if not self._has_operational_filters(filters):
            return events

        allowed_appointment_ids = {
            appointment.id
            for appointment in appointments
            if appointment.id is not None
        }
        return [
            event
            for event in events
            if event.appointment_id in allowed_appointment_ids
        ]

    def _has_operational_filters(self, filters: AnalyticsFilters) -> bool:
        return any(
            [
                filters.clinic,
                filters.chair,
                filters.professional,
                filters.status,
            ]
        )

    def _available_minutes(
        self,
        start_date: datetime,
        end_date: datetime,
        appointments: list[Appointment],
        filters: AnalyticsFilters,
        settings: OperationalSettings | None,
    ) -> tuple[int, str]:
        if settings is not None:
            configured_minutes = self._configured_available_minutes(start_date, end_date, filters, settings)
            if configured_minutes > 0:
                return configured_minutes, "Ocupacion calculada con horarios operativos configurados."

        working_days = self._working_days(start_date, end_date)
        if working_days == 0:
            return 0, "No hay dias laborables en el periodo seleccionado."

        if filters.chair:
            resource_count = 1
        else:
            resource_count = max(
                1,
                len({appointment.chair for appointment in appointments if appointment.chair}),
            )
        return (
            working_days * MVP_DAILY_AVAILABLE_MINUTES * resource_count,
            "Ocupacion estimada a 8 horas de consulta por dia laborable y gabinete visible.",
        )

    def _configured_available_minutes(
        self,
        start_date: datetime,
        end_date: datetime,
        filters: AnalyticsFilters,
        settings: OperationalSettings,
    ) -> int:
        clinic_names = [clinic.name for clinic in settings.clinics if clinic.active]
        if filters.clinic:
            clinic_names = [filters.clinic] if filters.clinic in clinic_names else []

        clinic_codes_by_name = {clinic.name: clinic.code for clinic in settings.clinics}
        active_chairs_by_clinic = {
            clinic.code: [
                chair
                for chair in settings.chairs
                if chair.active
                and chair.clinic_code == clinic.code
                and (filters.chair is None or chair.name == filters.chair)
            ]
            for clinic in settings.clinics
            if clinic.active
        }

        total_minutes = 0
        current = start_date.date()
        while current < end_date.date():
            day_name = current.strftime("%A").lower()
            for clinic_name in clinic_names:
                clinic_code = clinic_codes_by_name.get(clinic_name)
                if clinic_code is None:
                    continue
                schedule = settings.weekly_schedule.get(clinic_code)
                day_schedule = getattr(schedule, day_name, None) if schedule else None
                if day_schedule is None or day_schedule.closed:
                    continue
                chair_count = len(active_chairs_by_clinic.get(clinic_code, []))
                if chair_count == 0:
                    continue
                total_minutes += chair_count * sum(
                    self._block_minutes(block.start, block.end)
                    for block in day_schedule.blocks
                )
            current += timedelta(days=1)
        return total_minutes

    def _block_minutes(self, start: str, end: str) -> int:
        start_hour, start_minute = [int(part) for part in start.split(":", 1)]
        end_hour, end_minute = [int(part) for part in end.split(":", 1)]
        return (end_hour * 60 + end_minute) - (start_hour * 60 + start_minute)

    def _working_days(self, start_date: datetime, end_date: datetime) -> int:
        days = 0
        current = start_date.date()
        while current < end_date.date():
            if current.weekday() < 5:
                days += 1
            current += timedelta(days=1)
        return days

    def _appointments_by_day(self, appointments: list[Appointment]) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"appointments": 0, "minutes": 0}
        )
        for appointment in appointments:
            key = appointment.scheduled_start.date().isoformat()
            grouped[key]["appointments"] += 1
            grouped[key]["minutes"] += appointment.duration_minutes
        return [
            {"date": key, **value}
            for key, value in sorted(grouped.items())
        ]

    def _usage_rows(
        self,
        appointments: list[Appointment],
        field_name: str,
        fallback: str,
    ) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"appointments": 0, "minutes": 0}
        )
        for appointment in appointments:
            key = getattr(appointment, field_name) or fallback
            grouped[key]["appointments"] += 1
            grouped[key]["minutes"] += appointment.duration_minutes
        return [
            {field_name: key, **value}
            for key, value in sorted(grouped.items())
        ]

    def _frequent_treatments_from_events(self, events: list[TreatmentEvent]) -> list[dict[str, Any]]:
        counter: Counter[str] = Counter()
        for event in events:
            if event.event_type != TreatmentEventType.COMPLETED:
                continue
            treatment = self._treatments.find_by_id(event.treatment_id)
            if treatment is not None:
                counter[treatment.treatment_type] += 1
        return [
            {"treatment_type": treatment_type, "count": count}
            for treatment_type, count in counter.most_common(10)
        ]

    def _treatment_evolution(self, events: list[TreatmentEvent]) -> list[dict[str, Any]]:
        grouped = Counter(event.event_date.date().isoformat() for event in events)
        return [
            {"date": date_key, "events": count}
            for date_key, count in sorted(grouped.items())
        ]

    def _patient_activity(
        self,
        start_date: datetime,
        end_date: datetime,
        filters: AnalyticsFilters,
        appointments_in_period: list[Appointment],
        events_in_period: list[TreatmentEvent],
        recent_activity_days: int,
    ) -> dict[str, int]:
        recent_activity_start = end_date - timedelta(days=recent_activity_days)
        patients = self._patients.find_many(limit=0)
        patients_with_activity = {
            appointment.patient_id
            for appointment in appointments_in_period
        } | {
            event.patient_id
            for event in events_in_period
        }
        raw_recent_appointments = self._appointments.find_by_date_range(
            recent_activity_start,
            end_date,
            limit=0,
        )
        recent_appointments = self._filter_appointments(raw_recent_appointments, filters)
        raw_recent_events = self._events.find_many(
            {"event_date": {"$gte": recent_activity_start, "$lt": end_date}},
            limit=0,
        )
        recent_events = self._filter_events_by_appointments(
            raw_recent_events,
            recent_appointments,
            filters,
        )
        patients_with_recent_activity = {
            appointment.patient_id
            for appointment in recent_appointments
        } | {
            event.patient_id
            for event in recent_events
        }
        now = datetime.now(tz=end_date.tzinfo)
        raw_upcoming_appointments = self._appointments.find_many(
            {"scheduled_start": {"$gte": now}},
            limit=0,
        )
        upcoming_appointments = self._filter_appointments(raw_upcoming_appointments, filters)
        upcoming_patient_ids = {
            appointment.patient_id
            for appointment in upcoming_appointments
            if appointment.status != AppointmentStatus.CANCELLED
        }
        return {
            "with_recent_activity": len(patients_with_activity),
            "without_recent_activity": max(0, len(patients) - len(patients_with_recent_activity)),
            "with_upcoming_appointment": len(upcoming_patient_ids),
            "recent_activity_days": recent_activity_days,
        }

    def _detail_rows(self, appointments: list[Appointment]) -> list[dict[str, Any]]:
        return [
            {
                "date": appointment.scheduled_start.date().isoformat(),
                "time": appointment.scheduled_start.strftime("%H:%M"),
                "status": appointment.status.value,
                "clinic": appointment.clinic or "Sin clinica",
                "chair": appointment.chair or "Sin gabinete",
                "professional": appointment.professional or "Sin profesional",
                "minutes": appointment.duration_minutes,
                "reason": appointment.reason,
            }
            for appointment in appointments
        ]

    def _safe_ratio(self, numerator: int, denominator: int) -> float:
        return numerator / denominator if denominator else 0.0
