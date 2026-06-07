# GitHub Governance

This document defines lightweight GitHub repository management conventions for the MVP.

## Labels

Target labels:

| Label | Use |
| --- | --- |
| `enhancement` | New product or technical capability. |
| `bug` | Behavior that does not work as expected. |
| `documentation` | README, docs, diagrams, ADRs or templates. |
| `analytics` | KPIs, dashboards, aggregation queries and metrics. |
| `mongodb` | MongoDB connection, collections, indexes and validation. |
| `dashboard` | Streamlit dashboard screens and visualizations. |
| `docker` | Dockerfile, Docker Compose and local runtime setup. |
| `data-model` | Patients, appointments, treatments, activity logs and schema changes. |
| `security` | Secrets handling, data privacy and access-related concerns. |
| `integration` | Future external systems, imports and adapters. |
| `good-first-issue` | Small, well-scoped issues suitable for first contributions. |

Existing default labels should be kept when useful. If the repository already has `good first issue`, it can be kept as the GitHub default; `good-first-issue` is the normalized target label for this project.

## Project Board

Recommended board name: `Dental Operations Platform`.

Columns:

- Backlog: ideas and accepted future work.
- Ready: scoped issues ready to implement.
- In Progress: work currently being developed.
- Review: changes waiting for review or local validation.
- Done: completed issues and released documentation tasks.

## Milestones

### Foundation Setup

- GitHub repository structure.
- Docker Compose.
- MongoDB.
- Local environment.

### Core Data Model

- Collections.
- Indexes.
- Validations.

### CRUD Operations

- Patients.
- Appointments.
- Treatments.

### Analytics MVP

- Dashboards.
- KPIs.

### Public Release v0.1

- Documentation.
- Tests.
- Release preparation.

## Current Remote Audit

GitHub checks through the project environment (`dental-clinic-mvp`) showed:

- issues: none found;
- milestones: target milestones created;
- labels: default labels preserved and target project labels created;
- project boards: not confirmed because the current GitHub token is missing the `read:project` / project scope required by GitHub Projects v2.

Project board creation or adaptation requires refreshing the GitHub CLI token with project permissions.
