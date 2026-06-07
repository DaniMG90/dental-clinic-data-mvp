# Data Model

The data model is designed for a local MongoDB MVP. It favors clear operational collections and incremental schema hardening over premature complexity.

## Current Core Collections

### `patients`

Represents people treated by the clinic.

Suggested fields:

- `_id`
- `first_name`
- `last_name`
- `date_of_birth`
- `phone`
- `email`
- `status`
- `created_at`
- `updated_at`

Common queries:

- search by name;
- list active patients;
- retrieve patient detail with related appointments and treatments.

### `appointments`

Represents scheduled clinical visits.

Suggested fields:

- `_id`
- `patient_id`
- `scheduled_at`
- `duration_minutes`
- `status`
- `reason`
- `notes`
- `created_at`
- `updated_at`

Common queries:

- appointments by date range;
- appointments by patient;
- appointment counts by status.

### `treatments`

Represents clinical treatment plans or treatment records associated with a patient.

Suggested fields:

- `_id`
- `patient_id`
- `appointment_id`
- `treatment_type`
- `status`
- `estimated_cost`
- `started_at`
- `completed_at`
- `notes`
- `created_at`
- `updated_at`

Common queries:

- treatments by patient;
- active treatments;
- completed treatments by period;
- treatment activity by type.

### `activity_logs`

Represents important operational events.

Suggested fields:

- `_id`
- `entity_type`
- `entity_id`
- `action`
- `metadata`
- `created_at`

Common queries:

- recent activity;
- activity by entity;
- operational audit trail.

## Future Collections

### `inventory`

Tracks materials, stock levels and operational supply needs.

### `finance`

Tracks basic financial records such as treatment charges, payments or outstanding balances. This should be introduced carefully and only after the core operational model is stable.

### `external_imports`

Tracks imported files or external sync batches, including source, status, imported counts and errors.

## Indexing Guidelines

Initial indexes should be aligned with real query patterns:

- `patients`: name fields, status.
- `appointments`: `patient_id`, `scheduled_at`, `status`.
- `treatments`: `patient_id`, `appointment_id`, `status`.
- `activity_logs`: `entity_type`, `entity_id`, `created_at`.

## Validation Guidelines

MongoDB validation can be introduced after the Python models and repositories are stable. The first version should validate required fields, date formats, status values and relationship identifiers.
