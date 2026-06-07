from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from src.database.connection import get_database
from src.repositories.appointment_repository import AppointmentRepository
from src.repositories.patient_repository import PatientRepository
from src.repositories.treatment_event_repository import TreatmentEventRepository
from src.repositories.treatment_repository import TreatmentRepository


@dataclass(frozen=True)
class AnalyticsSummary:
    start_date: datetime
    end_date: datetime
    active_patients: int
    appointments_by_status: list[dict[str, Any]]
    cancellations: int
    occupation: list[dict[str, Any]]
    frequent_treatments: list[dict[str, Any]]
    treatment_evolution: list[dict[str, Any]]


class AnalyticsService:
    def __init__(
        self,
        patient_repository: PatientRepository | None = None,
        appointment_repository: AppointmentRepository | None = None,
        treatment_repository: TreatmentRepository | None = None,
        treatment_event_repository: TreatmentEventRepository | None = None,
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

    def weekly_summary(self, reference_date: datetime | None = None) -> AnalyticsSummary:
        reference = reference_date or datetime.now()
        start = reference - timedelta(days=reference.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
        return self.summary(start, end)

    def summary(self, start_date: datetime, end_date: datetime) -> AnalyticsSummary:
        appointments_by_status = self._appointments.count_by_status(start_date, end_date)
        cancellations = sum(
            item["count"]
            for item in appointments_by_status
            if item["status"] == "cancelled"
        )
        return AnalyticsSummary(
            start_date=start_date,
            end_date=end_date,
            active_patients=len(self._patients.find_active_patients(limit=0)),
            appointments_by_status=appointments_by_status,
            cancellations=cancellations,
            occupation=self._appointments.get_agenda_occupation(start_date, end_date),
            frequent_treatments=self._treatments.find_most_used_treatments(start_date, end_date),
            treatment_evolution=self._events.get_treatment_activity_evolution(start_date, end_date),
        )
