# Analytics

Analytics are part of the product direction, but they should evolve from stable operational data rather than isolated dashboard experiments.

## KPI Areas

### Operational Activity

- appointments per day, week and month;
- appointment status distribution;
- treatment volume by period;
- active treatments;
- completed treatments.

### Patient Activity

- active patients;
- new patients by period;
- patients with upcoming appointments;
- patients requiring follow-up.

### Clinical Workflow

- treatment status distribution;
- average time from treatment start to completion;
- appointment reasons by frequency;
- treatment types by frequency.

### Data Quality

- patients missing contact information;
- appointments without linked patient;
- treatments without status;
- imported rows with validation errors.

## Dashboards

The Streamlit dashboard layer should begin with compact operational views:

- database status and collection overview;
- appointment workload;
- treatment pipeline;
- patient activity;
- data quality checks.

## Aggregated Queries

MongoDB aggregation pipelines should support:

- grouping appointments by date and status;
- counting treatments by type and status;
- joining patient references where needed;
- filtering time windows for dashboard views;
- detecting missing or inconsistent fields.

## Metrics Implementation

Metric definitions should live outside UI code. Preferred locations:

- `src/analytics/` for reusable calculations;
- `src/services/` for application-level dashboard orchestration;
- `src/repositories/` for MongoDB-specific aggregation pipelines.

## MVP Boundaries

The analytics MVP should avoid predictive models, external BI tools and complex orchestration. The goal is to provide useful operational visibility from the local MongoDB dataset.
