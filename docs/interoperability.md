# Interoperability

This document describes the first structural version of the interoperability layer for Dental Operations Platform.

## Scope

The MVP now includes a small import/export foundation for demo operational data. The goal is not to connect to real clinical systems yet. The goal is to keep a clean boundary where future adapters can be added without mixing external formats, Streamlit screens and MongoDB access.

Current capabilities:

- import demo patients from CSV and JSON;
- import demo appointments from CSV and JSON when the referenced patient already exists;
- export patients to CSV and JSON;
- export appointments to CSV and JSON;
- export operational metrics to CSV and JSON;
- keep Excel, API and external clinic software adapters as explicit future extension points.

## Architecture

The interoperability layer lives in `src/integrations/`:

```text
src/integrations/
  import_engine.py
  export_engine.py
  adapters/
  mapping/
  validators/
```

Responsibilities:

- `adapters/`: read and write external formats such as CSV and JSON.
- `mapping/`: translate between external field names and internal Pydantic models.
- `validators/`: enforce minimum import/export rules before data reaches MongoDB.
- `ImportEngine`: orchestrates read, validate, map and repository persistence.
- `ExportEngine`: collects repository data, maps it to external shape and writes local files.

The repository layer remains the only layer that owns MongoDB collection access. Streamlit calls the engines, and the engines call repositories.

## Import Engine

The import engine returns an `ImportSummary` with:

- imported entity;
- source format;
- records read;
- records valid;
- records imported;
- records skipped;
- validation errors;
- imported ids;
- execution timestamp.

Minimum validation rules:

- patients need a name or external identifier;
- invalid email values are rejected;
- duplicated patients are skipped when an existing `external_patient_id` or `patient_code` is found;
- appointments need a patient reference, ISO datetime and status;
- duplicated appointments are skipped when an existing `external_appointment_id` or `appointment_code` is found.

Appointments can reference patients through:

- `external_patient_id`;
- `patient_code`;
- internal `patient_id` when available.

For demo imports, import patients first and appointments second.

## Export Engine

The export engine writes files under:

```text
data/exports/
  patients/
  appointments/
  metrics/
```

Generated export files are ignored by Git. Only `.gitkeep` placeholders are tracked.

Each export returns an `ExportSummary` with:

- exported entity;
- format;
- number of records;
- generated path;
- execution timestamp;
- errors, if any.

Metrics currently include simple operational counts from repositories:

- total patients;
- active patients;
- inactive or archived patients;
- total appointments;
- appointments by status.

## Demo Files

Tracked demo files live in `data/demo/`:

- `sample_patients.csv`;
- `sample_patients.json`;
- `sample_appointments.csv`;
- `sample_appointments.json`.

These examples use anonymous demo data. They are intended for local development, tests and portfolio demonstrations.

## Streamlit Workflow

The app includes a simple `Importar / Exportar datos` section:

- upload CSV or JSON demo files;
- choose `patients` or `appointments` for imports;
- choose `patients`, `appointments` or `metrics` for exports;
- choose `csv` or `json`;
- inspect the returned summary.

## Current Limits

- No real integration with clinical software.
- No bidirectional synchronization.
- No import of clinical history.
- No import of sensitive medical data.
- No Excel implementation yet.
- No external API implementation yet.
- No conflict-resolution workflow beyond obvious duplicate detection.

## Data Protection Guidance

Use only demo or anonymized data in this MVP. Before importing real operational data in a future phase:

- remove direct identifiers that are not necessary for the workflow;
- replace names, phones and emails with synthetic values when testing;
- avoid importing clinical notes or medical history;
- document the origin and purpose of each dataset;
- keep exported files out of Git and clean local export folders when they are no longer needed.
