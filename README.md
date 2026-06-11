# Dental Operations Platform

Local-first open source platform for operational data management and analytics in dental clinics.

## Executive Summary

Dental Operations Platform is a Python, MongoDB, Docker Compose and Streamlit project designed to centralize operational clinic data, expose a simple local interface, and prepare the ground for data-driven decisions.

The project is currently an evolving MVP. Its first milestone is a robust local environment with MongoDB persistence, a Streamlit application, clear service and repository layers, and technical documentation that can support future CRUD workflows, dashboards, imports, exports and interoperability adapters.

## Problem

Small dental clinics often manage patients, appointments, treatments and operational indicators across disconnected tools. This makes it harder to understand workload, treatment activity, appointment flow, follow-up needs and the operational health of the clinic.

This project explores a focused alternative: a local, understandable and extensible platform where operational data can be stored, queried and analyzed without introducing cloud deployment complexity at the MVP stage.

## Objectives

- Operational management: model patients, appointments, treatments and activity logs as the core clinic entities.
- Analytics: provide a foundation for KPIs, aggregate queries and Streamlit dashboards.
- Technical learning: practice product-oriented repository structure, MongoDB data modeling, Dockerized local environments and Python application layering.
- Extensible platform: keep the architecture ready for future inventory, finance and external system integrations.

## Architecture

The current architecture follows a simple layered model:

```text
Streamlit UI
|
Application Services
|
Repositories / Import-Export Engines
|
MongoDB
```

The repository layer is the only application layer that should use collection-level MongoDB access. Services and Streamlit code call domain methods through service orchestration, for example `AnalyticsService.summary()`, `AppointmentRepository.find_by_date_range()` and `TreatmentEventRepository.get_treatment_activity_evolution()`, instead of constructing PyMongo filters or pipelines directly in the UI.

The interoperability layer lives in `src/integrations/`. It separates adapters, mappers, validators and orchestration engines so external formats do not leak into models, repositories or Streamlit screens. The first supported demo formats are CSV and JSON for patient and appointment imports, plus CSV and JSON exports for patients, appointments and operational metrics. Excel, API and external clinic software adapters are intentionally prepared as future extension points, not implemented integrations.

The local runtime is orchestrated with Docker Compose and includes:

- a Streamlit application container;
- a MongoDB container with persistent volume;
- healthchecks for app and database readiness;
- environment-based configuration for local development.

See [docs/architecture.md](docs/architecture.md) for the full technical view.
See [docs/interface.md](docs/interface.md) for the current Streamlit navigation, roles and screens.

Diagram files should live in [docs/diagrams/](docs/diagrams/) when added or updated.

## Data Flow

The target flow is:

```text
External or manual data source
-> Streamlit UI / import adapter
-> Application services
-> Repository layer
-> MongoDB collections
-> Aggregations and queries
-> Dashboards and exports
```

See [docs/data-flow.md](docs/data-flow.md) for details.

## Tech Stack

- Python
- MongoDB
- Docker
- Docker Compose
- Streamlit
- Pandas
- Plotly
- PyMongo

## Data Model

The core model is centered on:

- `patients`
- `appointments`
- `treatments`
- `treatment_catalog`
- `treatment_events`
- `operational_settings`
- `import_sources`

Future collections include:

- `inventory`
- `finance`
- `external_imports`

See [docs/data-model.md](docs/data-model.md).

## Interoperability

The MVP includes a first import/export foundation:

- `ImportEngine`: reads CSV/JSON demo files, validates minimum structure, maps external records to domain models and persists through repositories.
- `ExportEngine`: collects repository data, maps it to external-safe records and writes local CSV/JSON files under `data/exports/`.
- Mappers: keep external field names separated from internal Pydantic models.
- Validators: reject incomplete records and obvious duplicates before persistence.

Tracked demo files:

- [data/demo/sample_patients.csv](data/demo/sample_patients.csv)
- [data/demo/sample_patients.json](data/demo/sample_patients.json)
- [data/demo/sample_appointments.csv](data/demo/sample_appointments.csv)
- [data/demo/sample_appointments.json](data/demo/sample_appointments.json)

Generated exports are ignored by Git. See [docs/interoperability.md](docs/interoperability.md) for usage, limits and anonymization guidance.

## Roadmap

The roadmap is organized around local foundation work, core data modeling, CRUD operations, analytics MVP and a public release.

See [docs/roadmap.md](docs/roadmap.md).

## Local Installation

### Requirements

- Docker
- Docker Compose
- Conda, only when running the development/test commands outside Docker

### Docker Compose Setup

1. Copy the environment template:

```bash
cp .env.example .env
```

2. Start the local stack:

```bash
docker compose up --build
```

3. Open Streamlit:

```text
http://localhost:8501
```

4. Stop the stack:

```bash
docker compose down
```

To remove local MongoDB data as well:

```bash
docker compose down -v
```

The Compose stack exposes:

- Streamlit at `http://localhost:8501`;
- MongoDB at `localhost:${MONGO_LOCAL_PORT:-27017}`;
- a MongoDB healthcheck using `mongosh`;
- an app healthcheck that verifies Streamlit HTTP health and MongoDB ping.

### Local Development Without Containers

For host-side scripts and tests, use the project Conda environment:

```bash
/opt/anaconda3/bin/conda run -n dental-clinic-mvp python -m pytest
```

When running MongoDB-facing scripts from the host while Docker Compose is running, override the internal Docker hostname:

```bash
MONGO_HOST=localhost /opt/anaconda3/bin/conda run -n dental-clinic-mvp python scripts/create_indexes.py
MONGO_HOST=localhost /opt/anaconda3/bin/conda run -n dental-clinic-mvp python scripts/seed_demo_data.py
```

`scripts/create_indexes.py` applies collection validators and indexes without dropping data. `scripts/seed_demo_data.py` upserts anonymous demo records and the default operational configuration.

### Environment Variables

The runtime is configured through `.env`, based on [.env.example](.env.example):

- `APP_ENV`: local environment label.
- `MONGO_INITDB_ROOT_USERNAME` and `MONGO_INITDB_ROOT_PASSWORD`: local MongoDB credentials.
- `MONGO_HOST`, `MONGO_PORT` and `MONGO_LOCAL_PORT`: container and host MongoDB connection settings.
- `MONGO_DATABASE`, `MONGO_DEMO_DATABASE`, `MONGO_DEV_DB`, `MONGO_DEMO_DB` and `MONGO_ACTIVE_DB`: database names and active database selection.
- `MONGO_CONNECT_MAX_RETRIES`, `MONGO_RETRY_DELAY_SECONDS` and `MONGO_TIMEOUT_MS`: MongoDB client retry behavior.
- `STREAMLIT_PORT`: exposed local Streamlit port.
- `DENTAL_ADMIN_PIN`: optional local Admin PIN. If omitted, the MVP default is `admin`.

Do not commit local `.env` files, real credentials, backups or exported real clinic data.

## Tests

Run the automated tests with the project Conda environment:

```bash
conda run -n dental-clinic-mvp python -m pytest
```

If `conda` is not available in the shell PATH, use the local Conda binary directly, for example:

```bash
/opt/anaconda3/bin/conda run -n dental-clinic-mvp python -m pytest
```

Current tests cover models, repositories, services, import/export, regression checks for documentation and configuration, and lightweight Streamlit UI helper behavior. They are designed to run without destructive writes to real clinic data.

For syntax/import validation:

```bash
/opt/anaconda3/bin/conda run -n dental-clinic-mvp python -m compileall app src tests scripts
```

## Demo Data, Real Data And Backups

The repository includes anonymous demo CSV/JSON files under `data/demo/` and a deterministic seed script. Demo data is for local development, tests and portfolio demonstrations.

Real operational data should use a separate MongoDB database selected with `MONGO_ACTIVE_DB`. Do not mix real data with demo seed data in the same database, and do not commit exports containing real patient or clinic information.

Backups are intentionally manual in the current MVP. Recommended local practice:

- stop the app before making a backup if consistency matters;
- use MongoDB tools such as `mongodump` against the active local database;
- store backups outside the Git repository;
- verify restores on a separate local database before relying on them.

Admin currently shows a backup placeholder only. It does not create, restore or delete backups.

## Project Status

Current phase: Operational Interface MVP.

Implemented foundations include Docker Compose, MongoDB connectivity, environment configuration, domain models, MongoDB validators and indexes, domain-oriented repositories, service-layer workflows, a first interoperability import/export layer and documentation.

The Streamlit application now includes a navigable operational interface with Agenda as the initial screen, patient management, patient profiles, treatment registration, operational analytics with a weekly default period, editable MongoDB-backed operational configuration and a basic technical Admin area.

Current limitations:

- local role selection is not production authentication;
- Stock is visible as a future module but not implemented;
- backups are manual;
- no cloud deployment, Kubernetes, microservices or CI/CD are required for the MVP;
- no clinical history, odontogram, consent workflow or financial dashboard is implemented.

## Design Principles

- Local first
- Open source
- Dockerized
- Provider-independent
- Compatible with macOS and Windows
- Prepared for future external integrations
- Prepared for future multi-user and multi-clinic evolution

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
