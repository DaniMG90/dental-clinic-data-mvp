const databaseName =
  process.env.MONGO_INITDB_DATABASE ||
  process.env.MONGO_DATABASE ||
  process.env.MONGO_DEV_DB ||
  "dental_crm_dev";

const targetDb = db.getSiblingDB(databaseName);

function applyCollection(name, validator) {
  const exists = targetDb.getCollectionNames().includes(name);
  const options = {
    validator,
    validationLevel: "strict",
    validationAction: "error",
  };

  if (exists) {
    targetDb.runCommand({ collMod: name, ...options });
  } else {
    targetDb.createCollection(name, options);
  }
}

const objectIdOrNull = [{ bsonType: "objectId" }, { bsonType: "null" }];
const stringOrNull = [{ bsonType: "string" }, { bsonType: "null" }];
const dateOrNull = [{ bsonType: "date" }, { bsonType: "null" }];
const numberOrNull = [{ bsonType: ["double", "int", "long", "decimal"] }, { bsonType: "null" }];

applyCollection("patients", {
  $jsonSchema: {
    bsonType: "object",
    required: ["patient_code", "first_name", "last_name", "status", "tags", "created_at", "updated_at"],
    properties: {
      patient_code: { bsonType: "string" },
      external_patient_id: { anyOf: stringOrNull },
      import_source_id: { anyOf: objectIdOrNull },
      first_name: { bsonType: "string" },
      last_name: { bsonType: "string" },
      birth_date: { anyOf: dateOrNull },
      phone: { anyOf: stringOrNull },
      email: { anyOf: stringOrNull },
      status: { enum: ["active", "inactive", "archived"] },
      tags: { bsonType: "array", items: { bsonType: "string" } },
      created_at: { bsonType: "date" },
      updated_at: { bsonType: "date" },
      notes: { anyOf: stringOrNull },
    },
  },
});

applyCollection("appointments", {
  $jsonSchema: {
    bsonType: "object",
    required: [
      "appointment_code",
      "patient_id",
      "scheduled_start",
      "scheduled_end",
      "duration_minutes",
      "status",
      "created_at",
      "updated_at",
    ],
    properties: {
      appointment_code: { bsonType: "string" },
      external_appointment_id: { anyOf: stringOrNull },
      import_source_id: { anyOf: objectIdOrNull },
      patient_id: { bsonType: "objectId" },
      scheduled_start: { bsonType: "date" },
      scheduled_end: { bsonType: "date" },
      duration_minutes: { bsonType: "int", minimum: 1 },
      status: { enum: ["scheduled", "completed", "cancelled", "no_show", "rescheduled"] },
      reason: { anyOf: stringOrNull },
      chair: { anyOf: stringOrNull },
      professional: { anyOf: stringOrNull },
      cancelled_at: { anyOf: dateOrNull },
      cancellation_reason: { anyOf: stringOrNull },
      created_at: { bsonType: "date" },
      updated_at: { bsonType: "date" },
      notes: { anyOf: stringOrNull },
    },
  },
});

applyCollection("treatments", {
  $jsonSchema: {
    bsonType: "object",
    required: ["treatment_code", "patient_id", "treatment_type", "status", "created_at", "updated_at"],
    properties: {
      treatment_code: { bsonType: "string" },
      external_treatment_id: { anyOf: stringOrNull },
      import_source_id: { anyOf: objectIdOrNull },
      patient_id: { bsonType: "objectId" },
      appointment_id: { anyOf: objectIdOrNull },
      treatment_type: { bsonType: "string" },
      description: { anyOf: stringOrNull },
      status: { enum: ["planned", "in_progress", "completed", "cancelled", "postponed"] },
      planned_date: { anyOf: dateOrNull },
      started_at: { anyOf: dateOrNull },
      completed_at: { anyOf: dateOrNull },
      estimated_price: { anyOf: numberOrNull },
      final_price: { anyOf: numberOrNull },
      created_at: { bsonType: "date" },
      updated_at: { bsonType: "date" },
      notes: { anyOf: stringOrNull },
    },
  },
});

applyCollection("treatment_events", {
  $jsonSchema: {
    bsonType: "object",
    required: ["treatment_id", "patient_id", "event_type", "event_date", "created_at"],
    properties: {
      treatment_id: { bsonType: "objectId" },
      patient_id: { bsonType: "objectId" },
      appointment_id: { anyOf: objectIdOrNull },
      event_type: {
        enum: [
          "created",
          "status_changed",
          "price_updated",
          "appointment_linked",
          "appointment_unlinked",
          "note_added",
          "completed",
          "cancelled",
          "postponed",
        ],
      },
      event_date: { bsonType: "date" },
      previous_status: { enum: ["planned", "in_progress", "completed", "cancelled", "postponed", null] },
      new_status: { enum: ["planned", "in_progress", "completed", "cancelled", "postponed", null] },
      description: { anyOf: stringOrNull },
      created_by: { anyOf: stringOrNull },
      created_at: { bsonType: "date" },
    },
  },
});

applyCollection("import_sources", {
  $jsonSchema: {
    bsonType: "object",
    required: [
      "source_name",
      "source_type",
      "imported_at",
      "status",
      "records_total",
      "records_inserted",
      "records_rejected",
    ],
    properties: {
      source_name: { bsonType: "string" },
      source_type: { enum: ["manual", "demo", "csv", "excel", "json", "api", "external_system"] },
      file_name: { anyOf: stringOrNull },
      file_hash: { anyOf: stringOrNull },
      imported_at: { bsonType: "date" },
      status: { enum: ["pending", "completed", "failed", "partial"] },
      records_total: { bsonType: "int", minimum: 0 },
      records_inserted: { bsonType: "int", minimum: 0 },
      records_rejected: { bsonType: "int", minimum: 0 },
      notes: { anyOf: stringOrNull },
    },
  },
});

targetDb.patients.createIndex({ patient_code: 1 }, { unique: true });
targetDb.patients.createIndex({ external_patient_id: 1 });
targetDb.patients.createIndex({ last_name: 1, first_name: 1 });
targetDb.patients.createIndex({ status: 1 });
targetDb.patients.createIndex({ tags: 1 });

targetDb.appointments.createIndex({ appointment_code: 1 }, { unique: true });
targetDb.appointments.createIndex({ patient_id: 1 });
targetDb.appointments.createIndex({ scheduled_start: 1 });
targetDb.appointments.createIndex({ status: 1 });
targetDb.appointments.createIndex({ scheduled_start: 1, status: 1 });
targetDb.appointments.createIndex({ chair: 1, scheduled_start: 1 });
targetDb.appointments.createIndex({ professional: 1, scheduled_start: 1 });

targetDb.treatments.createIndex({ treatment_code: 1 }, { unique: true });
targetDb.treatments.createIndex({ patient_id: 1 });
targetDb.treatments.createIndex({ appointment_id: 1 });
targetDb.treatments.createIndex({ treatment_type: 1 });
targetDb.treatments.createIndex({ status: 1 });
targetDb.treatments.createIndex({ completed_at: 1 });

targetDb.treatment_events.createIndex({ treatment_id: 1 });
targetDb.treatment_events.createIndex({ patient_id: 1 });
targetDb.treatment_events.createIndex({ appointment_id: 1 });
targetDb.treatment_events.createIndex({ event_type: 1 });
targetDb.treatment_events.createIndex({ event_date: 1 });

targetDb.import_sources.createIndex({ source_type: 1 });
targetDb.import_sources.createIndex({ imported_at: 1 });
targetDb.import_sources.createIndex({ status: 1 });
