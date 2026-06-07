from dataclasses import dataclass
from datetime import datetime

from bson import ObjectId

from src.database.connection import get_database
from src.models.base import utc_now
from src.models.patient import Patient, PatientStatus
from src.models.treatment import Treatment
from src.models.treatment_event import TreatmentEvent
from src.repositories.appointment_repository import AppointmentRepository
from src.repositories.patient_repository import PatientRepository
from src.repositories.treatment_event_repository import TreatmentEventRepository
from src.repositories.treatment_repository import TreatmentRepository


@dataclass(frozen=True)
class PatientActivity:
    appointments_count: int
    treatments_count: int
    last_appointment_at: datetime | None
    next_appointment_at: datetime | None


@dataclass(frozen=True)
class PatientProfile:
    patient: Patient
    appointments: list
    treatments: list[Treatment]
    treatment_events: list[TreatmentEvent]
    activity: PatientActivity


class PatientService:
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

    def list_patients(self, limit: int = 100) -> list[Patient]:
        return self._patients.find_many(limit=limit, sort=[("last_name", 1), ("first_name", 1)])

    def search_patients(self, search_text: str, limit: int = 50) -> list[Patient]:
        if not search_text.strip():
            return self.list_patients(limit=limit)
        return self._patients.search_by_name_or_phone(search_text, limit=limit)

    def get_patient(self, patient_id: ObjectId | str) -> Patient | None:
        return self._patients.find_by_id(patient_id)

    def get_profile(self, patient_id: ObjectId | str) -> PatientProfile | None:
        patient = self.get_patient(patient_id)
        if patient is None:
            return None

        appointments = self._appointments.find_by_patient_id(patient.id, limit=200)
        treatments = self._treatments.find_by_patient_id(patient.id, limit=200)
        events = self._events.find_by_patient_id(patient.id, limit=200)
        now = datetime.now(tz=appointments[0].scheduled_start.tzinfo) if appointments else datetime.now()
        past_appointments = [item for item in appointments if item.scheduled_start <= now]
        future_appointments = [item for item in appointments if item.scheduled_start > now]

        activity = PatientActivity(
            appointments_count=len(appointments),
            treatments_count=len(treatments),
            last_appointment_at=past_appointments[-1].scheduled_start if past_appointments else None,
            next_appointment_at=future_appointments[0].scheduled_start if future_appointments else None,
        )
        return PatientProfile(patient, appointments, treatments, events, activity)

    def create_patient(
        self,
        first_name: str,
        last_name: str,
        phone: str | None = None,
        email: str | None = None,
        notes: str | None = None,
        tags: list[str] | None = None,
    ) -> Patient:
        patient = Patient(
            patient_code=self._build_patient_code(),
            first_name=first_name,
            last_name=last_name,
            phone=phone or None,
            email=email or None,
            status=PatientStatus.ACTIVE,
            tags=tags or [],
            notes=notes or None,
        )
        return self._patients.create(patient)

    def update_patient(self, patient_id: ObjectId | str, changes: dict) -> Patient | None:
        return self._patients.update(patient_id, changes)

    def _build_patient_code(self) -> str:
        return f"PAT-{utc_now().strftime('%Y%m%d%H%M%S%f')}"
