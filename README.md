# Dental Clinic Data MVP

Local-first open-source MVP for operational data management in a small dental clinic.

## Goal

Build a local CRM-style application to manage:

- patients
- appointments
- treatments
- treatment events
- basic operational analytics
- future imports from external systems
- local exports and backups

## Design Principles

- Local first
- Open source
- Dockerized
- Provider-independent
- Compatible with macOS and Windows
- Prepared for future external integrations
- Prepared for future multi-user and multi-clinic evolution

## Tech Stack

- Python
- MongoDB
- Streamlit
- Docker / Docker Compose
- Anaconda for local development

## Initial Architecture

```text
Frontend Streamlit
|
Application Services
|
Repositories
|
MongoDB
```
