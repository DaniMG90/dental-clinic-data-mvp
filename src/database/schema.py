from typing import Any

from pymongo.database import Database


OBJECT_ID_OR_NULL = [{"bsonType": "objectId"}, {"bsonType": "null"}]
STRING_OR_NULL = [{"bsonType": "string"}, {"bsonType": "null"}]
DATE_OR_NULL = [{"bsonType": "date"}, {"bsonType": "null"}]
NUMBER_OR_NULL = [{"bsonType": ["double", "int", "long", "decimal"]}, {"bsonType": "null"}]


COLLECTION_VALIDATORS: dict[str, dict[str, Any]] = {
    "patients": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "patient_code",
                "first_name",
                "last_name",
                "status",
                "tags",
                "created_at",
                "updated_at",
            ],
            "properties": {
                "patient_code": {"bsonType": "string"},
                "external_patient_id": {"anyOf": STRING_OR_NULL},
                "import_source_id": {"anyOf": OBJECT_ID_OR_NULL},
                "first_name": {"bsonType": "string"},
                "last_name": {"bsonType": "string"},
                "birth_date": {"anyOf": DATE_OR_NULL},
                "phone": {"anyOf": STRING_OR_NULL},
                "email": {"anyOf": STRING_OR_NULL},
                "status": {"enum": ["active", "inactive", "archived"]},
                "tags": {"bsonType": "array", "items": {"bsonType": "string"}},
                "created_at": {"bsonType": "date"},
                "updated_at": {"bsonType": "date"},
                "notes": {"anyOf": STRING_OR_NULL},
            },
        }
    },
    "appointments": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "appointment_code",
                "patient_id",
                "scheduled_start",
                "scheduled_end",
                "duration_minutes",
                "status",
                "created_at",
                "updated_at",
            ],
            "properties": {
                "appointment_code": {"bsonType": "string"},
                "external_appointment_id": {"anyOf": STRING_OR_NULL},
                "import_source_id": {"anyOf": OBJECT_ID_OR_NULL},
                "patient_id": {"bsonType": "objectId"},
                "scheduled_start": {"bsonType": "date"},
                "scheduled_end": {"bsonType": "date"},
                "duration_minutes": {"bsonType": "int", "minimum": 1},
                "status": {"enum": ["scheduled", "completed", "cancelled", "no_show", "rescheduled"]},
                "reason": {"anyOf": STRING_OR_NULL},
                "clinic": {"anyOf": STRING_OR_NULL},
                "chair": {"anyOf": STRING_OR_NULL},
                "professional": {"anyOf": STRING_OR_NULL},
                "cancelled_at": {"anyOf": DATE_OR_NULL},
                "cancellation_reason": {"anyOf": STRING_OR_NULL},
                "created_at": {"bsonType": "date"},
                "updated_at": {"bsonType": "date"},
                "notes": {"anyOf": STRING_OR_NULL},
            },
        }
    },
    "treatments": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["treatment_code", "patient_id", "treatment_type", "status", "created_at", "updated_at"],
            "properties": {
                "treatment_code": {"bsonType": "string"},
                "external_treatment_id": {"anyOf": STRING_OR_NULL},
                "import_source_id": {"anyOf": OBJECT_ID_OR_NULL},
                "patient_id": {"bsonType": "objectId"},
                "appointment_id": {"anyOf": OBJECT_ID_OR_NULL},
                "treatment_type": {"bsonType": "string"},
                "description": {"anyOf": STRING_OR_NULL},
                "status": {"enum": ["planned", "in_progress", "completed", "cancelled", "postponed"]},
                "planned_date": {"anyOf": DATE_OR_NULL},
                "started_at": {"anyOf": DATE_OR_NULL},
                "completed_at": {"anyOf": DATE_OR_NULL},
                "estimated_price": {"anyOf": NUMBER_OR_NULL},
                "final_price": {"anyOf": NUMBER_OR_NULL},
                "created_at": {"bsonType": "date"},
                "updated_at": {"bsonType": "date"},
                "notes": {"anyOf": STRING_OR_NULL},
            },
        }
    },
    "treatment_catalog": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["catalog_code", "name", "active", "created_at", "updated_at"],
            "properties": {
                "catalog_code": {"bsonType": "string"},
                "name": {"bsonType": "string"},
                "category": {"anyOf": STRING_OR_NULL},
                "default_duration_minutes": {"anyOf": [{"bsonType": "int", "minimum": 1}, {"bsonType": "null"}]},
                "base_price": {"anyOf": NUMBER_OR_NULL},
                "active": {"bsonType": "bool"},
                "notes": {"anyOf": STRING_OR_NULL},
                "created_at": {"bsonType": "date"},
                "updated_at": {"bsonType": "date"},
            },
        }
    },
    "treatment_events": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["treatment_id", "patient_id", "event_type", "event_date", "created_at"],
            "properties": {
                "treatment_id": {"bsonType": "objectId"},
                "patient_id": {"bsonType": "objectId"},
                "appointment_id": {"anyOf": OBJECT_ID_OR_NULL},
                "event_type": {
                    "enum": [
                        "created",
                        "status_changed",
                        "price_updated",
                        "appointment_linked",
                        "appointment_unlinked",
                        "note_added",
                        "completed",
                        "cancelled",
                        "postponed",
                    ]
                },
                "event_date": {"bsonType": "date"},
                "previous_status": {"enum": ["planned", "in_progress", "completed", "cancelled", "postponed", None]},
                "new_status": {"enum": ["planned", "in_progress", "completed", "cancelled", "postponed", None]},
                "description": {"anyOf": STRING_OR_NULL},
                "created_by": {"anyOf": STRING_OR_NULL},
                "created_at": {"bsonType": "date"},
            },
        }
    },
    "import_sources": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "source_name",
                "source_type",
                "imported_at",
                "status",
                "records_total",
                "records_inserted",
                "records_rejected",
            ],
            "properties": {
                "source_name": {"bsonType": "string"},
                "source_type": {"enum": ["manual", "demo", "csv", "excel", "json", "api", "external_system"]},
                "file_name": {"anyOf": STRING_OR_NULL},
                "file_hash": {"anyOf": STRING_OR_NULL},
                "imported_at": {"bsonType": "date"},
                "status": {"enum": ["pending", "completed", "failed", "partial"]},
                "records_total": {"bsonType": "int", "minimum": 0},
                "records_inserted": {"bsonType": "int", "minimum": 0},
                "records_rejected": {"bsonType": "int", "minimum": 0},
                "notes": {"anyOf": STRING_OR_NULL},
            },
        }
    },
    "operational_settings": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "settings_key",
                "schema_version",
                "business_name",
                "internal_identifier",
                "data_mode",
                "timezone",
                "clinics",
                "chairs",
                "professionals",
                "weekly_schedule",
                "agenda",
                "analytics",
                "treatments",
                "security",
                "created_at",
                "updated_at",
            ],
            "properties": {
                "settings_key": {"bsonType": "string"},
                "schema_version": {"bsonType": "int", "minimum": 1},
                "business_name": {"bsonType": "string"},
                "internal_identifier": {"bsonType": "string"},
                "data_mode": {"enum": ["demo", "real"]},
                "timezone": {"bsonType": "string"},
                "clinics": {"bsonType": "array"},
                "chairs": {"bsonType": "array"},
                "professionals": {"bsonType": "array"},
                "weekly_schedule": {"bsonType": "object"},
                "agenda": {"bsonType": "object"},
                "analytics": {"bsonType": "object"},
                "treatments": {"bsonType": "object"},
                "security": {"bsonType": "object"},
                "created_at": {"bsonType": "date"},
                "updated_at": {"bsonType": "date"},
            },
        }
    },
}


def apply_collection_validators(database: Database) -> None:
    existing_collections = set(database.list_collection_names())

    for collection_name, validator in COLLECTION_VALIDATORS.items():
        options = {
            "validator": validator,
            "validationLevel": "strict",
            "validationAction": "error",
        }
        if collection_name in existing_collections:
            database.command({"collMod": collection_name, **options})
        else:
            database.create_collection(collection_name, **options)
