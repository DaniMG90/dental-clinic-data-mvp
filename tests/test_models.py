from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from pydantic import ValidationError

from src.models import (
    Appointment,
    AppointmentStatus,
    ImportSource,
    ImportSourceType,
    Patient,
    Treatment,
    TreatmentEvent,
    TreatmentEventType,
    TreatmentStatus,
)


def test_patient_accepts_mongodb_object_id_string():
    patient_id = ObjectId()

    patient = Patient(
        _id=str(patient_id),
        patient_code="PAT-TEST",
        first_name="Ana",
        last_name="Garcia",
        birth_date=datetime(1990, 1, 1, tzinfo=timezone.utc),
    )

    assert patient.id == patient_id
    assert patient.to_mongo()["_id"] == patient_id


def test_appointment_rejects_invalid_schedule():
    now = datetime.now(timezone.utc)

    with pytest.raises(ValidationError):
        Appointment(
            appointment_code="APT-TEST",
            patient_id=ObjectId(),
            scheduled_start=now,
            scheduled_end=now - timedelta(minutes=15),
            duration_minutes=30,
        )


def test_core_models_validate_target_statuses_and_references():
    patient_id = ObjectId()
    appointment_id = ObjectId()
    treatment_id = ObjectId()

    appointment = Appointment(
        appointment_code="APT-OK",
        patient_id=patient_id,
        scheduled_start=datetime.now(timezone.utc),
        scheduled_end=datetime.now(timezone.utc) + timedelta(minutes=45),
        duration_minutes=45,
        status=AppointmentStatus.SCHEDULED,
    )
    treatment = Treatment(
        treatment_code="TRT-OK",
        patient_id=patient_id,
        appointment_id=appointment_id,
        treatment_type="Implantology",
        status=TreatmentStatus.PLANNED,
        estimated_price=750.0,
    )
    event = TreatmentEvent(
        treatment_id=treatment_id,
        patient_id=patient_id,
        appointment_id=appointment_id,
        event_type=TreatmentEventType.CREATED,
        event_date=datetime.now(timezone.utc),
        new_status=TreatmentStatus.PLANNED,
    )
    import_source = ImportSource(
        source_name="Manual test",
        source_type=ImportSourceType.MANUAL,
    )

    assert appointment.patient_id == patient_id
    assert treatment.appointment_id == appointment_id
    assert event.treatment_id == treatment_id
    assert import_source.records_rejected == 0
