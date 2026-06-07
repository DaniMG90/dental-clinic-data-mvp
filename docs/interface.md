# Streamlit Interface

This document describes the first operational interface for the Dental Operations Platform MVP.

## Navigation

The application uses a Streamlit sidebar with these sections:

- Agenda
- Pacientes
- Tratamientos
- Analitica
- Stock
- Configuracion
- Admin

The initial screen is Agenda. This keeps the product focused on daily clinic operation instead of opening with an analytics dashboard.

Stock is visible but marked as a future module. It is intentionally not implemented in this phase.

## Roles

Role handling is deliberately simple in this MVP:

- Auxiliar: daily agenda, appointment actions, patient lookup and patient consultation.
- Odontologo: auxiliary workflows plus treatments, analytics and operational configuration.
- Admin: technical system view behind a local PIN.

The local Admin PIN defaults to `admin` and can be overridden with `DENTAL_ADMIN_PIN`.

This is not production authentication. The intended evolution is persistent users, password hashing, sessions, role permissions and audit logging.

## Agenda

Agenda is global. It supports filtering by clinic, chair, professional, status and date while avoiding independent calendars.

Available views:

- daily view with hour blocks;
- weekly view as a table plus simple chart;
- monthly view as a table plus simple chart.

Appointment actions:

- create appointment;
- mark as completed;
- cancel with optional reason;
- open the linked patient profile.

Overlapping appointments are allowed. When overlaps exist, the UI marks them visually and warns on creation instead of blocking the workflow.

## Patients

Patients are the central navigation entity.

The patient section supports:

- list active and inactive records;
- search by name, surname or phone;
- create patient;
- edit operational notes and status;
- open a patient profile.

The patient profile contains:

- basic data;
- operational activity metrics;
- appointment history;
- treatment history;
- treatment event history;
- quick actions to create an appointment or register a treatment.

## Treatments

Treatments are managed independently from appointment completion. A treatment can be registered from the patient context or later from the treatment screen.

The treatment screen supports:

- create treatment;
- consult the treatment catalog/data already stored in `treatments`;
- update treatment status;
- create `treatment_events` for treatment creation and status changes.

## Analytics

The analytics screen starts with a weekly period by default and keeps the MVP intentionally compact.

It shows:

- active patients;
- cancellations;
- appointments by status;
- agenda occupation by day;
- frequent treatments;
- treatment activity evolution.

Charts are simple Plotly charts backed by service-level summaries.

## Configuration

Configuration is currently read-only and code-backed to avoid premature persistence complexity.

It displays:

- clinics;
- chairs;
- professionals;
- default appointment duration;
- appointment statuses.

Future evolution should move this into an `operational_settings` collection once the workflows stabilize.

## Admin

Admin shows:

- MongoDB connection state;
- active database;
- demo/real database mode;
- document counts by collection;
- backup placeholder;
- future maintenance and diagnostics placeholders.

No destructive operation is executed from Admin in this MVP.
