# Data Model

The data model is designed for a local MongoDB MVP. It favors clear operational collections and incremental schema hardening over premature complexity.

## Current Core Collections

### `patients`

Represents people treated by the clinic.

Current fields:

- `_id`
- `patient_code`
- `external_patient_id`
- `import_source_id`
- `first_name`
- `last_name`
- `birth_date`
- `phone`
- `email`
- `status`
- `tags`
- `created_at`
- `updated_at`
- `notes`

Common queries:

- search by name or phone;
- list active patients;
- retrieve patient detail with related appointments, treatments and treatment events.

### `appointments`

Represents scheduled clinical visits.

Current fields:

- `_id`
- `appointment_code`
- `external_appointment_id`
- `import_source_id`
- `patient_id`
- `scheduled_start`
- `scheduled_end`
- `duration_minutes`
- `status`
- `reason`
- `clinic`
- `chair`
- `professional`
- `cancelled_at`
- `cancellation_reason`
- `created_at`
- `updated_at`
- `notes`

Common queries:

- appointments by date range;
- appointments by patient;
- appointment counts by status;
- global agenda filters by clinic, chair and professional;
- overlap detection for visual warnings.

### `treatments`

Represents treatment plans or performed treatment records associated with a patient. This is not the catalog.

Current fields:

- `_id`
- `treatment_code`
- `external_treatment_id`
- `import_source_id`
- `patient_id`
- `appointment_id`
- `treatment_type`
- `description`
- `status`
- `planned_date`
- `started_at`
- `completed_at`
- `estimated_price`
- `final_price`
- `created_at`
- `updated_at`
- `notes`

Common queries:

- treatments by patient;
- active treatments;
- completed treatments by period;
- treatment activity by type.

### `treatment_catalog`

Represents editable operational definitions of available treatments.

Current fields:

- `_id`
- `catalog_code`
- `name`
- `category`
- `default_duration_minutes`
- `base_price`
- `active`
- `notes`
- `created_at`
- `updated_at`

Common queries:

- search catalog by name, category, code or notes;
- list active catalog items for treatment registration;
- activate or deactivate catalog items.

### `treatment_events`

Represents treatment activity events.

Current fields:

- `_id`
- `treatment_id`
- `patient_id`
- `appointment_id`
- `event_type`
- `event_date`
- `previous_status`
- `new_status`
- `description`
- `created_by`
- `created_at`

Common queries:

- activity by patient;
- activity by treatment;
- treatment evolution over time;
- event frequency by period.

### `import_sources`

Tracks imported files or seed batches, including source, status, imported counts and errors.

### `operational_settings`

Stores the main editable operational configuration document for the local MVP.

The primary document uses:

- `settings_key`: `default`;
- `schema_version`;
- clinic business identity;
- data mode and timezone;
- active/inactive clinics;
- active/inactive chairs linked to clinics;
- active/inactive professionals;
- weekly schedules by clinic;
- agenda defaults and enabled statuses;
- analytics defaults;
- treatment categories;
- basic security/data-operation flags.

The service initializes this document if the collection is empty and merges missing fields with current defaults when the schema evolves.

## Future Collections

### `inventory`

Tracks materials, stock levels and operational supply needs.

### `finance`

Tracks basic financial records such as treatment charges, payments or outstanding balances. This should be introduced carefully and only after the core operational model is stable.

## Indexing Guidelines

Initial indexes are aligned with real query patterns:

- `patients`: `patient_code`, external id, name fields, status and tags.
- `appointments`: `appointment_code`, `patient_id`, `scheduled_start`, `status`, `clinic`, `chair`, `professional`.
- `treatments`: `treatment_code`, `patient_id`, `appointment_id`, `treatment_type`, `status`, `completed_at`.
- `treatment_catalog`: `catalog_code`, `name`, `category`, `active`.
- `treatment_events`: `patient_id`, `treatment_id`, `appointment_id`, `event_type`, `event_date`.
- `import_sources`: source type, import date and status.
- `operational_settings`: `settings_key`, `data_mode`.

## Validation Guidelines

MongoDB validation is applied through collection validators and Pydantic models. The current version validates required fields, date fields, status values and relationship identifiers while leaving room for future operational fields.
