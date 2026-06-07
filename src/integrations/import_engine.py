from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pydantic import ValidationError

from src.integrations.adapters.csv_adapter import CsvImportAdapter
from src.integrations.adapters.json_adapter import JsonImportAdapter
from src.integrations.mapping.appointment_mapper import external_to_appointment
from src.integrations.mapping.patient_mapper import external_to_patient
from src.integrations.validators.import_validators import (
    validate_appointment_record,
    validate_patient_record,
)


@dataclass(frozen=True)
class ImportSummary:
    entity: str
    source_format: str
    records_read: int = 0
    records_valid: int = 0
    records_imported: int = 0
    records_skipped: int = 0
    validation_errors: list[dict[str, Any]] = field(default_factory=list)
    imported_ids: list[str] = field(default_factory=list)
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity": self.entity,
            "source_format": self.source_format,
            "records_read": self.records_read,
            "records_valid": self.records_valid,
            "records_imported": self.records_imported,
            "records_skipped": self.records_skipped,
            "validation_errors": self.validation_errors,
            "imported_ids": self.imported_ids,
            "executed_at": self.executed_at.isoformat(),
        }


class ImportEngine:
    def __init__(self) -> None:
        self._adapters = {
            "csv": CsvImportAdapter,
            "json": JsonImportAdapter,
        }

    def import_data(
        self,
        entity: str,
        source_format: str,
        source: Any,
        repository: Any,
        related_repositories: dict[str, Any] | None = None,
    ) -> ImportSummary:
        normalized_entity = entity.strip().lower()
        normalized_format = source_format.strip().lower()
        if normalized_format not in self._adapters:
            return ImportSummary(
                entity=normalized_entity,
                source_format=normalized_format,
                validation_errors=[{"row": None, "errors": [f"Unsupported import format: {source_format}."]}],
            )

        adapter = self._adapters[normalized_format]()
        try:
            raw_records = adapter.read(source)
        except Exception as exc:
            return ImportSummary(
                entity=normalized_entity,
                source_format=normalized_format,
                validation_errors=[{"row": None, "errors": [str(exc)]}],
            )

        valid_models: list[Any] = []
        validation_errors: list[dict[str, Any]] = []

        for index, record in enumerate(raw_records, start=1):
            errors = self._validate_record(normalized_entity, record, repository)
            if errors:
                validation_errors.append({"row": index, "errors": errors})
                continue

            try:
                valid_models.append(
                    self._map_record(
                        normalized_entity,
                        record,
                        related_repositories=related_repositories or {},
                    ),
                )
            except (ValidationError, ValueError) as exc:
                validation_errors.append({"row": index, "errors": [str(exc)]})

        imported_ids: list[str] = []
        for model in valid_models:
            created = repository.create(model)
            created_id = getattr(created, "id", None)
            if created_id is not None:
                imported_ids.append(str(created_id))

        return ImportSummary(
            entity=normalized_entity,
            source_format=normalized_format,
            records_read=len(raw_records),
            records_valid=len(valid_models),
            records_imported=len(imported_ids),
            records_skipped=len(raw_records) - len(valid_models),
            validation_errors=validation_errors,
            imported_ids=imported_ids,
        )

    def _validate_record(self, entity: str, record: dict[str, Any], repository: Any) -> list[str]:
        if entity == "patients":
            return validate_patient_record(record, repository=repository)
        if entity == "appointments":
            return validate_appointment_record(record, repository=repository)
        return [f"Unsupported import entity: {entity}."]

    def _map_record(
        self,
        entity: str,
        record: dict[str, Any],
        related_repositories: dict[str, Any],
    ) -> Any:
        if entity == "patients":
            return external_to_patient(record)
        if entity == "appointments":
            patient_id = self._resolve_patient_id(record, related_repositories.get("patients"))
            if patient_id is None:
                raise ValueError("Appointment patient reference could not be resolved.")
            return external_to_appointment(record, patient_id=patient_id)
        raise ValueError(f"Unsupported import entity: {entity}.")

    def _resolve_patient_id(self, record: dict[str, Any], patient_repository: Any | None) -> ObjectId | str | None:
        explicit_id = record.get("patient_id") or record.get("internal_patient_id")
        if explicit_id:
            return explicit_id
        if patient_repository is None:
            return None

        external_id = record.get("external_patient_id")
        patient_code = record.get("patient_code")
        if external_id:
            patients = patient_repository.find_many({"external_patient_id": external_id}, limit=1)
            if patients:
                return patients[0].id
        if patient_code:
            patients = patient_repository.find_many({"patient_code": patient_code}, limit=1)
            if patients:
                return patients[0].id
        return None
