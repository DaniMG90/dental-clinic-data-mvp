from dataclasses import dataclass
from datetime import datetime
import re
from typing import Any

from bson import ObjectId

from src.database.connection import get_database
from src.models.appointment import AppointmentStatus
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
    upcoming_appointments_count: int
    past_appointments_count: int
    cancelled_appointments_count: int
    last_appointment_at: datetime | None
    next_appointment_at: datetime | None
    last_activity_at: datetime | None


@dataclass(frozen=True)
class PatientProfile:
    patient: Patient
    appointments: list
    treatments: list[Treatment]
    treatment_events: list[TreatmentEvent]
    activity: PatientActivity


class PatientServiceError(ValueError):
    pass


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
        cancelled_appointments = [item for item in appointments if item.status == AppointmentStatus.CANCELLED]

        activity = PatientActivity(
            appointments_count=len(appointments),
            treatments_count=len(treatments),
            upcoming_appointments_count=len(future_appointments),
            past_appointments_count=len(past_appointments),
            cancelled_appointments_count=len(cancelled_appointments),
            last_appointment_at=past_appointments[-1].scheduled_start if past_appointments else None,
            next_appointment_at=future_appointments[0].scheduled_start if future_appointments else None,
            last_activity_at=self._latest_activity_at(appointments, treatments, events),
        )
        return PatientProfile(patient, appointments, treatments, events, activity)

    def create_patient(
        self,
        first_name: str,
        last_name: str,
        phone: str | None = None,
        email: str | None = None,
        birth_date: datetime | None = None,
        status: PatientStatus = PatientStatus.ACTIVE,
        notes: str | None = None,
        tags: list[str] | None = None,
    ) -> Patient:
        payload = self._normalize_patient_changes(
            {
                "first_name": first_name,
                "last_name": last_name,
                "phone": phone,
                "email": email,
                "birth_date": birth_date,
                "status": status,
                "tags": tags or [],
                "notes": notes,
            },
            require_names=True,
        )
        patient = Patient(
            patient_code=self._build_patient_code(),
            first_name=payload["first_name"],
            last_name=payload["last_name"],
            birth_date=payload.get("birth_date"),
            phone=payload.get("phone"),
            email=payload.get("email"),
            status=payload.get("status", PatientStatus.ACTIVE),
            tags=payload.get("tags", []),
            notes=payload.get("notes"),
        )
        return self._patients.create(patient)

    def update_patient(self, patient_id: ObjectId | str, changes: dict) -> Patient | None:
        return self._patients.update_patient_fields(
            patient_id,
            self._normalize_patient_changes(changes, require_names=False),
        )

    def _normalize_patient_changes(self, changes: dict[str, Any], require_names: bool) -> dict[str, Any]:
        normalized: dict[str, Any] = {}

        first_name = self._clean_text(changes.get("first_name")) if "first_name" in changes else None
        last_name = self._clean_text(changes.get("last_name")) if "last_name" in changes else None
        if require_names or "first_name" in changes:
            if not first_name:
                raise PatientServiceError("El nombre del paciente es obligatorio.")
            normalized["first_name"] = first_name
        if require_names or "last_name" in changes:
            if not last_name:
                raise PatientServiceError("Los apellidos del paciente son obligatorios.")
            normalized["last_name"] = last_name

        if "phone" in changes:
            phone = self._clean_text(changes.get("phone"))
            if phone and not self._is_valid_phone(phone):
                raise PatientServiceError("El telefono debe tener un formato razonable.")
            normalized["phone"] = phone

        if "email" in changes:
            email = self._clean_text(changes.get("email"))
            if email and not self._is_valid_email(email):
                raise PatientServiceError("El email no tiene un formato valido.")
            normalized["email"] = email.lower() if email else None

        if "birth_date" in changes:
            normalized["birth_date"] = changes.get("birth_date")

        if "status" in changes:
            status = changes.get("status")
            normalized["status"] = status if isinstance(status, PatientStatus) else PatientStatus(status)

        if "tags" in changes:
            normalized["tags"] = [
                tag
                for tag in [self._clean_text(value) for value in changes.get("tags", [])]
                if tag
            ]

        if "notes" in changes:
            normalized["notes"] = self._clean_text(changes.get("notes"))

        return normalized

    def _clean_text(self, value: Any) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    def _is_valid_phone(self, value: str) -> bool:
        digits = re.sub(r"\D", "", value)
        return 6 <= len(digits) <= 15 and re.fullmatch(r"[+()0-9 .-]+", value) is not None

    def _is_valid_email(self, value: str) -> bool:
        return re.fullmatch(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value) is not None

    def _latest_activity_at(self, appointments: list, treatments: list[Treatment], events: list[TreatmentEvent]) -> datetime | None:
        candidates = [
            *[appointment.updated_at for appointment in appointments if appointment.updated_at],
            *[treatment.updated_at for treatment in treatments if treatment.updated_at],
            *[event.created_at for event in events if event.created_at],
        ]
        return max(candidates) if candidates else None

    def _build_patient_code(self) -> str:
        return f"PAT-{utc_now().strftime('%Y%m%d%H%M%S%f')}"
