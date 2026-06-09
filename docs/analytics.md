# Analytics

Analytics in Dental Operations Platform are operational, not financial BI. The goal is to help the clinic owner understand workload, agenda use, cancellations, performed treatments and basic patient activity from the local MongoDB dataset.

The default screen period is the current week.

## Screen Structure

The Streamlit analytics screen is intentionally compact:

- top filters;
- KPI cards;
- appointment activity charts;
- occupation view;
- performed treatment view;
- patient activity summary;
- appointment detail table.

Available filters:

- current week;
- current month;
- last 30 days;
- last 90 days;
- custom range;
- clinic;
- chair;
- professional;
- appointment status.

The current MVP keeps the context multi-clinic and multi-chair ready. It also prepares the professional filter for future multi-professional use.

## KPI Definitions

### Appointments

Appointment KPIs are calculated from `appointments` through `AnalyticsService` and `AppointmentRepository`.

- total appointments: all appointments in the filtered period;
- completed appointments: appointments with status `completed`;
- cancelled appointments: appointments with status `cancelled`;
- no-shows: appointments with status `no_show`;
- completion rate: completed appointments / total appointments;
- cancellation rate: cancelled appointments / total appointments;
- no-show rate: no-shows / total appointments.

All ratios return `0` when there are no appointments, avoiding division by zero and misleading technical errors.

### Occupation

MVP occupation is defined as:

```text
occupation = occupied appointment minutes / available appointment minutes
```

Occupied minutes include appointments that are not `cancelled` and not `no_show`.

Available minutes use the MVP fallback definition:

```text
8 hours per working day x visible chair count
```

If a chair filter is active, the resource count is `1`. If no chair filter is active, the resource count is based on visible chairs in the filtered appointment set, with a minimum of `1` for a working day.

This is explicitly marked in the UI as an estimate. A future configuration collection should replace this fallback with real clinic opening hours, chair availability and holiday rules.

### Treatments

Treatment analytics distinguish two concepts:

- treatment catalog: available treatment definitions;
- performed treatments: patient-linked treatment records and `treatment_events`.

Frequent treatments are based on completed `treatment_events`, not on catalog items. If there are catalog items but no completed events in the selected period, the UI shows an informative empty state instead of inventing activity.

### Patients

The analytics screen avoids the ambiguous term "active patient" for operational KPIs.

It shows:

- patients with activity in the selected period;
- patients without activity in the last 90 days;
- patients with an upcoming appointment.

Activity means either an appointment or a treatment event. The screen does not show patient rankings or unnecessary personal details in aggregate analytics.

## Architecture

The screen follows the project architecture:

```text
UI -> Services -> Repositories -> MongoDB
```

Streamlit does not query MongoDB directly. The UI calls `AnalyticsService`, which orchestrates repository reads and prepares UI-ready summaries.

MongoDB-specific filtering and persistence remain in repositories. Cross-collection metric composition remains in services until a dedicated `src/analytics/` layer becomes useful.

## Robustness

The analytics screen must work with demo data, sparse data and empty databases.

Expected behavior:

- no chart crashes when there are no rows;
- no division by zero;
- clear empty-state messages;
- no sensitive patient details in aggregate sections;
- no use of catalog records as performed treatments.

## Limitations

Current limitations are deliberate:

- occupation uses an 8-hour working-day fallback, not persisted clinic schedules;
- no financial dashboard;
- no predictive analytics;
- no clinical history analysis;
- no patient ranking;
- no external BI tooling.

## Future Evolution

Recommended next steps:

- persist operational schedules in `operational_settings`;
- calculate occupation from configured clinic and chair availability;
- add holidays and closures;
- add richer cancellation/no-show trend views;
- move reusable pure metric functions into `src/analytics/metrics.py` when the service grows;
- add data quality indicators for missing clinic, chair or professional data.
