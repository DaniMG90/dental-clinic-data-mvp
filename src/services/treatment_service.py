from datetime import datetime

from bson import ObjectId

from src.database.connection import get_database
from src.models.base import utc_now
from src.models.treatment import Treatment, TreatmentStatus
from src.models.treatment_event import TreatmentEvent, TreatmentEventType
from src.repositories.patient_repository import PatientRepository
from src.repositories.treatment_event_repository import TreatmentEventRepository
from src.repositories.treatment_repository import TreatmentRepository


class TreatmentService:
    def __init__(
        self,
        treatment_repository: TreatmentRepository | None = None,
        treatment_event_repository: TreatmentEventRepository | None = None,
        patient_repository: PatientRepository | None = None,
    ):
        database = None
        if treatment_repository is None or treatment_event_repository is None or patient_repository is None:
            database = get_database()
        self._treatments = treatment_repository or TreatmentRepository(database)
        self._events = treatment_event_repository or TreatmentEventRepository(database)
        self._patients = patient_repository or PatientRepository(database)

    def list_treatments(self, limit: int = 100) -> list[Treatment]:
        return self._treatments.find_many(limit=limit, sort=[("created_at", -1)])

    def list_by_patient(self, patient_id: ObjectId | str, limit: int = 100) -> list[Treatment]:
        return self._treatments.find_by_patient_id(patient_id, limit=limit)

    def create_treatment(
        self,
        patient_id: ObjectId | str,
        treatment_type: str,
        description: str | None = None,
        appointment_id: ObjectId | str | None = None,
        planned_date: datetime | None = None,
        estimated_price: float | None = None,
        notes: str | None = None,
        created_by: str | None = None,
    ) -> Treatment:
        treatment = Treatment(
            treatment_code=self._build_treatment_code(),
            patient_id=patient_id,
            appointment_id=appointment_id,
            treatment_type=treatment_type,
            description=description or None,
            status=TreatmentStatus.PLANNED,
            planned_date=planned_date,
            estimated_price=estimated_price,
            notes=notes or None,
        )
        created = self._treatments.create(treatment)
        self._events.create(
            TreatmentEvent(
                treatment_id=created.id,
                patient_id=created.patient_id,
                appointment_id=created.appointment_id,
                event_type=TreatmentEventType.CREATED,
                event_date=utc_now(),
                new_status=created.status,
                description="Treatment created from operational UI.",
                created_by=created_by,
            ),
        )
        return created

    def update_status(
        self,
        treatment_id: ObjectId | str,
        new_status: TreatmentStatus,
        description: str | None = None,
        created_by: str | None = None,
    ) -> Treatment | None:
        treatment = self._treatments.find_by_id(treatment_id)
        if treatment is None:
            return None

        changes = {"status": new_status}
        if new_status == TreatmentStatus.IN_PROGRESS and treatment.started_at is None:
            changes["started_at"] = utc_now()
        if new_status == TreatmentStatus.COMPLETED:
            changes["completed_at"] = utc_now()

        updated = self._treatments.update(treatment_id, changes)
        self._events.create(
            TreatmentEvent(
                treatment_id=treatment.id,
                patient_id=treatment.patient_id,
                appointment_id=treatment.appointment_id,
                event_type=self._event_type_for_status(new_status),
                event_date=utc_now(),
                previous_status=treatment.status,
                new_status=new_status,
                description=description or "Treatment status updated.",
                created_by=created_by,
            ),
        )
        return updated

    def update_treatment(self, treatment_id: ObjectId | str, changes: dict) -> Treatment | None:
        return self._treatments.update(treatment_id, changes)

    def _event_type_for_status(self, status: TreatmentStatus) -> TreatmentEventType:
        if status == TreatmentStatus.COMPLETED:
            return TreatmentEventType.COMPLETED
        if status == TreatmentStatus.CANCELLED:
            return TreatmentEventType.CANCELLED
        if status == TreatmentStatus.POSTPONED:
            return TreatmentEventType.POSTPONED
        return TreatmentEventType.STATUS_CHANGED

    def _build_treatment_code(self) -> str:
        return f"TRT-{utc_now().strftime('%Y%m%d%H%M%S%f')}"
