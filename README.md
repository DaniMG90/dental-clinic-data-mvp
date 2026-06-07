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
Import / Export Engines
|
Repositories
|
MongoDB
```

The repository layer is the only application layer that should use collection-level MongoDB access. Services and Streamlit code call domain methods such as `PatientRepository.find_active_patients()`, `AppointmentRepository.get_agenda_occupation()` and `TreatmentEventRepository.get_treatment_activity_evolution()` instead of constructing PyMongo filters or pipelines directly.

The interoperability layer lives in `src/integrations/`. It separates adapters, mappers, validators and orchestration engines so external formats do not leak into models, repositories or Streamlit screens. The first supported demo formats are CSV and JSON for patient and appointment imports, plus CSV and JSON exports for patients, appointments and operational metrics. Excel, API and external clinic software adapters are intentionally prepared as future extension points, not implemented integrations.

The local runtime is orchestrated with Docker Compose and includes:

- a Streamlit application container;
- a MongoDB container with persistent volume;
- healthchecks for app and database readiness;
- environment-based configuration for local development.

See [docs/architecture.md](docs/architecture.md) for the full technical view.

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
- `treatment_events`

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

### Setup

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

## Tests

Run the automated tests with the project Conda environment:

```bash
conda run -n dental-clinic-mvp python -m pytest
```

If `conda` is not available in the shell PATH, use the local Conda binary directly, for example:

```bash
/opt/anaconda3/bin/conda run -n dental-clinic-mvp python -m pytest
```

## Project Status

Current phase: Foundation Setup / Core Data Model preparation.

Implemented foundations include Docker Compose, MongoDB connectivity, Streamlit startup validation, environment configuration, domain-oriented MongoDB repositories, a first interoperability import/export layer and preliminary documentation.

Planned next work includes completing domain models, repositories, seed data, indexes, CRUD flows, analytics queries and dashboards.

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
