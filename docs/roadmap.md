# Roadmap

The roadmap keeps the project aligned with a local MVP, open source learning value and portfolio-grade evidence.

## Foundation Setup

Scope:

- GitHub repository structure;
- Docker Compose runtime;
- MongoDB local persistence;
- Streamlit startup;
- environment configuration;
- repository documentation.

Status: completed.

## Core Data Model

Scope:

- define patient, appointment, treatment and activity log models;
- create MongoDB indexes;
- define basic validation rules;
- prepare demo seed data;
- document current and future collections.

Status: completed for MVP core collections. Future hardening remains planned.

## CRUD Operations

Scope:

- patient creation, listing and detail views;
- appointment scheduling and status updates;
- treatment creation and status tracking;
- repository and service tests for core workflows.

Status: in progress. First operational Streamlit workflows are implemented, including editable MongoDB-backed operational configuration.

## Analytics MVP

Scope:

- dashboard structure in Streamlit;
- operational KPIs;
- MongoDB aggregation queries;
- treatment and appointment metrics;
- data quality indicators.

Status: in progress. Operational Streamlit analytics now include period filters, appointment KPIs, explicit occupation estimates, performed-treatment metrics from `treatment_events` and patient activity indicators.

## Public Release v0.1

Scope:

- complete README and technical docs;
- issue and pull request templates;
- license validation;
- basic tests for models, repositories and services;
- regression tests for documentation, Docker configuration and lightweight Streamlit UI helpers;
- release notes;
- clear local installation instructions.

Status: in progress. Local tests, Docker healthchecks and operational documentation are now part of the stabilization baseline.

## Recommended Post-MVP Hardening

- add a lightweight browser smoke test only if UI regressions become frequent;
- add explicit backup and restore scripts after the data model stabilizes further;
- add audit logs for sensitive operational edits;
- refine Admin diagnostics without adding destructive operations by default;
- keep demo and real database workflows clearly separated.

## Out of Scope for Current MVP

- GitHub Actions and CI/CD;
- Kubernetes;
- cloud deployment;
- microservices;
- complex automation;
- predictive analytics;
- production-grade identity and access management.
