# ADR-004: Operational Streamlit Interface

## Status

Accepted.

## Context

The MVP needs to become usable as a local clinic operations tool without introducing a frontend framework or a complex authentication layer. Existing documentation already defines a layered architecture and Streamlit as the main UI.

The product direction requires Agenda to be the default screen, patients to be the central entity, and treatments to be independent from appointment completion.

## Decision

Implement a simple Streamlit sidebar application with these operational sections:

- Agenda;
- Pacientes;
- Tratamientos;
- Analitica;
- Stock;
- Configuracion;
- Admin.

All UI reads and writes go through application services. Services coordinate repositories, and repositories remain the only layer with MongoDB collection access.

The agenda is global and filterable by clinic, chair and professional. Appointments may overlap. The UI warns visually but does not block creation.

Admin uses a local PIN in this phase and documents the path toward robust authentication.

## Consequences

Positive:

- the MVP becomes navigable and demonstrable;
- the interface stays easy to iterate with Streamlit;
- service tests can cover business workflows without launching Streamlit;
- future multi-clinic support is prepared without splitting calendars.

Tradeoffs:

- role handling is not production-grade authentication;
- operational settings are code-backed until workflows stabilize;
- the UI is intentionally simple and will need iterative UX refinement after real use.
