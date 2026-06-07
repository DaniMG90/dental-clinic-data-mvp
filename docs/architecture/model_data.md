# MongoDB Data Model V2

## Current Situation

The repository already described a local-first MongoDB architecture for a Dental Operations Platform, but the executable data model was still mostly skeletal.

Reviewed areas:

- Collections: documented target collections existed in `README.md` and `docs/data-model.md`, but no MongoDB initialization script was present.
- Pydantic models: `src/models/patient.py`, `src/models/appointment.py`, `src/models/treatment.py` and `src/models/treatment_event.py` existed as placeholders.
- Repositories: `src/repositories/patients_repository.py`, `appointments_repository.py` and `treatments_repository.py` existed as placeholders.
- Seed scripts: `scripts/seed_demo_data.py` existed as a placeholder.
- MongoDB validations: no `$jsonSchema` validation existed before this change.
- Indexes: `scripts/create_indexes.py` and `src/database/indexes.py` existed as placeholders.
- Analytics queries: `src/analytics/metrics.py` and `src/services/analytics_service.py` were placeholders. Documentation listed expected analytics such as appointment counts, treatment status and patient activity.

## Reusable Elements

- Existing layered architecture: Streamlit UI, services, repositories and MongoDB.
- Existing runtime configuration in `src/core/config.py`.
- Existing database connection helpers in `src/database/connection.py` and `src/database/mongo_client.py`.
- Existing `src/` package layout. The task mentioned `app/models`, but the repository uses `src/models`; the implementation keeps the project convention.
- Existing plural repository module names are kept as compatibility wrappers.

## Elements To Modify

- Replace placeholder model files with Pydantic models.
- Replace placeholder repository files with CRUD repositories.
- Add MongoDB collection validation and indexes.
- Add deterministic demo seed data with real references.
- Add documentation for the current and target model.

## Elements To Remove

No destructive removals are required for the MVP. The previous placeholders are reused as real implementation files or compatibility wrappers.

## Migration Impact

The migration impact is low because no previous persisted schema was enforced in code. Existing local MongoDB volumes may need manual application of indexes and validation because Docker init scripts only run when MongoDB initializes a new database volume.

Recommended migration path for an existing local database:

```bash
MONGO_HOST=localhost conda run -n dental-clinic-mvp python scripts/create_indexes.py
MONGO_HOST=localhost conda run -n dental-clinic-mvp python scripts/seed_demo_data.py
```

`scripts/create_indexes.py` applies validators and indexes. The `MONGO_HOST=localhost` override is needed when the command is executed from the host while Docker Compose uses `mongodb` as the internal service hostname.

For a clean local reset:

```bash
docker compose down -v
docker compose up --build
```

## Model In Development

The V2 model focuses on five operational collections.

### `patients`

Responsibility: basic operational patient data.

Key fields:

- `patient_code`: internal unique business identifier.
- `external_patient_id`: future import and sync mapping.
- `import_source_id`: optional reference to `import_sources`.
- `first_name`, `last_name`, `birth_date`, `phone`, `email`.
- `status`, `tags`, `notes`.
- `created_at`, `updated_at`.

Indexes:

- unique `patient_code`.
- `external_patient_id`.
- `last_name`, `first_name`.
- `status`.
- `tags`.

### `appointments`

Responsibility: agenda and time-based clinic activity.

Key fields:

- `appointment_code`: internal unique business identifier.
- `external_appointment_id`: future calendar or external source mapping.
- `patient_id`: reference to `patients`.
- `scheduled_start`, `scheduled_end`, `duration_minutes`.
- `status`: `scheduled`, `completed`, `cancelled`, `no_show`, `rescheduled`.
- `chair`, `professional`, cancellation fields and notes.

Indexes:

- unique `appointment_code`.
- `patient_id`.
- `scheduled_start`.
- `status`.
- `scheduled_start`, `status`.
- `chair`, `scheduled_start`.
- `professional`, `scheduled_start`.

### `treatments`

Responsibility: current state of clinical treatments.

Key fields:

- `treatment_code`: internal unique business identifier.
- `external_treatment_id`: future import and sync mapping.
- `patient_id` and optional `appointment_id`.
- `treatment_type`, `description`.
- `status`: `planned`, `in_progress`, `completed`, `cancelled`, `postponed`.
- planned, started and completed dates.
- `estimated_price`, `final_price`.
- audit timestamps and notes.

Indexes:

- unique `treatment_code`.
- `patient_id`.
- `appointment_id`.
- `treatment_type`.
- `status`.
- `completed_at`.

### `treatment_events`

Responsibility: historical treatment changes and operational events.

This is not full Event Sourcing. It is a simple audit-style collection for analytics, timeline views and future synchronization support.

Key fields:

- `treatment_id`, `patient_id`, optional `appointment_id`.
- `event_type`.
- `event_date`.
- previous and new treatment status.
- description, `created_by`, `created_at`.

Indexes:

- `treatment_id`.
- `patient_id`.
- `appointment_id`.
- `event_type`.
- `event_date`.

### `import_sources`

Responsibility: traceability for imports, demo data and future external systems.

Key fields:

- `source_name`, `source_type`.
- file metadata.
- `imported_at`.
- `status`.
- inserted, rejected and total record counts.
- notes.

Indexes:

- `source_type`.
- `imported_at`.
- `status`.

## Future Compatibility

The model intentionally includes external IDs, import source references and timestamps. These fields support future import pipelines, calendar synchronization, finance, stock and advanced analytics without introducing microservices, distributed events, CQRS or heavy ODMs at the MVP stage.
