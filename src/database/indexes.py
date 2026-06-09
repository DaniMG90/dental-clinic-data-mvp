from pymongo import ASCENDING
from pymongo.database import Database


def create_indexes(database: Database) -> None:
    database.patients.create_index([("patient_code", ASCENDING)], unique=True)
    database.patients.create_index([("external_patient_id", ASCENDING)])
    database.patients.create_index([("last_name", ASCENDING), ("first_name", ASCENDING)])
    database.patients.create_index([("status", ASCENDING)])
    database.patients.create_index([("tags", ASCENDING)])

    database.appointments.create_index([("appointment_code", ASCENDING)], unique=True)
    database.appointments.create_index([("patient_id", ASCENDING)])
    database.appointments.create_index([("scheduled_start", ASCENDING)])
    database.appointments.create_index([("status", ASCENDING)])
    database.appointments.create_index([("scheduled_start", ASCENDING), ("status", ASCENDING)])
    database.appointments.create_index([("clinic", ASCENDING), ("scheduled_start", ASCENDING)])
    database.appointments.create_index([("chair", ASCENDING), ("scheduled_start", ASCENDING)])
    database.appointments.create_index([("professional", ASCENDING), ("scheduled_start", ASCENDING)])

    database.treatments.create_index([("treatment_code", ASCENDING)], unique=True)
    database.treatments.create_index([("patient_id", ASCENDING)])
    database.treatments.create_index([("appointment_id", ASCENDING)])
    database.treatments.create_index([("treatment_type", ASCENDING)])
    database.treatments.create_index([("status", ASCENDING)])
    database.treatments.create_index([("completed_at", ASCENDING)])

    database.treatment_catalog.create_index([("catalog_code", ASCENDING)], unique=True)
    database.treatment_catalog.create_index([("name", ASCENDING)])
    database.treatment_catalog.create_index([("category", ASCENDING)])
    database.treatment_catalog.create_index([("active", ASCENDING)])

    database.treatment_events.create_index([("treatment_id", ASCENDING)])
    database.treatment_events.create_index([("patient_id", ASCENDING)])
    database.treatment_events.create_index([("appointment_id", ASCENDING)])
    database.treatment_events.create_index([("event_type", ASCENDING)])
    database.treatment_events.create_index([("event_date", ASCENDING)])

    database.import_sources.create_index([("source_type", ASCENDING)])
    database.import_sources.create_index([("imported_at", ASCENDING)])
    database.import_sources.create_index([("status", ASCENDING)])
