# Configuration

Configuration contains operational business settings. It is designed for the clinic owner or odontologist to adjust normal clinic behavior without technical database work.

Admin remains the place for technical maintenance, diagnostics, index review and future controlled repair tools.

## Storage

Operational configuration is persisted in MongoDB collection:

```text
operational_settings
```

The MVP uses one main document:

```text
settings_key = "default"
```

`OperationalSettingsService.get_settings()` creates the default document when the collection is empty and merges missing fields with current defaults when the schema evolves.

## Editable Areas

The Streamlit Configuration screen is split into tabs:

- General;
- Clinics and chairs;
- Weekly schedules;
- Agenda;
- Professionals;
- Analytics;
- Security / data.

No raw JSON editor is exposed to users.

## Defaults

Initial defaults are aligned with the current MVP:

- business name: Dental Operations Platform;
- internal identifier: LOCAL-CLINIC;
- data mode: demo;
- timezone: Europe/Madrid;
- clinics: Clinic Centro and Clinic Norte;
- chairs: two chairs per clinic;
- professionals: Dr. Alvarez and Dr. Rivera;
- agenda default duration: 45 minutes;
- visible agenda hours: 08:00 to 21:00;
- overlaps: allowed with warning;
- analytics default period: weekly;
- inactive-patient threshold: 180 days;
- treatment categories: Orthodontics, Surgery, Preventive, Aesthetic and General.

Weekly schedules default to Monday-Friday with two blocks:

- 09:00-14:00;
- 16:00-20:00.

Saturday and Sunday are closed by default.

## Permissions

- Auxiliar: can view basic configuration, cannot modify it.
- Odontologo: can modify operational configuration.
- Admin: can modify operational configuration and uses Admin for technical tasks.

The MVP keeps the existing local role selector. It does not introduce new authentication.

## Integrations

Agenda reads:

- active clinics;
- active chairs;
- active professionals;
- visible agenda hours;
- default appointment duration;
- enabled appointment statuses;
- overlap policy.

Analytics reads:

- active clinics, chairs and professionals for filters;
- default analytics period;
- inactive-patient threshold;
- weekly schedules for occupation calculation.

Treatments reads:

- configured categories for catalog forms.

Patients are not directly affected.

## Validation

Validation is enforced by Pydantic models and service-level updates:

- names and codes cannot be empty;
- clinic and chair codes must be unique;
- active chairs must belong to an active clinic;
- weekly schedules must reference existing clinics;
- time blocks must start before they end;
- agenda start hour must be before end hour;
- appointment durations and visual intervals must be positive;
- at least one appointment status must stay enabled;
- inactive-patient threshold must be positive;
- timezone must be valid.

## Boundaries

Configuration does not include:

- database repairs;
- destructive cleanup;
- backup or restore tools;
- index maintenance;
- advanced diagnostics.

Those belong in Admin.

## Future Evolution

Recommended improvements:

- add holiday and exception calendars;
- support clinic-specific default appointment durations;
- store professional availability by day;
- use chair codes instead of only display names in appointments;
- add audit trail for configuration changes;
- evolve the local role selector into proper authentication when needed.
