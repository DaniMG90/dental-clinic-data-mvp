from datetime import date, datetime, timedelta, timezone

import pandas as pd
from bson import ObjectId

from app import main as streamlit_app
from src.models.appointment import Appointment, AppointmentStatus


def appointment_at(start: datetime, minutes: int = 30) -> Appointment:
    return Appointment(
        _id=ObjectId(),
        appointment_code=f"APT-{start.strftime('%H%M')}",
        patient_id=ObjectId(),
        scheduled_start=start,
        scheduled_end=start + timedelta(minutes=minutes),
        duration_minutes=minutes,
        status=AppointmentStatus.SCHEDULED,
    )


def test_streamlit_entrypoint_imports_without_database_access():
    assert callable(streamlit_app.main)


def test_date_window_supports_daily_weekly_and_monthly_views():
    selected = date(2026, 1, 15)

    daily_start, daily_end = streamlit_app._date_window("Diaria", selected)
    weekly_start, weekly_end = streamlit_app._date_window("Semanal", selected)
    monthly_start, monthly_end = streamlit_app._date_window("Mensual", selected)

    assert daily_start == datetime(2026, 1, 15)
    assert daily_end == datetime(2026, 1, 16)
    assert weekly_start == datetime(2026, 1, 12)
    assert weekly_end == datetime(2026, 1, 19)
    assert monthly_start == datetime(2026, 1, 1)
    assert monthly_end == datetime(2026, 2, 1)


def test_patient_name_guess_uses_search_text_without_requiring_extra_copy():
    assert streamlit_app._guess_patient_name("") == ("", "")
    assert streamlit_app._guess_patient_name("Ana") == ("Ana", "")
    assert streamlit_app._guess_patient_name("Ana Garcia Lopez") == ("Ana", "Garcia Lopez")


def test_overlapping_ids_marks_only_conflicting_appointments():
    base = datetime(2026, 1, 1, 9, tzinfo=timezone.utc)
    first = appointment_at(base, 60)
    overlapping = appointment_at(base + timedelta(minutes=30), 30)
    separate = appointment_at(base + timedelta(hours=2), 30)

    overlapping_ids = streamlit_app._overlapping_ids([first, overlapping, separate])

    assert first.id in overlapping_ids
    assert overlapping.id in overlapping_ids
    assert separate.id not in overlapping_ids


def test_clean_editor_rows_keeps_only_meaningful_configuration_rows():
    dataframe = pd.DataFrame(
        [
            {"name": "Clinic Centro", "code": "CENTRO", "active": True},
            {"name": "", "code": "", "active": None},
            {"name": None, "code": "NORTE", "active": True},
        ],
    )

    rows = streamlit_app._clean_editor_rows(dataframe, ["name", "code", "active"])

    assert rows == [
        {"name": "Clinic Centro", "code": "CENTRO", "active": True},
        {"name": "", "code": "NORTE", "active": True},
    ]
