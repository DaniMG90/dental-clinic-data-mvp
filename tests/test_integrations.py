import json
from pathlib import Path

from bson import ObjectId

from src.integrations.export_engine import ExportEngine
from src.integrations.import_engine import ImportEngine
from src.integrations.mapping.appointment_mapper import appointment_to_external, external_to_appointment
from src.integrations.mapping.patient_mapper import external_to_patient, patient_to_external
from src.integrations.validators.import_validators import (
    validate_appointment_record,
    validate_patient_record,
)
from src.models.appointment import AppointmentStatus
from src.models.patient import PatientStatus
from src.repositories.appointment_repository import AppointmentRepository
from src.repositories.patient_repository import PatientRepository
from tests.test_repositories import FakeDatabase, dt


def test_import_engine_imports_valid_patient_json(tmp_path):
    source = tmp_path / "patients.json"
    source.write_text(
        json.dumps(
            [
                {
                    "external_patient_id": "demo-patient-json-001",
                    "first_name": "Julia",
                    "last_name": "Santos",
                    "email": "julia.santos@example.com",
                },
            ],
        ),
        encoding="utf-8",
    )
    repository = PatientRepository(FakeDatabase())

    summary = ImportEngine().import_data("patients", "json", source, repository)

    assert summary.records_read == 1
    assert summary.records_valid == 1
    assert summary.records_imported == 1
    assert repository.find_many(limit=0)[0].first_name == "Julia"


def test_import_engine_imports_valid_patient_csv(tmp_path):
    source = tmp_path / "patients.csv"
    source.write_text(
        "external_patient_id,first_name,last_name,status\n"
        "demo-patient-csv-001,Carlos,Ruiz,active\n",
        encoding="utf-8",
    )
    repository = PatientRepository(FakeDatabase())

    summary = ImportEngine().import_data("patients", "csv", source, repository)

    assert summary.records_read == 1
    assert summary.records_imported == 1
    assert repository.find_many(limit=0)[0].status == PatientStatus.ACTIVE


def test_import_engine_rejects_invalid_patient_data(tmp_path):
    source = tmp_path / "patients.json"
    source.write_text(json.dumps([{"email": "invalid"}]), encoding="utf-8")
    repository = PatientRepository(FakeDatabase())

    summary = ImportEngine().import_data("patients", "json", source, repository)

    assert summary.records_read == 1
    assert summary.records_valid == 0
    assert summary.records_imported == 0
    assert "requires a name" in summary.validation_errors[0]["errors"][0]


def test_import_engine_imports_appointment_with_external_patient_reference(tmp_path):
    database = FakeDatabase()
    patient_repository = PatientRepository(database)
    appointment_repository = AppointmentRepository(database)
    patient = patient_repository.create(
        external_to_patient(
            {
                "external_patient_id": "demo-patient-apt-001",
                "first_name": "Laura",
                "last_name": "Mora",
            },
        ),
    )
    source = tmp_path / "appointments.json"
    source.write_text(
        json.dumps(
            [
                {
                    "external_appointment_id": "demo-appointment-json-001",
                    "external_patient_id": patient.external_patient_id,
                    "scheduled_start": "2026-02-01T09:00:00+00:00",
                    "duration_minutes": 45,
                    "status": "scheduled",
                },
            ],
        ),
        encoding="utf-8",
    )

    summary = ImportEngine().import_data(
        "appointments",
        "json",
        source,
        appointment_repository,
        related_repositories={"patients": patient_repository},
    )

    assert summary.records_imported == 1
    appointment = appointment_repository.find_many(limit=0)[0]
    assert appointment.patient_id == patient.id
    assert appointment.duration_minutes == 45


def test_export_engine_exports_patients_to_json(tmp_path):
    repository = PatientRepository(FakeDatabase())
    repository.create(
        external_to_patient(
            {
                "external_patient_id": "demo-patient-export-001",
                "first_name": "Elena",
                "last_name": "Vega",
            },
        ),
    )

    summary = ExportEngine(export_root=tmp_path).export_data(
        "patients",
        "json",
        {"patients": repository},
    )

    assert summary.records_exported == 1
    exported = json.loads(Path(summary.file_path).read_text(encoding="utf-8"))
    assert exported[0]["first_name"] == "Elena"


def test_export_engine_exports_appointments_to_csv(tmp_path):
    repository = AppointmentRepository(FakeDatabase())
    repository.create(
        external_to_appointment(
            {
                "external_appointment_id": "demo-appointment-export-001",
                "scheduled_start": "2026-02-01T09:00:00+00:00",
                "duration_minutes": 30,
                "status": "completed",
            },
            patient_id=ObjectId(),
        ),
    )

    summary = ExportEngine(export_root=tmp_path).export_data(
        "appointments",
        "csv",
        {"appointments": repository},
    )

    assert summary.records_exported == 1
    assert "completed" in Path(summary.file_path).read_text(encoding="utf-8")


def test_export_engine_exports_metrics_demo(tmp_path):
    database = FakeDatabase()
    patient_repository = PatientRepository(database)
    appointment_repository = AppointmentRepository(database)
    patient = patient_repository.create(
        external_to_patient(
            {
                "external_patient_id": "demo-patient-metrics-001",
                "first_name": "Nora",
                "last_name": "Diaz",
            },
        ),
    )
    appointment_repository.create(
        external_to_appointment(
            {
                "external_appointment_id": "demo-appointment-metrics-001",
                "scheduled_start": dt(1).isoformat(),
                "duration_minutes": 60,
                "status": "scheduled",
            },
            patient_id=patient.id,
        ),
    )

    summary = ExportEngine(export_root=tmp_path).export_data(
        "metrics",
        "json",
        {"patients": patient_repository, "appointments": appointment_repository},
    )

    assert summary.records_exported >= 3
    content = Path(summary.file_path).read_text(encoding="utf-8")
    assert "patients_total" in content
    assert "appointments_by_status" in content


def test_mappers_handle_optional_and_extra_fields():
    patient = external_to_patient(
        {
            "external_id": "demo-extra-001",
            "name": "Mario",
            "last_name": "Iglesias",
            "unused": "ignored",
        },
    )
    appointment = external_to_appointment(
        {
            "external_id": "demo-extra-apt-001",
            "scheduled_start": "2026-02-01T09:00:00+00:00",
            "status": "cancelada",
            "unused": "ignored",
        },
        patient_id=ObjectId(),
    )

    assert patient.first_name == "Mario"
    assert patient_to_external(patient)["external_patient_id"] == "demo-extra-001"
    assert appointment.status == AppointmentStatus.CANCELLED
    assert appointment_to_external(appointment)["status"] == "cancelled"


def test_import_validators_return_clear_errors():
    patient_errors = validate_patient_record({"email": "not-valid"})
    appointment_errors = validate_appointment_record({"status": "scheduled"})

    assert "Patient record requires" in patient_errors[0]
    assert "Appointment record requires patient_id" in appointment_errors[0]
