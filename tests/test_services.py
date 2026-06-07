from datetime import timedelta

import pytest
from pydantic import ValidationError

from src.models.appointment import Appointment, AppointmentStatus
from src.models.patient import Patient
from src.models.treatment import TreatmentStatus
from src.repositories.appointment_repository import AppointmentRepository
from src.repositories.patient_repository import PatientRepository
from src.repositories.treatment_event_repository import TreatmentEventRepository
from src.repositories.treatment_repository import TreatmentRepository
from src.services.analytics_service import AnalyticsService
from src.services.appointment_service import AgendaFilters, AppointmentService
from src.services.patient_service import PatientService
from src.services.treatment_service import TreatmentService
from tests.test_repositories import FakeDatabase, dt


def build_services():
    database = FakeDatabase()
    patient_repository = PatientRepository(database)
    appointment_repository = AppointmentRepository(database)
    treatment_repository = TreatmentRepository(database)
    event_repository = TreatmentEventRepository(database)
    return (
        patient_repository,
        appointment_repository,
        treatment_repository,
        event_repository,
    )


def test_appointment_service_creates_overlapping_appointments_without_blocking():
    patient_repository, appointment_repository, _, _ = build_services()
    patient = patient_repository.create(Patient(patient_code="PAT-SVC", first_name="Ana", last_name="Garcia"))
    service = AppointmentService(appointment_repository, patient_repository)

    first, first_overlaps = service.create_appointment(
        patient.id,
        dt(1, 9),
        60,
        clinic="Clinic Centro",
        chair="Gabinete 1",
        professional="Dr. Alvarez",
    )
    second, second_overlaps = service.create_appointment(
        patient.id,
        dt(1, 9) + timedelta(minutes=30),
        45,
        clinic="Clinic Centro",
        chair="Gabinete 1",
        professional="Dr. Alvarez",
    )

    assert first.status == AppointmentStatus.SCHEDULED
    assert second.id is not None
    assert first_overlaps == []
    assert second_overlaps[0].id == first.id


def test_appointment_service_filters_global_agenda_by_clinic():
    patient_repository, appointment_repository, _, _ = build_services()
    patient = patient_repository.create(Patient(patient_code="PAT-FILTER", first_name="Luis", last_name="Mora"))
    service = AppointmentService(appointment_repository, patient_repository)
    service.create_appointment(patient.id, dt(1, 9), 30, clinic="Clinic Centro")
    service.create_appointment(patient.id, dt(1, 10), 30, clinic="Clinic Norte")

    appointments = service.list_agenda(dt(1, 0), dt(2, 0), AgendaFilters(clinic="Clinic Norte"))

    assert len(appointments) == 1
    assert appointments[0].clinic == "Clinic Norte"


def test_appointment_creation_audit_accepts_complete_and_partial_records():
    patient_repository, appointment_repository, _, _ = build_services()
    patient = patient_repository.create(Patient(patient_code="PAT-AUDIT", first_name="Julia", last_name="Santos"))
    service = AppointmentService(appointment_repository, patient_repository)

    complete, complete_overlaps = service.create_appointment(
        patient.id,
        dt(3, 9),
        45,
        reason="Revision completa",
        clinic="Clinic Centro",
        chair="Gabinete 1",
        professional="Dr. Alvarez",
        notes="Paciente prefiere primera hora.",
    )
    partial, partial_overlaps = service.create_appointment(patient.id, dt(3, 11), 30)

    assert complete.reason == "Revision completa"
    assert complete.clinic == "Clinic Centro"
    assert partial.reason is None
    assert partial.clinic is None
    assert complete_overlaps == []
    assert partial_overlaps == []


def test_appointment_creation_audit_rejects_incoherent_records():
    patient_repository, appointment_repository, _, _ = build_services()
    patient = patient_repository.create(Patient(patient_code="PAT-BAD", first_name="Marta", last_name="Lopez"))
    service = AppointmentService(appointment_repository, patient_repository)

    invalid_cases = [
        {"patient_id": patient.id, "scheduled_start": dt(4, 9), "duration_minutes": 0},
        {"patient_id": patient.id, "scheduled_start": dt(4, 10), "duration_minutes": -15},
        {"patient_id": "not-an-object-id", "scheduled_start": dt(4, 11), "duration_minutes": 30},
        {"patient_id": patient.id, "scheduled_start": dt(4, 12), "duration_minutes": 24 * 60 + 1},
    ]

    for invalid_case in invalid_cases:
        with pytest.raises(ValidationError):
            service.create_appointment(**invalid_case)


def test_appointment_creation_batch_keeps_agenda_query_usable():
    patient_repository, appointment_repository, _, _ = build_services()
    patients = [
        patient_repository.create(Patient(patient_code=f"PAT-BATCH-{index}", first_name=f"Paciente{index}", last_name="Carga"))
        for index in range(4)
    ]
    service = AppointmentService(appointment_repository, patient_repository)

    created_count = 0
    overlap_warnings = 0
    for day in range(1, 6):
        for slot in range(8):
            patient = patients[(day + slot) % len(patients)]
            start = dt(day, 8) + timedelta(minutes=slot * 30)
            _, overlaps = service.create_appointment(
                patient.id,
                start,
                45,
                reason="Carga operativa",
                clinic="Clinic Centro" if slot % 2 == 0 else "Clinic Norte",
                chair="Gabinete 1" if slot % 2 == 0 else "Gabinete 2",
                professional="Dr. Alvarez",
            )
            created_count += 1
            overlap_warnings += len(overlaps)

    agenda = service.list_with_patients(dt(1, 0), dt(6, 0), AgendaFilters(clinic="Clinic Centro"))

    assert created_count == 40
    assert overlap_warnings > 0
    assert len(agenda) == 20
    assert all(row["patient"] is not None for row in agenda)


def test_patient_service_builds_profile_with_related_activity():
    patient_repository, appointment_repository, treatment_repository, event_repository = build_services()
    patient = patient_repository.create(Patient(patient_code="PAT-PROFILE", first_name="Nora", last_name="Diaz"))
    appointment_repository.create(
        Appointment(
            appointment_code="APT-PROFILE",
            patient_id=patient.id,
            scheduled_start=dt(1, 9),
            scheduled_end=dt(1, 10),
            duration_minutes=60,
        ),
    )
    treatment_service = TreatmentService(treatment_repository, event_repository, patient_repository)
    treatment_service.create_treatment(patient.id, "Orthodontics", created_by="test")
    service = PatientService(patient_repository, appointment_repository, treatment_repository, event_repository)

    profile = service.get_profile(patient.id)

    assert profile is not None
    assert profile.activity.appointments_count == 1
    assert profile.activity.treatments_count == 1
    assert len(profile.treatment_events) == 1


def test_treatment_service_records_status_event():
    patient_repository, _, treatment_repository, event_repository = build_services()
    patient = patient_repository.create(Patient(patient_code="PAT-TRT", first_name="Elena", last_name="Vega"))
    service = TreatmentService(treatment_repository, event_repository, patient_repository)
    treatment = service.create_treatment(patient.id, "Implantology", created_by="test")

    updated = service.update_status(treatment.id, TreatmentStatus.COMPLETED, created_by="test")
    events = event_repository.find_by_treatment_id(treatment.id)

    assert updated.status == TreatmentStatus.COMPLETED
    assert events[-1].new_status == TreatmentStatus.COMPLETED


def test_analytics_service_returns_weekly_summary():
    patient_repository, appointment_repository, treatment_repository, event_repository = build_services()
    patient = patient_repository.create(Patient(patient_code="PAT-AN", first_name="Mario", last_name="Ruiz"))
    appointment_repository.create(
        Appointment(
            appointment_code="APT-AN",
            patient_id=patient.id,
            scheduled_start=dt(1, 9),
            scheduled_end=dt(1, 10),
            duration_minutes=60,
            status=AppointmentStatus.CANCELLED,
        ),
    )
    service = AnalyticsService(patient_repository, appointment_repository, treatment_repository, event_repository)

    summary = service.summary(dt(1, 0), dt(2, 0))

    assert summary.active_patients == 1
    assert summary.cancellations == 1
