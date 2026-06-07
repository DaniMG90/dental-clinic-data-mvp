# Data Flow

This document describes the target data flow for the local MVP and the future analytics layer.

## High-Level Flow

```text
Manual entry or external source
-> Streamlit UI / Import Engine
-> mapper and validator
-> Application service or repository use case
-> Repository
-> MongoDB collection
-> Aggregation or query
-> Streamlit dashboard / Export Engine
-> local CSV or JSON export
```

## Data Origins

Initial data sources are expected to be:

- manual entry through Streamlit forms;
- demo seed data for local development;
- demo imports from CSV and JSON files;
- future imports from Excel files, external APIs or external clinic systems.

External integrations are intentionally future-facing. The MVP should first stabilize local data structures and operational workflows.

## Transformation

Application services and the interoperability layer should be responsible for transforming raw UI input or imported rows into normalized application objects.

Transformation responsibilities include:

- validating required fields;
- normalizing dates and statuses;
- mapping imported fields into internal collection fields;
- preparing derived values used by dashboards;
- recording relevant activity in `activity_logs` when implemented.

Import adapters only read external formats. Mappers translate external fields into internal models. Validators reject incomplete records and obvious duplicates before data is persisted.

## Persistence

MongoDB is the persistence layer. Repositories should own collection-specific operations and hide database details from UI and services.

Target core collections:

- `patients`
- `appointments`
- `treatments`
- `activity_logs`

Future collections:

- `inventory`
- `finance`
- `external_imports`

## Queries

Operational screens should use simple repository queries for entity lookup and CRUD workflows.

Analytics screens should use aggregation queries for:

- appointment volume by period;
- treatment activity by status;
- active patients;
- pending follow-ups;
- operational workload indicators.

## Dashboards

Streamlit dashboards should consume prepared data from services. UI code should stay focused on layout and interaction, while aggregation logic should live in repositories, services or `src/analytics/`.

## Exports

Export workflows generate local CSV or JSON files from curated repository results. Exported files should not be committed to Git and should remain under ignored local export directories.

Current export folders:

- `data/exports/patients/`
- `data/exports/appointments/`
- `data/exports/metrics/`
