# Data Flow

This document describes the target data flow for the local MVP and the future analytics layer.

## High-Level Flow

```text
Manual entry or external source
-> Streamlit UI / import adapter
-> Application service
-> Repository
-> MongoDB collection
-> Aggregation or query
-> Streamlit dashboard / CSV export
```

## Data Origins

Initial data sources are expected to be:

- manual entry through Streamlit forms;
- demo seed data for local development;
- future imports from CSV files or external clinic systems.

External integrations are intentionally future-facing. The MVP should first stabilize local data structures and operational workflows.

## Transformation

Application services should be responsible for transforming raw UI input or imported rows into normalized application objects.

Transformation responsibilities include:

- validating required fields;
- normalizing dates and statuses;
- mapping imported fields into internal collection fields;
- preparing derived values used by dashboards;
- recording relevant activity in `activity_logs` when implemented.

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

Future export workflows can generate local CSV files from curated query results. Exported files should not be committed to Git and should remain under ignored local export directories.
