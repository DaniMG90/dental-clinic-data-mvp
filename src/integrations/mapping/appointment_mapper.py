from datetime import datetime, timedelta, timezone
from typing import Any

from bson import ObjectId

from src.models.appointment import Appointment, AppointmentStatus


def external_to_appointment(record: dict[str, Any], patient_id: ObjectId | str | None = None) -> Appointment:
    start = _parse_datetime(_first_present(record, "scheduled_start", "start", "fecha_hora"))
    end = _parse_datetime(_first_present(record, "scheduled_end", "end", "fecha_hora_fin"))
    duration = int(_first_present(record, "duration_minutes", "duration", "duracion_minutos") or 30)
    if end is None and start is not None:
        end = start + timedelta(minutes=duration)

    external_id = _first_present(record, "external_appointment_id", "external_id", "appointment_id", "id")
    resolved_patient_id = patient_id or _first_present(record, "patient_id", "internal_patient_id")

    return Appointment(
        appointment_code=_first_present(record, "appointment_code", "code", "codigo") or f"EXT-APT-{external_id}",
        external_appointment_id=external_id,
        patient_id=resolved_patient_id,
        scheduled_start=start,
        scheduled_end=end,
        duration_minutes=duration,
        status=_parse_appointment_status(_first_present(record, "status", "estado")),
        reason=_first_present(record, "reason", "motivo", "treatment"),
        chair=_first_present(record, "chair", "sillon"),
        professional=_first_present(record, "professional", "profesional"),
        notes=_first_present(record, "notes", "observaciones"),
    )


def appointment_to_external(appointment: Appointment | dict[str, Any]) -> dict[str, Any]:
    data = appointment.model_dump() if isinstance(appointment, Appointment) else dict(appointment)
    return {
        "appointment_code": data.get("appointment_code"),
        "external_appointment_id": data.get("external_appointment_id"),
        "patient_id": str(data.get("patient_id") or ""),
        "scheduled_start": _format_datetime(data.get("scheduled_start")),
        "scheduled_end": _format_datetime(data.get("scheduled_end")),
        "duration_minutes": data.get("duration_minutes"),
        "status": str(data.get("status") or ""),
        "reason": data.get("reason"),
        "chair": data.get("chair"),
        "professional": data.get("professional"),
    }


def _first_present(record: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return None


def _parse_appointment_status(value: Any) -> AppointmentStatus:
    if value in (None, ""):
        return AppointmentStatus.SCHEDULED
    normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "programada": AppointmentStatus.SCHEDULED,
        "scheduled": AppointmentStatus.SCHEDULED,
        "completed": AppointmentStatus.COMPLETED,
        "completada": AppointmentStatus.COMPLETED,
        "cancelled": AppointmentStatus.CANCELLED,
        "canceled": AppointmentStatus.CANCELLED,
        "cancelada": AppointmentStatus.CANCELLED,
        "no_show": AppointmentStatus.NO_SHOW,
        "rescheduled": AppointmentStatus.RESCHEDULED,
        "reprogramada": AppointmentStatus.RESCHEDULED,
    }
    return aliases.get(normalized, AppointmentStatus.SCHEDULED)


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
