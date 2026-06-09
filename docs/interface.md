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
- weekly view with hours on the vertical axis and days on the horizontal axis;
- monthly view with a selectable month grid that can open the selected day in weekly view.

Appointment actions:

- create appointment;
- mark as completed;
- cancel with optional reason;
- open the linked patient profile.

Overlapping appointments are allowed. When overlaps exist, the UI marks them visually and warns on creation instead of blocking the workflow.

Appointment creation has automated service tests for:

- complete appointment records;
- partial but valid appointment records;
- invalid duration values;
- invalid patient references;
- batch creation with intentional overlaps.

Current logs are enough for application startup and container health, but they are not yet enough for full operational audit. Future agenda hardening should add structured appointment creation logs, validation failure counters and optional rate limits for bulk imports or repeated form submissions.

## Patients

Patients are the central operational navigation entity, not just an administrative table.

The main flow is:

1. Search patient.
2. Open patient profile if found.
3. Create patient from the search context if not found.
4. Act from the profile: new appointment, register treatment or edit patient.

The patient section supports:

- focused search by name, surname, phone, email, patient code and operational notes;
- minimal list with name, phone, status and open/edit actions;
- create patient with required name and surname;
- edit visible patient fields without overwriting hidden fields;
- validate phone, email and status through `PatientService`;
- open a patient profile.

The patient profile contains:

- basic data;
- operational activity metrics;
- upcoming, past and cancelled appointments;
- treatments associated with the patient;
- treatment event history;
- operational notes and status;
- quick actions to create an appointment, register a treatment or edit patient data.

The profile intentionally avoids a full clinical history. Clinical history, odontogram and medical consent workflows are out of scope for this MVP phase.

Demo and real data remain separated through the active MongoDB database configuration. The UI reads from whichever database is configured as active and does not mix sources in the patient screen.

Future patient hardening should add duplicate detection by phone/email, structured audit logs for edits and a persisted settings model for optional patient fields.

## Treatments

Treatments are managed independently from appointment completion. Completing an appointment does not require registering a treatment.

The interface separates two concepts:

- `treatment_catalog`: editable operational catalog of available treatment definitions.
- `treatments` and `treatment_events`: treatments applied to patients and their activity events.

The treatment screen supports:

- search, create and edit catalog items;
- activate or deactivate catalog items;
- register a performed treatment from an active catalog item;
- associate a performed treatment with a patient;
- optionally associate a performed treatment with an appointment;
- consult performed treatments and treatment events with filters by patient, treatment text and date.

The treatment registration form intentionally remains short:

- patient;
- catalog treatment;
- date;
- optional appointment;
- operational observation.

The MVP does not implement full clinical history, odontogram, consent documents or sensitive clinical detail in this screen.

Future treatment hardening should add duplicate prevention for catalog names, richer pricing rules, category configuration and a dedicated clinical history module if the project scope expands.

## Analytics

The analytics screen starts with the current week by default and keeps the MVP intentionally compact. It is an operational view for the odontologist, not a financial BI dashboard.

It shows:

- appointment KPIs: total, completed, cancelled and no-shows;
- explicit occupation estimate based on occupied appointment minutes over available chair minutes;
- appointments by day and by status;
- usage by clinic, chair and professional;
- frequent performed treatments based on completed `treatment_events`;
- treatment event evolution;
- patients with activity in the selected period;
- patients without activity in the last 90 days;
- patients with an upcoming appointment.

Filters support week, month, last 30 days, last 90 days, custom range, clinic, chair, professional and appointment status.

Charts are simple Plotly charts backed by service-level summaries. The UI does not query MongoDB directly and does not use the treatment catalog as evidence of performed treatment activity.

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
