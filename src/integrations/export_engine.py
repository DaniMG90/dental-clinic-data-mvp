from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.integrations.adapters.csv_adapter import CsvExportAdapter
from src.integrations.adapters.json_adapter import JsonExportAdapter
from src.integrations.mapping.appointment_mapper import appointment_to_external
from src.integrations.mapping.metrics_mapper import metrics_to_export
from src.integrations.mapping.patient_mapper import patient_to_external
from src.integrations.validators.export_validators import validate_export_request


@dataclass(frozen=True)
class ExportSummary:
    entity: str
    export_format: str
    records_exported: int = 0
    file_path: str | None = None
    errors: list[str] = field(default_factory=list)
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity": self.entity,
            "export_format": self.export_format,
            "records_exported": self.records_exported,
            "file_path": self.file_path,
            "errors": self.errors,
            "executed_at": self.executed_at.isoformat(),
        }


class ExportEngine:
    def __init__(self, export_root: str | Path = "data/exports") -> None:
        self.export_root = Path(export_root)
        self._adapters = {
            "csv": CsvExportAdapter,
            "json": JsonExportAdapter,
        }

    def export_data(
        self,
        entity: str,
        export_format: str,
        repositories: dict[str, Any],
    ) -> ExportSummary:
        normalized_entity = entity.strip().lower()
        normalized_format = export_format.strip().lower()
        errors = validate_export_request(normalized_entity, normalized_format)
        if errors:
            return ExportSummary(entity=normalized_entity, export_format=normalized_format, errors=errors)

        try:
            records = self._collect_entity_data(normalized_entity, repositories)
            mapped_records = self._map_entity_data(normalized_entity, records)
            destination = self._build_destination(normalized_entity, normalized_format)
            adapter = self._adapters[normalized_format]()
            path = adapter.write(destination, mapped_records)
        except Exception as exc:
            return ExportSummary(
                entity=normalized_entity,
                export_format=normalized_format,
                errors=[str(exc)],
            )

        return ExportSummary(
            entity=normalized_entity,
            export_format=normalized_format,
            records_exported=len(mapped_records),
            file_path=str(path),
        )

    def _collect_entity_data(self, entity: str, repositories: dict[str, Any]) -> list[Any] | dict[str, Any]:
        if entity == "patients":
            return repositories["patients"].find_many(limit=0)
        if entity == "appointments":
            return repositories["appointments"].find_many(limit=0)
        if entity == "metrics":
            return self._collect_metrics(repositories)
        raise ValueError(f"Unsupported export entity: {entity}.")

    def _map_entity_data(self, entity: str, records: list[Any] | dict[str, Any]) -> list[dict[str, Any]]:
        if entity == "patients":
            return [patient_to_external(patient) for patient in records]
        if entity == "appointments":
            return [appointment_to_external(appointment) for appointment in records]
        if entity == "metrics":
            return metrics_to_export(records)
        raise ValueError(f"Unsupported export entity: {entity}.")

    def _collect_metrics(self, repositories: dict[str, Any]) -> dict[str, Any]:
        patients_repository = repositories.get("patients")
        appointments_repository = repositories.get("appointments")

        metrics: dict[str, Any] = {}
        if patients_repository is not None:
            metrics["patients_total"] = len(patients_repository.find_many(limit=0))
            metrics["patients_active"] = len(patients_repository.find_active_patients(limit=0))
            metrics["patients_inactive"] = len(patients_repository.find_inactive_patients(limit=0))
        if appointments_repository is not None:
            metrics["appointments_total"] = len(appointments_repository.find_many(limit=0))
            metrics["appointments_by_status"] = appointments_repository.count_by_status()
        return metrics

    def _build_destination(self, entity: str, export_format: str) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return self.export_root / entity / f"{entity}_{timestamp}.{export_format}"
