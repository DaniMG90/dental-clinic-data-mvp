from datetime import datetime
from typing import Any


def validate_patient_record(record: dict[str, Any], repository: Any | None = None) -> list[str]:
    errors: list[str] = []
    has_name = any(record.get(key) for key in ("first_name", "name", "nombre"))
    has_identifier = any(record.get(key) for key in ("patient_code", "external_patient_id", "external_id", "id"))
    if not has_name and not has_identifier:
        errors.append("Patient record requires a name or external identifier.")

    email = record.get("email") or record.get("correo")
    if email and "@" not in str(email):
        errors.append("Patient email is not valid.")

    identifier = record.get("external_patient_id") or record.get("external_id") or record.get("id")
    patient_code = record.get("patient_code") or record.get("code") or record.get("codigo")
    if repository is not None and _patient_exists(repository, identifier, patient_code):
        errors.append("Patient duplicate detected by external identifier or patient code.")

    return errors


def validate_appointment_record(record: dict[str, Any], repository: Any | None = None) -> list[str]:
    errors: list[str] = []
    has_patient_reference = any(
        record.get(key)
        for key in (
            "patient_id",
            "internal_patient_id",
            "external_patient_id",
            "patient_code",
        )
    )
    if not has_patient_reference:
        errors.append("Appointment record requires patient_id, external_patient_id or patient_code.")

    scheduled_start = record.get("scheduled_start") or record.get("start") or record.get("fecha_hora")
    if not scheduled_start:
        errors.append("Appointment record requires scheduled_start.")
    elif not _is_datetime_like(scheduled_start):
        errors.append("Appointment scheduled_start must be an ISO datetime.")

    status = record.get("status") or record.get("estado")
    if status is None or str(status).strip() == "":
        errors.append("Appointment record requires status.")

    appointment_code = record.get("appointment_code") or record.get("code") or record.get("codigo")
    external_id = record.get("external_appointment_id") or record.get("external_id") or record.get("id")
    if repository is not None and _appointment_exists(repository, external_id, appointment_code):
        errors.append("Appointment duplicate detected by external identifier or appointment code.")

    return errors


def _patient_exists(repository: Any, external_id: Any, patient_code: Any) -> bool:
    filters = []
    if external_id:
        filters.append({"external_patient_id": external_id})
    if patient_code:
        filters.append({"patient_code": patient_code})
    return any(repository.find_many(filters=filters_item, limit=1) for filters_item in filters)


def _appointment_exists(repository: Any, external_id: Any, appointment_code: Any) -> bool:
    filters = []
    if external_id:
        filters.append({"external_appointment_id": external_id})
    if appointment_code:
        filters.append({"appointment_code": appointment_code})
    return any(repository.find_many(filters=filters_item, limit=1) for filters_item in filters)


def _is_datetime_like(value: Any) -> bool:
    if isinstance(value, datetime):
        return True
    try:
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return False
    return True
