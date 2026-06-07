# ADR-001: Use MongoDB as the Local Operational Database

## Status

Accepted.

## Context

The platform needs a local database for patient, appointment, treatment and activity data. The model is expected to evolve while the MVP is still being shaped.

## Decision

Use MongoDB as the primary local persistence layer.

## Rationale

- Flexible document model for evolving clinic entities.
- Good fit for local Docker Compose development.
- Supports aggregation pipelines for operational analytics.
- Works well with PyMongo and Python service/repository layering.

## Consequences

- The project must define explicit validation and indexing practices.
- Relationships such as `patient_id` and `appointment_id` need careful handling in repositories and services.
- Analytics can use MongoDB aggregations before introducing additional tooling.
