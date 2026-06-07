from dataclasses import dataclass
from datetime import datetime, timedelta

from bson import ObjectId

from src.database.connection import get_database
from src.models.appointment import Appointment, AppointmentStatus
from src.models.base import utc_now
from src.repositories.appointment_repository import AppointmentRepository
from src.repositories.patient_repository import PatientRepository


@dataclass(frozen=True)
class AgendaFilters:
    clinic: str | None = None
    chair: str | None = None
    professional: str | None = None
    status: AppointmentStatus | None = None


class AppointmentService:
    def __init__(
        self,
        appointment_repository: AppointmentRepository | None = None,
        patient_repository: PatientRepository | None = None,
    ):
        database = None
        if appointment_repository is None or patient_repository is None:
            database = get_database()
        self._appointments = appointment_repository or AppointmentRepository(database)
        self._patients = patient_repository or PatientRepository(database)

    def list_agenda(
        self,
        start_date: datetime,
        end_date: datetime,
        filters: AgendaFilters | None = None,
        limit: int = 500,
    ) -> list[Appointment]:
        appointments = self._appointments.find_by_date_range(start_date, end_date, limit=limit)
        if filters is None:
            return appointments
        return [
            appointment
            for appointment in appointments
            if self._matches_filters(appointment, filters)
        ]

    def list_with_patients(
        self,
        start_date: datetime,
        end_date: datetime,
        filters: AgendaFilters | None = None,
    ) -> list[dict]:
        rows = []
        for appointment in self.list_agenda(start_date, end_date, filters):
            patient = self._patients.find_by_id(appointment.patient_id)
            rows.append({"appointment": appointment, "patient": patient})
        return rows

    def create_appointment(
        self,
        patient_id: ObjectId | str,
        scheduled_start: datetime,
        duration_minutes: int,
        reason: str | None = None,
        clinic: str | None = None,
        chair: str | None = None,
        professional: str | None = None,
        notes: str | None = None,
    ) -> tuple[Appointment, list[Appointment]]:
        scheduled_end = scheduled_start + timedelta(minutes=duration_minutes)
        appointment = Appointment(
            appointment_code=self._build_appointment_code(),
            patient_id=patient_id,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            duration_minutes=duration_minutes,
            status=AppointmentStatus.SCHEDULED,
            reason=reason or None,
            clinic=clinic or None,
            chair=chair or None,
            professional=professional or None,
            notes=notes or None,
        )
        overlaps = self.find_overlaps(scheduled_start, scheduled_end)
        return self._appointments.create(appointment), overlaps

    def update_appointment(self, appointment_id: ObjectId | str, changes: dict) -> Appointment | None:
        if "duration_minutes" in changes and "scheduled_start" in changes:
            changes["scheduled_end"] = changes["scheduled_start"] + timedelta(minutes=changes["duration_minutes"])
        return self._appointments.update(appointment_id, changes)

    def cancel_appointment(
        self,
        appointment_id: ObjectId | str,
        cancellation_reason: str | None = None,
    ) -> Appointment | None:
        return self._appointments.update(
            appointment_id,
            {
                "status": AppointmentStatus.CANCELLED,
                "cancelled_at": utc_now(),
                "cancellation_reason": cancellation_reason or None,
            },
        )

    def complete_appointment(self, appointment_id: ObjectId | str) -> Appointment | None:
        return self._appointments.update(appointment_id, {"status": AppointmentStatus.COMPLETED})

    def find_overlaps(
        self,
        scheduled_start: datetime,
        scheduled_end: datetime,
        appointment_id_to_exclude: ObjectId | str | None = None,
    ) -> list[Appointment]:
        return self._appointments.find_overlapping(
            scheduled_start,
            scheduled_end,
            appointment_id_to_exclude=appointment_id_to_exclude,
        )

    def _matches_filters(self, appointment: Appointment, filters: AgendaFilters) -> bool:
        checks = [
            filters.clinic is None or appointment.clinic == filters.clinic,
            filters.chair is None or appointment.chair == filters.chair,
            filters.professional is None or appointment.professional == filters.professional,
            filters.status is None or appointment.status == filters.status,
        ]
        return all(checks)

    def _build_appointment_code(self) -> str:
        return f"APT-{utc_now().strftime('%Y%m%d%H%M%S%f')}"
