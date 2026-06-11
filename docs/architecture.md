# Architecture

Dental Operations Platform follows a local-first layered architecture. The goal is to keep the MVP simple enough to run on a developer machine while preserving clear boundaries for future growth.

## Current Components

### Streamlit UI

The `app/` package contains the Streamlit entrypoint. The current interface is operational and navigable:

- Agenda is the initial screen and supports daily, weekly and monthly views.
- Pacientes supports search, creation and patient profile navigation.
- Tratamientos supports independent treatment registration and status updates.
- Analitica exposes compact weekly operational metrics.
- Configuracion edits operational settings persisted in MongoDB.
- Admin exposes technical status behind a local MVP PIN.

UI code must call services and must not instantiate MongoDB repositories directly.

### Application Services

The `src/services/` package coordinates business use cases. Services should contain application logic such as validating workflow rules, preparing dashboard data and coordinating repository calls.

Current services:

- `AppointmentService`: agenda windows, appointment creation, completion, cancellation, overlap detection and patient-enriched agenda rows.
- `PatientService`: patient search, creation, update and patient profile composition.
- `TreatmentService`: treatment catalog management, performed treatment registration, status changes and `treatment_events` record composition.
- `AnalyticsService`: weekly and custom-period operational summaries.
- `OperationalSettingsService`: initialization, validation and updates for editable business configuration.
- `AdminService`: technical system status and collection document counts.

### Interoperability Layer

The `src/integrations/` package contains the first import/export foundation. It is intentionally small and focused on future interoperability:

- `ImportEngine` orchestrates reading, validating, mapping and repository persistence.
- `ExportEngine` orchestrates repository collection, mapping and local file generation.
- `adapters/` contains format and source boundaries. CSV and JSON are implemented for demo workflows. Excel, API and external clinic software adapters are explicit future extension points.
- `mapping/` translates external records into internal Pydantic models and maps domain data into export-safe records.
- `validators/` keeps minimum import/export validation outside Streamlit and outside repositories.

This layer must not query MongoDB directly. It calls repositories so collection-level access remains centralized.

### Repository Layer

The `src/repositories/` package isolates MongoDB access from the rest of the application. Repositories are responsible for queries, persistence operations and collection-specific access patterns.

Repositories expose methods with domain intent instead of raw PyMongo queries. Streamlit screens and services should call methods such as `find_by_date_range()`, `get_agenda_occupation()` or `get_treatment_frequency()` and should not build MongoDB filters or aggregation pipelines directly.

Current repositories:

- `PatientRepository`: CRUD, active and inactive patient lookup, name or phone search.
- `AppointmentRepository`: CRUD, patient agenda lookup, date range lookup, status counts and agenda occupation.
- `TreatmentRepository`: CRUD, active treatment lookup, treatment type lookup and most-used treatment analysis.
- `TreatmentCatalogRepository`: CRUD, catalog search, active/inactive listing and catalog field updates.
- `TreatmentEventRepository`: CRUD, lookups by patient, treatment or appointment, treatment activity evolution and treatment frequency.

The shared `BaseMongoRepository` only centralizes the repetitive CRUD mechanics: ObjectId conversion, model serialization, insert, lookup, update and delete. It intentionally does not expose generic raw query or pipeline execution methods. Collection-specific repositories keep MongoDB-aware filters and aggregation pipelines close to the collection they optimize.

This design decouples business logic from PyMongo while preserving MongoDB strengths:

- indexed filters remain available for operational queries;
- aggregation pipelines remain available for dashboard and analytics use cases;
- ObjectId handling is encapsulated before data reaches services or UI code;
- future adapters for clinical software can implement equivalent domain operations without forcing the MVP to hide MongoDB behind an artificial ORM.

### Database Layer

The `src/database/` package contains MongoDB connectivity and index-related infrastructure. The active database is configured through environment variables and Docker Compose.

### Domain Models

The `src/models/` package contains the current core clinic entities: patients, appointments, treatments, treatment events and import sources.

### Analytics

The `src/analytics/` package is reserved for reusable metric and aggregation logic. Streamlit dashboards should consume this layer through services instead of embedding query logic directly in UI code.

Current operational analytics are orchestrated by `AnalyticsService`. The service reads appointments, patients, treatments and treatment events through repositories, applies UI filters outside Streamlit, and returns UI-ready summaries. Treatment frequency is based on completed treatment events, not catalog definitions.

### Imports and Exports

The older `src/imports/` and `src/exports/` packages remain as lightweight placeholders from the initial structure. New interoperability work should use `src/integrations/` because it keeps import engines, export engines, adapters, mappers and validators together.

## Runtime Topology

```text
Browser
  |
  v
Streamlit app container
  |
  v
Python services and repositories
  |
  v
MongoDB container + persistent volume
```

Interoperability runtime flow:

```text
CSV / JSON demo file
  |
  v
Streamlit upload or local script
  |
  v
ImportEngine / ExportEngine
  |
  v
Repositories
  |
  v
MongoDB or data/exports/
```

Docker Compose defines the local runtime:

- `app`: Streamlit application container.
- `mongodb`: MongoDB database container.
- `mongo_data`: persistent MongoDB volume.
- `dental_network`: local bridge network.

Both services define healthchecks. MongoDB uses `mongosh` to run `db.adminCommand('ping')`. The app healthcheck verifies Streamlit's `/_stcore/health` endpoint and a MongoDB ping through the same Python configuration used by the application. The app timeout is intentionally longer than the HTTP timeout because importing Python dependencies and opening a MongoDB client can exceed a very small container healthcheck window on local machines.

Fresh MongoDB volumes are initialized through `mongo/init/01_create_collections.js`, which creates validators and indexes for the current MVP collections. Existing volumes should be updated with `scripts/create_indexes.py`; Docker init scripts run only when MongoDB creates a new database volume.

## Responsibilities

- UI: render workflows and dashboards.
- Services: coordinate use cases, prepare view models and call repository methods.
- Repositories: read and write MongoDB collections through domain-specific methods.
- Database infrastructure: manage connections, healthchecks and indexes.
- Analytics: define reusable KPIs and aggregations.
- Integrations: map external formats to the domain and export repository data without leaking format-specific logic into UI or repositories.
- Documentation: describe product intent, architecture decisions and roadmap.

## Future Scalability

The MVP intentionally avoids microservices, Kubernetes and cloud deployment. Future evolution can still be supported by:

- adding stronger schema validation at the MongoDB collection level;
- introducing indexes aligned with query patterns;
- separating import adapters by source system;
- expanding analytics queries and dashboards;
- adding role-aware workflows if the project evolves toward multi-user usage;
- expanding global agenda filters for multi-clinic operation without creating independent calendars;
- adding audit trail and richer scheduling rules for operational settings.

## Diagrams

Diagram files should be stored in `docs/diagrams/`.

No diagram file is currently present in the repository. The architecture above should be used as the source of truth until diagram assets are added.
