import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_database
from src.database.indexes import create_indexes
from src.models import (
    Appointment,
    AppointmentStatus,
    ImportSource,
    ImportSourceStatus,
    ImportSourceType,
    Patient,
    PatientStatus,
    Treatment,
    TreatmentCatalogItem,
    TreatmentEvent,
    TreatmentEventType,
    TreatmentStatus,
)


def upsert_by_code(collection, code_field: str, document: dict):
    result = collection.update_one(
        {code_field: document[code_field]},
        {"$set": document},
        upsert=True,
    )
    if result.upserted_id:
        return result.upserted_id
    return collection.find_one({code_field: document[code_field]}, {"_id": 1})["_id"]


def main() -> None:
    database = get_database()
    create_indexes(database)

    now = datetime.now(timezone.utc)

    import_source = ImportSource(
        source_name="Demo seed data",
        source_type=ImportSourceType.DEMO,
        file_name="scripts/seed_demo_data.py",
        file_hash="demo-seed-v2",
        imported_at=now,
        status=ImportSourceStatus.COMPLETED,
        records_total=17,
        records_inserted=17,
        records_rejected=0,
        notes="Deterministic demo dataset for the MongoDB V2 model.",
    ).to_mongo()
    import_source_id = upsert_by_code(database.import_sources, "file_hash", import_source)

    patient_inputs = [
        Patient(
            patient_code="PAT-0001",
            external_patient_id="demo-patient-001",
            import_source_id=import_source_id,
            first_name="Ana",
            last_name="Garcia",
            birth_date=datetime(1988, 5, 14, tzinfo=timezone.utc),
            phone="+34 600 111 222",
            email="ana.garcia@example.com",
            status=PatientStatus.ACTIVE,
            tags=["demo", "orthodontics"],
            created_at=now - timedelta(days=60),
            updated_at=now,
            notes="Demo patient with active orthodontic treatment.",
        ),
        Patient(
            patient_code="PAT-0002",
            external_patient_id="demo-patient-002",
            import_source_id=import_source_id,
            first_name="Luis",
            last_name="Martinez",
            birth_date=datetime(1979, 11, 2, tzinfo=timezone.utc),
            phone="+34 600 333 444",
            email="luis.martinez@example.com",
            status=PatientStatus.ACTIVE,
            tags=["demo", "implantology"],
            created_at=now - timedelta(days=45),
            updated_at=now,
        ),
        Patient(
            patient_code="PAT-0003",
            external_patient_id="demo-patient-003",
            import_source_id=import_source_id,
            first_name="Marta",
            last_name="Lopez",
            birth_date=datetime(1994, 2, 20, tzinfo=timezone.utc),
            phone="+34 600 555 666",
            email="marta.lopez@example.com",
            status=PatientStatus.INACTIVE,
            tags=["demo"],
            created_at=now - timedelta(days=90),
            updated_at=now - timedelta(days=15),
            notes="Inactive demo patient retained for analytics checks.",
        ),
    ]

    patient_ids = {
        patient.patient_code: upsert_by_code(database.patients, "patient_code", patient.to_mongo())
        for patient in patient_inputs
    }

    appointments = [
        Appointment(
            appointment_code="APT-0001",
            external_appointment_id="demo-appointment-001",
            import_source_id=import_source_id,
            patient_id=patient_ids["PAT-0001"],
            scheduled_start=now + timedelta(days=2, hours=9),
            scheduled_end=now + timedelta(days=2, hours=10),
            duration_minutes=60,
            status=AppointmentStatus.SCHEDULED,
            reason="Orthodontic review",
            chair="Chair 1",
            professional="Dr. Alvarez",
            created_at=now - timedelta(days=10),
            updated_at=now,
        ),
        Appointment(
            appointment_code="APT-0002",
            external_appointment_id="demo-appointment-002",
            import_source_id=import_source_id,
            patient_id=patient_ids["PAT-0002"],
            scheduled_start=now - timedelta(days=5, hours=10),
            scheduled_end=now - timedelta(days=5, hours=9, minutes=15),
            duration_minutes=45,
            status=AppointmentStatus.COMPLETED,
            reason="Implant planning",
            chair="Chair 2",
            professional="Dr. Rivera",
            created_at=now - timedelta(days=20),
            updated_at=now - timedelta(days=5),
        ),
        Appointment(
            appointment_code="APT-0003",
            external_appointment_id="demo-appointment-003",
            import_source_id=import_source_id,
            patient_id=patient_ids["PAT-0003"],
            scheduled_start=now - timedelta(days=12, hours=11),
            scheduled_end=now - timedelta(days=12, hours=10, minutes=30),
            duration_minutes=30,
            status=AppointmentStatus.CANCELLED,
            reason="Dental cleaning",
            chair="Chair 1",
            professional="Hygienist Team",
            cancelled_at=now - timedelta(days=13),
            cancellation_reason="Patient requested cancellation",
            created_at=now - timedelta(days=25),
            updated_at=now - timedelta(days=13),
        ),
    ]

    appointment_ids = {
        appointment.appointment_code: upsert_by_code(
            database.appointments,
            "appointment_code",
            appointment.to_mongo(),
        )
        for appointment in appointments
    }

    catalog_items = [
        TreatmentCatalogItem(
            catalog_code="TCAT-0001",
            name="Orthodontics",
            category="Orthodontics",
            default_duration_minutes=60,
            base_price=1200.0,
            active=True,
            notes="Demo catalog item for orthodontic treatment plans.",
            created_at=now - timedelta(days=70),
            updated_at=now,
        ),
        TreatmentCatalogItem(
            catalog_code="TCAT-0002",
            name="Implantology",
            category="Surgery",
            default_duration_minutes=90,
            base_price=950.0,
            active=True,
            notes="Demo catalog item for implant planning and procedures.",
            created_at=now - timedelta(days=70),
            updated_at=now,
        ),
        TreatmentCatalogItem(
            catalog_code="TCAT-0003",
            name="Preventive cleaning",
            category="Preventive",
            default_duration_minutes=30,
            base_price=65.0,
            active=True,
            notes="Demo catalog item for preventive hygiene visits.",
            created_at=now - timedelta(days=70),
            updated_at=now,
        ),
        TreatmentCatalogItem(
            catalog_code="TCAT-0004",
            name="Whitening",
            category="Aesthetic",
            default_duration_minutes=45,
            base_price=180.0,
            active=False,
            notes="Inactive demo item used to validate catalog activation.",
            created_at=now - timedelta(days=70),
            updated_at=now,
        ),
    ]
    catalog_ids = {
        item.catalog_code: upsert_by_code(
            database.treatment_catalog,
            "catalog_code",
            item.to_mongo(),
        )
        for item in catalog_items
    }

    treatments = [
        Treatment(
            treatment_code="TRT-0001",
            external_treatment_id="demo-treatment-001",
            import_source_id=import_source_id,
            patient_id=patient_ids["PAT-0001"],
            appointment_id=appointment_ids["APT-0001"],
            treatment_type="Orthodontics",
            description="Monthly orthodontic adjustment plan.",
            status=TreatmentStatus.IN_PROGRESS,
            planned_date=now + timedelta(days=2),
            started_at=now - timedelta(days=30),
            estimated_price=1200.0,
            final_price=None,
            created_at=now - timedelta(days=35),
            updated_at=now,
            notes="Next review already scheduled.",
        ),
        Treatment(
            treatment_code="TRT-0002",
            external_treatment_id="demo-treatment-002",
            import_source_id=import_source_id,
            patient_id=patient_ids["PAT-0002"],
            appointment_id=appointment_ids["APT-0002"],
            treatment_type="Implantology",
            description="Single implant planning and initial procedure.",
            status=TreatmentStatus.COMPLETED,
            planned_date=now - timedelta(days=5),
            started_at=now - timedelta(days=5),
            completed_at=now - timedelta(days=5),
            estimated_price=950.0,
            final_price=980.0,
            created_at=now - timedelta(days=20),
            updated_at=now - timedelta(days=5),
        ),
        Treatment(
            treatment_code="TRT-0003",
            external_treatment_id="demo-treatment-003",
            import_source_id=import_source_id,
            patient_id=patient_ids["PAT-0003"],
            appointment_id=appointment_ids["APT-0003"],
            treatment_type="Preventive cleaning",
            description="Cancelled cleaning appointment.",
            status=TreatmentStatus.CANCELLED,
            planned_date=now - timedelta(days=12),
            estimated_price=65.0,
            created_at=now - timedelta(days=25),
            updated_at=now - timedelta(days=13),
        ),
    ]

    treatment_ids = {
        treatment.treatment_code: upsert_by_code(
            database.treatments,
            "treatment_code",
            treatment.to_mongo(),
        )
        for treatment in treatments
    }

    database.treatment_events.delete_many({"created_by": "demo_seed_v2"})
    events = [
        TreatmentEvent(
            treatment_id=treatment_ids["TRT-0001"],
            patient_id=patient_ids["PAT-0001"],
            appointment_id=appointment_ids["APT-0001"],
            event_type=TreatmentEventType.CREATED,
            event_date=now - timedelta(days=35),
            new_status=TreatmentStatus.PLANNED,
            description="Treatment plan created.",
            created_by="demo_seed_v2",
            created_at=now,
        ),
        TreatmentEvent(
            treatment_id=treatment_ids["TRT-0001"],
            patient_id=patient_ids["PAT-0001"],
            appointment_id=appointment_ids["APT-0001"],
            event_type=TreatmentEventType.STATUS_CHANGED,
            event_date=now - timedelta(days=30),
            previous_status=TreatmentStatus.PLANNED,
            new_status=TreatmentStatus.IN_PROGRESS,
            description="Treatment started.",
            created_by="demo_seed_v2",
            created_at=now,
        ),
        TreatmentEvent(
            treatment_id=treatment_ids["TRT-0002"],
            patient_id=patient_ids["PAT-0002"],
            appointment_id=appointment_ids["APT-0002"],
            event_type=TreatmentEventType.COMPLETED,
            event_date=now - timedelta(days=5),
            previous_status=TreatmentStatus.IN_PROGRESS,
            new_status=TreatmentStatus.COMPLETED,
            description="Treatment completed with final price update.",
            created_by="demo_seed_v2",
            created_at=now,
        ),
        TreatmentEvent(
            treatment_id=treatment_ids["TRT-0003"],
            patient_id=patient_ids["PAT-0003"],
            appointment_id=appointment_ids["APT-0003"],
            event_type=TreatmentEventType.CANCELLED,
            event_date=now - timedelta(days=13),
            previous_status=TreatmentStatus.PLANNED,
            new_status=TreatmentStatus.CANCELLED,
            description="Appointment and treatment cancelled by patient request.",
            created_by="demo_seed_v2",
            created_at=now,
        ),
    ]
    database.treatment_events.insert_many([event.to_mongo() for event in events])

    print(
        "Demo data loaded: "
        f"{len(patient_ids)} patients, {len(appointment_ids)} appointments, "
        f"{len(catalog_ids)} catalog treatments, {len(treatment_ids)} treatments, "
        f"{len(events)} treatment events, 1 import source."
    )


if __name__ == "__main__":
    main()
