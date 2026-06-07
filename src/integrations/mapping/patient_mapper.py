from datetime import datetime, timezone
from typing import Any

from src.models.patient import Patient, PatientStatus


def external_to_patient(record: dict[str, Any]) -> Patient:
    first_name = _first_present(record, "first_name", "name", "nombre")
    last_name = _first_present(record, "last_name", "surname", "apellidos") or "Unknown"
    external_id = _first_present(record, "external_patient_id", "external_id", "patient_id", "id")

    patient_code = _first_present(record, "patient_code", "code", "codigo")
    if not patient_code:
        patient_code = f"EXT-{external_id}" if external_id else f"IMPORT-{str(first_name).upper()}-{str(last_name).upper()}"

    return Patient(
        patient_code=patient_code,
        external_patient_id=external_id,
        first_name=first_name,
        last_name=last_name,
        birth_date=_parse_datetime(_first_present(record, "birth_date", "date_of_birth", "fecha_nacimiento")),
        phone=_first_present(record, "phone", "telefono", "mobile"),
        email=_first_present(record, "email", "correo"),
        status=_parse_patient_status(_first_present(record, "status", "estado")),
        tags=_parse_tags(record.get("tags")),
        notes=_first_present(record, "notes", "observaciones"),
    )


def patient_to_external(patient: Patient | dict[str, Any]) -> dict[str, Any]:
    data = patient.model_dump() if isinstance(patient, Patient) else dict(patient)
    return {
        "patient_code": data.get("patient_code"),
        "external_patient_id": data.get("external_patient_id"),
        "first_name": data.get("first_name"),
        "last_name": data.get("last_name"),
        "birth_date": _format_datetime(data.get("birth_date")),
        "phone": data.get("phone"),
        "email": data.get("email"),
        "status": str(data.get("status") or ""),
        "tags": ",".join(data.get("tags") or []),
        "is_demo": "demo" in (data.get("tags") or []),
    }


def _first_present(record: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return None


def _parse_patient_status(value: Any) -> PatientStatus:
    if value in (None, ""):
        return PatientStatus.ACTIVE
    normalized = str(value).strip().lower()
    if normalized in {"active", "activo"}:
        return PatientStatus.ACTIVE
    if normalized in {"inactive", "inactivo"}:
        return PatientStatus.INACTIVE
    if normalized in {"archived", "archivado"}:
        return PatientStatus.ARCHIVED
    return PatientStatus.ACTIVE


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _format_datetime(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _parse_tags(value: Any) -> list[str]:
    if value is None:
        return ["demo_import"]
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return [tag.strip() for tag in str(value).split(",") if tag.strip()]
