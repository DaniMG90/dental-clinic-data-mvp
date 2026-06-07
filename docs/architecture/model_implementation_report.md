# MongoDB Model V2 Implementation Report

## Changes Implemented

- Added Pydantic models for `Patient`, `Appointment`, `Treatment`, `TreatmentEvent` and `ImportSource`.
- Added MongoDB `ObjectId` compatibility through a lightweight custom Pydantic type.
- Added CRUD repositories with a shared PyMongo base repository.
- Preserved existing plural repository modules as compatibility wrappers.
- Added MongoDB initialization script with `$jsonSchema` validators using `validationLevel: strict` and `validationAction: error`.
- Added Python schema application for existing local databases, so validators can be applied without deleting MongoDB volumes.
- Added indexes for all V2 collections.
- Mounted `mongo/init` into the MongoDB Docker container for clean local database initialization.
- Added deterministic demo seed data for all V2 collections with real references.
- Added unit tests for model validation and repository CRUD behavior.

## Decisions Adopted

- Keep the existing `src/models` and `src/repositories` layout instead of creating a parallel `app/models` tree.
- Use PyMongo directly and avoid ODMs to keep the MVP simple.
- Use `treatment_events` as an operational event history, not a full Event Sourcing implementation.
- Use internal business codes such as `patient_code`, `appointment_code` and `treatment_code` for readable unique identifiers.
- Keep prices as `float` for simple MongoDB storage in the MVP. A later finance module can introduce stricter money handling if needed.
- Keep email validation lightweight to avoid adding `email-validator` as an extra dependency.

## Incompatibilities Detected

- Existing MongoDB volumes do not automatically run new Docker init scripts. Existing local databases should run `scripts/create_indexes.py`, which now applies validators and indexes without dropping data.
- Host-executed scripts may need `MONGO_HOST=localhost` because `.env` can use `MONGO_HOST=mongodb` for containers.
- The original documentation referenced `activity_logs` and `external_imports`; V2 replaces those concerns with `treatment_events` and `import_sources`.
- The task mentioned `app/models`, while the repository structure uses `src/models`. The implementation follows the repository structure.

## Pending Technical Debt

- Add analytics service functions over the new collections.
- Add Streamlit pages for CRUD workflows and operational dashboards.
- Add migration tooling for non-demo local datasets.
- Add validation scripts that compare live MongoDB collection options and expected indexes.
- Add finance and stock models only when those modules enter scope.

## Recommendations For Future Phases

- Build dashboards around appointment status, treatment status, completed treatments and patient activity first.
- Introduce import adapters incrementally using `import_sources` for traceability.
- Add calendar integration using `external_appointment_id` and `import_source_id`.
- Keep financial records in a separate collection when the finance module starts; do not overload `treatments`.
- Add stock collections separately, linked to treatment types only when operational workflows require it.
