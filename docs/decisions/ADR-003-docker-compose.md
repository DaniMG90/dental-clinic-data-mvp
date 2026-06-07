# ADR-003: Use Docker Compose for the Local Runtime

## Status

Accepted.

## Context

The project needs a reproducible local environment for Streamlit and MongoDB that can run without cloud infrastructure.

## Decision

Use Docker Compose to orchestrate the local application and database containers.

## Rationale

- Simple local setup for contributors and reviewers.
- Clear separation between app and MongoDB services.
- Persistent MongoDB volume for local development.
- Healthchecks improve startup reliability.

## Consequences

- The MVP remains local-first and avoids deployment complexity.
- Environment variables must be documented and kept in `.env.example`.
- CI/CD, Kubernetes and cloud deployment remain out of scope for now.
