# ADR-002: Use Streamlit for the Local Application Interface

## Status

Accepted.

## Context

The MVP needs a fast local interface for operational workflows and dashboards without introducing a full frontend stack.

## Decision

Use Streamlit as the local UI and dashboard framework.

## Rationale

- Fast iteration for data-oriented Python applications.
- Natural fit for dashboards, tables and operational views.
- Keeps the MVP focused on data modeling, services and analytics.
- Reduces frontend complexity for a personal open source project.

## Consequences

- UI code should stay thin and delegate logic to services.
- Complex multi-user workflows are out of scope for the current MVP.
- Future frontend changes remain possible because business logic is kept outside Streamlit.
