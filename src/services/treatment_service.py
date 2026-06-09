from datetime import datetime
from dataclasses import dataclass
from typing import Any

from bson import ObjectId

from src.database.connection import get_database
from src.models.appointment import Appointment
from src.models.base import utc_now
from src.models.treatment import Treatment, TreatmentStatus
from src.models.treatment_catalog import TreatmentCatalogItem
from src.models.treatment_event import TreatmentEvent, TreatmentEventType
from src.repositories.appointment_repository import AppointmentRepository
from src.repositories.patient_repository import PatientRepository
from src.repositories.treatment_catalog_repository import TreatmentCatalogRepository
from src.repositories.treatment_event_repository import TreatmentEventRepository
from src.repositories.treatment_repository import TreatmentRepository


@dataclass(frozen=True)
class TreatmentRecord:
    treatment: Treatment
    patient: Any | None
    appointment: Appointment | None
    latest_event: TreatmentEvent | None


@dataclass(frozen=True)
class TreatmentEventRecord:
    event: TreatmentEvent
    treatment: Treatment | None
    patient: Any | None
    appointment: Appointment | None


class TreatmentServiceError(ValueError):
    pass


class TreatmentService:
    def __init__(
        self,
        treatment_repository: TreatmentRepository | None = None,
        treatment_event_repository: TreatmentEventRepository | None = None,
        patient_repository: PatientRepository | None = None,
        treatment_catalog_repository: TreatmentCatalogRepository | None = None,
        appointment_repository: AppointmentRepository | None = None,
    ):
        database = None
        if any(
            repository is None
            for repository in [
                treatment_repository,
                treatment_event_repository,
                patient_repository,
                treatment_catalog_repository,
                appointment_repository,
            ]
        ):
            database = get_database()
        self._treatments = treatment_repository or TreatmentRepository(database)
        self._events = treatment_event_repository or TreatmentEventRepository(database)
        self._patients = patient_repository or PatientRepository(database)
        self._catalog = treatment_catalog_repository or TreatmentCatalogRepository(database)
        self._appointments = appointment_repository or AppointmentRepository(database)

    def search_catalog(
        self,
        search_text: str = "",
        include_inactive: bool = True,
        limit: int = 100,
    ) -> list[TreatmentCatalogItem]:
        return self._catalog.search(search_text, include_inactive=include_inactive, limit=limit)

    def create_catalog_item(
        self,
        name: str,
        category: str | None = None,
        default_duration_minutes: int | None = None,
        base_price: float | None = None,
        active: bool = True,
        notes: str | None = None,
    ) -> TreatmentCatalogItem:
        payload = self._normalize_catalog_changes(
            {
                "name": name,
                "category": category,
                "default_duration_minutes": default_duration_minutes,
                "base_price": base_price,
                "active": active,
                "notes": notes,
            },
            require_name=True,
        )
        return self._catalog.create(
            TreatmentCatalogItem(
                catalog_code=self._build_catalog_code(),
                **payload,
            ),
        )

    def update_catalog_item(self, catalog_item_id: ObjectId | str, changes: dict[str, Any]) -> TreatmentCatalogItem | None:
        return self._catalog.update_catalog_fields(
            catalog_item_id,
            self._normalize_catalog_changes(changes, require_name=False),
        )

    def set_catalog_active(self, catalog_item_id: ObjectId | str, active: bool) -> TreatmentCatalogItem | None:
        return self.update_catalog_item(catalog_item_id, {"active": active})

    def list_treatments(self, limit: int = 100) -> list[Treatment]:
        return self._treatments.find_many(limit=limit, sort=[("created_at", -1)])

    def list_treatment_records(
        self,
        patient_id: ObjectId | str | None = None,
        treatment_query: str = "",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
    ) -> list[TreatmentRecord]:
        records = []
        treatments = self.list_by_patient(patient_id, limit=limit) if patient_id else self.list_treatments(limit=limit)
        for treatment in treatments:
            if not self._matches_treatment_filters(treatment, treatment_query, start_date, end_date):
                continue
            events = self._events.find_by_treatment_id(treatment.id, limit=50) if treatment.id else []
            records.append(
                TreatmentRecord(
                    treatment=treatment,
                    patient=self._patients.find_by_id(treatment.patient_id),
                    appointment=self._appointments.find_by_id(treatment.appointment_id) if treatment.appointment_id else None,
                    latest_event=events[-1] if events else None,
                ),
            )
        return records

    def list_events(
        self,
        patient_id: ObjectId | str | None = None,
        treatment_query: str = "",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
    ) -> list[TreatmentEventRecord]:
        events = (
            self._events.find_by_patient_id(patient_id, limit=limit)
            if patient_id
            else self._events.find_many(limit=limit, sort=[("event_date", -1)])
        )
        records = []
        for event in events:
            record = self._event_record(event)
            if self._matches_event_filters(record, treatment_query, start_date, end_date):
                records.append(record)
        return records

    def list_by_patient(self, patient_id: ObjectId | str, limit: int = 100) -> list[Treatment]:
        return self._treatments.find_by_patient_id(patient_id, limit=limit)

    def list_patient_appointments(self, patient_id: ObjectId | str, limit: int = 100) -> list[Appointment]:
        return self._appointments.find_by_patient_id(patient_id, limit=limit)

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
        treatment_type = self._clean_text(treatment_type)
        if not treatment_type:
            raise TreatmentServiceError("El tipo de tratamiento es obligatorio.")
        if estimated_price is not None and estimated_price < 0:
            raise TreatmentServiceError("El precio estimado no puede ser negativo.")

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

    def register_performed_treatment(
        self,
        patient_id: ObjectId | str,
        catalog_item_id: ObjectId | str,
        event_date: datetime,
        appointment_id: ObjectId | str | None = None,
        notes: str | None = None,
        created_by: str | None = None,
    ) -> Treatment:
        catalog_item = self._catalog.find_by_id(catalog_item_id)
        if catalog_item is None:
            raise TreatmentServiceError("El tratamiento de catalogo seleccionado no existe.")
        if not catalog_item.active:
            raise TreatmentServiceError("El tratamiento de catalogo esta inactivo.")
        treatment = self.create_treatment(
            patient_id=patient_id,
            treatment_type=catalog_item.name,
            description=catalog_item.category,
            appointment_id=appointment_id,
            planned_date=event_date,
            estimated_price=catalog_item.base_price,
            notes=notes,
            created_by=created_by,
        )
        updated = self.update_status(
            treatment.id,
            TreatmentStatus.COMPLETED,
            description=notes or "Treatment performed from catalog.",
            created_by=created_by,
        )
        return updated or treatment

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

    def _event_record(self, event: TreatmentEvent) -> TreatmentEventRecord:
        treatment = self._treatments.find_by_id(event.treatment_id)
        return TreatmentEventRecord(
            event=event,
            treatment=treatment,
            patient=self._patients.find_by_id(event.patient_id),
            appointment=self._appointments.find_by_id(event.appointment_id) if event.appointment_id else None,
        )

    def _normalize_catalog_changes(self, changes: dict[str, Any], require_name: bool) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        if require_name or "name" in changes:
            name = self._clean_text(changes.get("name"))
            if not name:
                raise TreatmentServiceError("El nombre del tratamiento es obligatorio.")
            normalized["name"] = name
        if "category" in changes:
            normalized["category"] = self._clean_text(changes.get("category"))
        if "default_duration_minutes" in changes:
            duration = changes.get("default_duration_minutes")
            normalized["default_duration_minutes"] = int(duration) if duration not in (None, "") else None
            if normalized["default_duration_minutes"] is not None and normalized["default_duration_minutes"] <= 0:
                raise TreatmentServiceError("La duracion debe ser positiva.")
        if "base_price" in changes:
            price = changes.get("base_price")
            normalized["base_price"] = float(price) if price not in (None, "") else None
            if normalized["base_price"] is not None and normalized["base_price"] < 0:
                raise TreatmentServiceError("El precio no puede ser negativo.")
        if "active" in changes:
            normalized["active"] = bool(changes.get("active"))
        if "notes" in changes:
            normalized["notes"] = self._clean_text(changes.get("notes"))
        return normalized

    def _clean_text(self, value: Any) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    def _matches_treatment_filters(
        self,
        treatment: Treatment,
        treatment_query: str,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> bool:
        if treatment_query.strip() and treatment_query.strip().lower() not in treatment.treatment_type.lower():
            return False
        activity_date = treatment.planned_date or treatment.created_at
        if start_date and activity_date < start_date:
            return False
        if end_date and activity_date >= end_date:
            return False
        return True

    def _matches_event_filters(
        self,
        record: TreatmentEventRecord,
        treatment_query: str,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> bool:
        if treatment_query.strip():
            treatment_name = record.treatment.treatment_type if record.treatment else ""
            if treatment_query.strip().lower() not in treatment_name.lower():
                return False
        if start_date and record.event.event_date < start_date:
            return False
        if end_date and record.event.event_date >= end_date:
            return False
        return True

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

    def _build_catalog_code(self) -> str:
        return f"TCAT-{utc_now().strftime('%Y%m%d%H%M%S%f')}"
