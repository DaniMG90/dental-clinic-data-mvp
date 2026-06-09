from datetime import date, datetime, time, timedelta
from os import getenv
from typing import Iterable

import pandas as pd
import plotly.express as px
import streamlit as st

from src.models.appointment import Appointment, AppointmentStatus
from src.models.patient import Patient, PatientStatus
from src.models.treatment import TreatmentStatus
from src.services.admin_service import AdminService
from src.services.analytics_service import AnalyticsFilters, AnalyticsService
from src.services.appointment_service import AgendaFilters, AppointmentService
from src.services.database_status_service import DatabaseStatusService
from src.services.patient_service import PatientService, PatientServiceError
from src.services.treatment_service import TreatmentService, TreatmentServiceError


CLINICS = ["Clinic Centro", "Clinic Norte"]
CHAIRS = ["Gabinete 1", "Gabinete 2"]
PROFESSIONALS = ["Dr. Alvarez", "Dr. Rivera"]
DEFAULT_APPOINTMENT_MINUTES = 45
OPERATING_DAY_START = 8
OPERATING_DAY_END = 21


st.set_page_config(page_title="Dental Operations Platform", page_icon="D", layout="wide")


def main() -> None:
    _load_styles()
    _init_state()

    status = DatabaseStatusService().get_status()
    _render_sidebar(status.connected)

    st.title("Dental Operations Platform")

    if not status.connected:
        st.error("MongoDB no esta disponible.")
        st.code(status.error or "Unknown connection error")
        return

    section = st.session_state.section
    role = st.session_state.role

    if section == "Agenda":
        _render_agenda()
    elif section == "Pacientes":
        _render_patients()
    elif section == "Tratamientos":
        _render_treatments(disabled=role == "Auxiliar")
    elif section == "Analitica":
        _render_analytics(disabled=role == "Auxiliar")
    elif section == "Stock":
        _render_stock()
    elif section == "Configuracion":
        _render_configuration(disabled=role == "Auxiliar")
    elif section == "Admin":
        _render_admin()


def _init_state() -> None:
    st.session_state.setdefault("section", "Agenda")
    st.session_state.setdefault("role", "Auxiliar")
    st.session_state.setdefault("selected_patient_id", None)
    st.session_state.setdefault("agenda_view", "Diaria")
    st.session_state.setdefault("agenda_date", date.today())
    st.session_state.setdefault("pending_agenda_view", None)
    st.session_state.setdefault("pending_agenda_date", None)
    st.session_state.setdefault("patient_quick_action", None)


def _render_sidebar(database_connected: bool) -> None:
    with st.sidebar:
        st.caption("Operacion diaria")
        st.session_state.role = st.selectbox("Rol local", ["Auxiliar", "Odontologo", "Admin"])

        sections = ["Agenda", "Pacientes", "Tratamientos", "Analitica", "Stock", "Configuracion", "Admin"]
        st.session_state.section = st.radio(
            "Navegacion",
            sections,
            index=sections.index(st.session_state.section),
        )

        if st.session_state.section == "Stock":
            st.info("Stock esta visible como modulo futuro.")

        st.divider()
        st.metric("MongoDB", "OK" if database_connected else "Sin conexion")
        st.caption("Arquitectura: UI -> Services -> Repositories -> MongoDB")


def _render_agenda() -> None:
    service = AppointmentService()
    patient_service = PatientService()

    st.subheader("Agenda")
    _apply_pending_agenda_navigation()
    view_mode, selected_date, filters = _agenda_controls()
    start_date, end_date = _date_window(view_mode, selected_date)
    rows = service.list_with_patients(start_date, end_date, filters)

    create_tab, view_tab = st.tabs(["Crear cita", f"Vista {view_mode.lower()}"])
    with create_tab:
        _render_create_appointment_form(service, patient_service, selected_date)

    with view_tab:
        if view_mode == "Diaria":
            _render_daily_agenda(rows, service, selected_date)
        elif view_mode == "Semanal":
            _render_weekly_agenda(rows, service, selected_date)
        else:
            _render_monthly_agenda(rows, selected_date)


def _agenda_controls() -> tuple[str, date, AgendaFilters]:
    columns = st.columns([1, 1, 1, 1, 1])
    with columns[0]:
        view_mode = st.radio("Vista", ["Diaria", "Semanal", "Mensual"], horizontal=True, key="agenda_view")
    with columns[1]:
        selected_date = st.date_input("Fecha", key="agenda_date")
    with columns[2]:
        clinic = st.selectbox("Clinica", ["Todas", *CLINICS])
    with columns[3]:
        chair = st.selectbox("Gabinete", ["Todos", *CHAIRS])
    with columns[4]:
        professional = st.selectbox("Profesional", ["Todos", *PROFESSIONALS])

    status = st.selectbox("Estado", ["Todos", *[item.value for item in AppointmentStatus]])
    return (
        view_mode,
        selected_date,
        AgendaFilters(
            clinic=None if clinic == "Todas" else clinic,
            chair=None if chair == "Todos" else chair,
            professional=None if professional == "Todos" else professional,
            status=None if status == "Todos" else AppointmentStatus(status),
        ),
    )


def _render_create_appointment_form(
    service: AppointmentService,
    patient_service: PatientService,
    selected_date: date,
) -> None:
    patients = patient_service.search_patients("", limit=200)
    patient_options = {f"{patient.last_name}, {patient.first_name} ({patient.patient_code})": patient for patient in patients}

    if not patient_options:
        st.info("No hay pacientes. Crea primero un paciente desde Pacientes.")
        return

    default_patient_label = next(iter(patient_options))
    selected_patient_id = st.session_state.selected_patient_id
    if selected_patient_id:
        for label, patient in patient_options.items():
            if str(patient.id) == selected_patient_id:
                default_patient_label = label
                break

    with st.form("create_appointment_form", clear_on_submit=True):
        columns = st.columns(3)
        patient_label = columns[0].selectbox(
            "Paciente",
            list(patient_options),
            index=list(patient_options).index(default_patient_label),
        )
        appointment_date = columns[1].date_input("Fecha cita", value=selected_date)
        appointment_time = columns[2].time_input("Hora", value=time(9, 0))

        columns = st.columns(4)
        duration = columns[0].number_input("Duracion min.", min_value=10, max_value=240, value=DEFAULT_APPOINTMENT_MINUTES, step=5)
        clinic = columns[1].selectbox("Clinica", CLINICS)
        chair = columns[2].selectbox("Gabinete", CHAIRS)
        professional = columns[3].selectbox("Profesional", PROFESSIONALS)

        reason = st.text_input("Motivo")
        notes = st.text_area("Notas operativas", height=80)
        submitted = st.form_submit_button("Crear cita")

    if submitted:
        patient = patient_options[patient_label]
        scheduled_start = datetime.combine(appointment_date, appointment_time)
        created, overlaps = service.create_appointment(
            patient.id,
            scheduled_start,
            int(duration),
            reason=reason,
            clinic=clinic,
            chair=chair,
            professional=professional,
            notes=notes,
        )
        st.success(f"Cita creada: {created.appointment_code}")
        if overlaps:
            st.warning(f"La cita se solapa con {len(overlaps)} cita(s). Se permite por diseno operativo.")


def _render_daily_agenda(rows: list[dict], service: AppointmentService, selected_date: date) -> None:
    st.caption("Vista diaria por bloques horarios. Los solapes aparecen resaltados.")
    _render_time_grid_agenda(rows, [selected_date], service)


def _render_weekly_agenda(rows: list[dict], service: AppointmentService, selected_date: date) -> None:
    week_start = selected_date - timedelta(days=selected_date.weekday())
    days = [week_start + timedelta(days=offset) for offset in range(7)]
    st.caption(f"Semana {week_start.isoformat()} - {(week_start + timedelta(days=6)).isoformat()}")
    _render_time_grid_agenda(rows, days, service)


def _render_time_grid_agenda(rows: list[dict], days: list[date], service: AppointmentService) -> None:
    appointments = [row["appointment"] for row in rows]
    overlapping_ids = _overlapping_ids(appointments)

    if not rows:
        st.info("No hay citas para los filtros seleccionados.")
        _render_empty_time_grid(days)
        return

    st.markdown("<div class='calendar-shell'>", unsafe_allow_html=True)
    header_columns = st.columns([0.55, *([1] * len(days))])
    header_columns[0].markdown("**Hora**")
    for index, day_value in enumerate(days, start=1):
        header_columns[index].markdown(f"**{_weekday_label(day_value)}**<br><small>{day_value.strftime('%d/%m')}</small>", unsafe_allow_html=True)

    for hour in range(OPERATING_DAY_START, OPERATING_DAY_END):
        columns = st.columns([0.55, *([1] * len(days))])
        columns[0].markdown(f"<div class='calendar-hour'>{hour:02d}:00</div>", unsafe_allow_html=True)
        for day_index, day_value in enumerate(days, start=1):
            hour_rows = [
                row
                for row in rows
                if row["appointment"].scheduled_start.date() == day_value
                and row["appointment"].scheduled_start.hour == hour
            ]
            with columns[day_index]:
                if not hour_rows:
                    st.markdown("<div class='empty-slot'></div>", unsafe_allow_html=True)
                for row in hour_rows:
                    _render_appointment_card(
                        row["appointment"],
                        row["patient"],
                        service,
                        row["appointment"].id in overlapping_ids,
                    )
    st.markdown("</div>", unsafe_allow_html=True)
    _render_out_of_hours(rows, days, service, overlapping_ids)


def _render_empty_time_grid(days: list[date]) -> None:
    header_columns = st.columns([0.55, *([1] * len(days))])
    header_columns[0].markdown("**Hora**")
    for index, day_value in enumerate(days, start=1):
        header_columns[index].markdown(f"**{_weekday_label(day_value)}**<br><small>{day_value.strftime('%d/%m')}</small>", unsafe_allow_html=True)
    for hour in range(OPERATING_DAY_START, OPERATING_DAY_END):
        columns = st.columns([0.55, *([1] * len(days))])
        columns[0].markdown(f"<div class='calendar-hour'>{hour:02d}:00</div>", unsafe_allow_html=True)
        for index in range(1, len(days) + 1):
            columns[index].markdown("<div class='empty-slot'></div>", unsafe_allow_html=True)


def _render_out_of_hours(
    rows: list[dict],
    days: list[date],
    service: AppointmentService,
    overlapping_ids: set,
) -> None:
    out_of_hours = [
        row
        for row in rows
        if row["appointment"].scheduled_start.date() in days
        and (
            row["appointment"].scheduled_start.hour < OPERATING_DAY_START
            or row["appointment"].scheduled_start.hour >= OPERATING_DAY_END
        )
    ]
    if not out_of_hours:
        return
    with st.expander("Citas fuera del horario visible"):
        for row in out_of_hours:
            _render_appointment_card(
                row["appointment"],
                row["patient"],
                service,
                row["appointment"].id in overlapping_ids,
            )


def _render_appointment_card(
    appointment: Appointment,
    patient: Patient | None,
    service: AppointmentService,
    has_overlap: bool,
) -> None:
    patient_name = _patient_name(patient)
    css_class = "appointment-card overlap" if has_overlap else "appointment-card"
    st.markdown(
        f"""
        <div class="{css_class}">
          <strong>{appointment.scheduled_start.strftime('%H:%M')} - {appointment.scheduled_end.strftime('%H:%M')}</strong>
          <span>{patient_name}</span><br>
          <small>{appointment.reason or 'Sin motivo'} | {appointment.clinic or 'Clinica sin asignar'} | {appointment.chair or 'Gabinete sin asignar'} | {appointment.status.value}</small>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander(f"Acciones {appointment.appointment_code}"):
        columns = st.columns(4)
        if columns[0].button("Completar", key=f"complete-{appointment.id}", disabled=appointment.status == AppointmentStatus.COMPLETED):
            service.complete_appointment(appointment.id)
            st.rerun()
        cancel_reason = columns[1].text_input("Motivo cancelacion", key=f"cancel-reason-{appointment.id}", label_visibility="collapsed")
        if columns[2].button("Cancelar", key=f"cancel-{appointment.id}", disabled=appointment.status == AppointmentStatus.CANCELLED):
            service.cancel_appointment(appointment.id, cancellation_reason=cancel_reason)
            st.rerun()
        if columns[3].button("Abrir paciente", key=f"open-patient-{appointment.id}", disabled=patient is None):
            st.session_state.selected_patient_id = str(patient.id)
            st.session_state.patient_quick_action = None
            st.session_state.section = "Pacientes"
            st.rerun()


def _render_monthly_agenda(rows: list[dict], selected_date: date) -> None:
    month_start = selected_date.replace(day=1)
    grid_start = month_start - timedelta(days=month_start.weekday())
    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1)
    grid_end = next_month + timedelta(days=(6 - next_month.weekday()))
    days = []
    current = grid_start
    while current <= grid_end:
        days.append(current)
        current += timedelta(days=1)

    rows_by_day: dict[date, list[dict]] = {}
    for row in rows:
        rows_by_day.setdefault(row["appointment"].scheduled_start.date(), []).append(row)

    st.caption("Selecciona un dia para abrir su semana en la agenda.")
    for week_start in range(0, len(days), 7):
        columns = st.columns(7)
        for index, day_value in enumerate(days[week_start : week_start + 7]):
            day_rows = rows_by_day.get(day_value, [])
            in_current_month = day_value.month == selected_date.month
            with columns[index]:
                css_class = "month-day" if in_current_month else "month-day muted"
                st.markdown(
                    f"<div class='{css_class}'><strong>{day_value.day}</strong><br><small>{_weekday_label(day_value)}</small></div>",
                    unsafe_allow_html=True,
                )
                for row in day_rows[:3]:
                    appointment = row["appointment"]
                    st.markdown(
                        f"<div class='month-appointment'>{appointment.scheduled_start.strftime('%H:%M')} {_patient_name(row['patient'])}</div>",
                        unsafe_allow_html=True,
                    )
                if len(day_rows) > 3:
                    st.caption(f"+{len(day_rows) - 3} mas")
                if st.button("Ver semana", key=f"month-week-{day_value.isoformat()}"):
                    _queue_agenda_navigation("Semanal", day_value)
                    st.rerun()


def _apply_pending_agenda_navigation() -> None:
    pending_view = st.session_state.get("pending_agenda_view")
    pending_date = st.session_state.get("pending_agenda_date")
    if pending_view is not None:
        st.session_state.agenda_view = pending_view
        st.session_state.pending_agenda_view = None
    if pending_date is not None:
        st.session_state.agenda_date = pending_date
        st.session_state.pending_agenda_date = None


def _queue_agenda_navigation(view_mode: str, selected_date: date) -> None:
    st.session_state.pending_agenda_view = view_mode
    st.session_state.pending_agenda_date = selected_date


def _render_patients() -> None:
    service = PatientService()
    st.subheader("Pacientes")
    search_text = st.text_input(
        "Buscar paciente",
        placeholder="Nombre, apellidos, telefono, email, codigo u observacion",
    )
    patients = service.search_patients(search_text, limit=100)

    if search_text.strip() and not patients:
        st.warning("No se encontraron pacientes con ese criterio.")
        with st.expander("Crear paciente con esta busqueda", expanded=True):
            _render_create_patient_form(
                service,
                search_text=search_text,
                form_key="quick_create_patient_form",
            )

    profile_tab, list_tab, create_tab = st.tabs(["Ficha", "Listado", "Alta"])
    with profile_tab:
        _render_patient_profile(service)
    with list_tab:
        _render_patient_list(patients)
    with create_tab:
        _render_create_patient_form(service, form_key="create_patient_form")


def _render_patient_list(patients: Iterable[Patient]) -> None:
    patients = list(patients)
    if not patients:
        st.info("No hay pacientes para mostrar.")
        return

    for patient in patients:
        columns = st.columns([4, 2, 1.4, 1, 1])
        columns[0].markdown(
            f"**{patient.last_name}, {patient.first_name}**  \n"
            f"<small>{patient.patient_code}</small>",
            unsafe_allow_html=True,
        )
        columns[1].write(patient.phone or "-")
        columns[2].write(patient.status.value)
        if columns[3].button("Abrir", key=f"patient-open-{patient.id}"):
            st.session_state.selected_patient_id = str(patient.id)
            st.session_state.patient_quick_action = None
            st.rerun()
        if columns[4].button("Editar", key=f"patient-edit-{patient.id}"):
            st.session_state.selected_patient_id = str(patient.id)
            st.session_state.patient_quick_action = "edit"
            st.rerun()


def _render_create_patient_form(
    service: PatientService,
    search_text: str = "",
    form_key: str = "create_patient_form",
) -> None:
    guessed_first_name, guessed_last_name = _guess_patient_name(search_text)
    with st.form(form_key, clear_on_submit=True):
        columns = st.columns(2)
        first_name = columns[0].text_input("Nombre", value=guessed_first_name, key=f"{form_key}_first_name")
        last_name = columns[1].text_input("Apellidos", value=guessed_last_name, key=f"{form_key}_last_name")
        columns = st.columns(2)
        phone = columns[0].text_input("Telefono", key=f"{form_key}_phone")
        email = columns[1].text_input("Email", key=f"{form_key}_email")
        columns = st.columns(2)
        status = columns[0].selectbox("Estado", [item.value for item in PatientStatus], key=f"{form_key}_status")
        has_birth_date = columns[1].checkbox("Registrar fecha de nacimiento", key=f"{form_key}_has_birth_date")
        birth_date_value = (
            st.date_input("Fecha de nacimiento", key=f"{form_key}_birth_date")
            if has_birth_date
            else None
        )
        tags = st.text_input("Etiquetas separadas por coma", key=f"{form_key}_tags")
        notes = st.text_area("Observaciones operativas", height=100, key=f"{form_key}_notes")
        submitted = st.form_submit_button("Crear paciente")

    if submitted:
        try:
            patient = service.create_patient(
                first_name,
                last_name,
                phone=phone,
                email=email,
                birth_date=_date_to_datetime(birth_date_value),
                status=PatientStatus(status),
                notes=notes,
                tags=[tag.strip() for tag in tags.split(",") if tag.strip()],
            )
            st.session_state.selected_patient_id = str(patient.id)
            st.session_state.patient_quick_action = None
            st.success("Paciente creado.")
            st.rerun()
        except (PatientServiceError, ValueError) as exc:
            st.error(str(exc))


def _render_patient_profile(service: PatientService) -> None:
    patient_id = st.session_state.selected_patient_id
    if patient_id is None:
        st.info("Selecciona un paciente desde el listado o desde una cita.")
        return

    profile = service.get_profile(patient_id)
    if profile is None:
        st.warning("Paciente no encontrado.")
        return

    patient = profile.patient
    st.markdown(f"### {patient.first_name} {patient.last_name}")
    columns = st.columns(5)
    columns[0].metric("Citas", profile.activity.appointments_count)
    columns[1].metric("Proximas", profile.activity.upcoming_appointments_count)
    columns[2].metric("Canceladas", profile.activity.cancelled_appointments_count)
    columns[3].metric("Tratamientos", profile.activity.treatments_count)
    columns[4].metric("Ultima actividad", _format_datetime(profile.activity.last_activity_at))

    quick = st.columns(3)
    if quick[0].button("Nueva cita"):
        st.session_state.selected_patient_id = str(patient.id)
        st.session_state.section = "Agenda"
        st.rerun()
    if quick[1].button("Registrar tratamiento"):
        st.session_state.selected_patient_id = str(patient.id)
        st.session_state.section = "Tratamientos"
        st.rerun()
    if quick[2].button("Editar paciente"):
        st.session_state.patient_quick_action = "edit"

    if st.session_state.patient_quick_action == "edit":
        with st.expander("Editar datos del paciente", expanded=True):
            _render_edit_patient_form(service, patient)

    summary_tab, appointments_tab, treatments_tab, events_tab = st.tabs(
        ["Resumen", "Citas", "Tratamientos", "Actividad"],
    )
    with summary_tab:
        _render_patient_summary(profile)
    with appointments_tab:
        _render_patient_appointments(profile.appointments)
    with treatments_tab:
        st.dataframe(_treatments_dataframe(profile.treatments), width="stretch", hide_index=True)
    with events_tab:
        st.dataframe(_events_dataframe(profile.treatment_events), width="stretch", hide_index=True)


def _render_patient_summary(profile) -> None:
    patient = profile.patient
    columns = st.columns(2)
    with columns[0]:
        st.write("Datos basicos")
        st.write(f"Codigo: `{patient.patient_code}`")
        st.write(f"Telefono: {patient.phone or '-'}")
        st.write(f"Email: {patient.email or '-'}")
        st.write(f"Estado: {patient.status.value}")
        st.write(f"Fecha nacimiento: {_format_datetime(patient.birth_date) if patient.birth_date else '-'}")
    with columns[1]:
        st.write("Observaciones operativas")
        st.info(patient.notes or "Sin observaciones operativas.")
        if patient.tags:
            st.caption("Etiquetas: " + ", ".join(patient.tags))


def _render_patient_appointments(appointments: list[Appointment]) -> None:
    if not appointments:
        st.info("El paciente no tiene citas registradas.")
        return

    upcoming = [item for item in appointments if item.status != AppointmentStatus.CANCELLED and item.scheduled_start >= datetime.now(tz=item.scheduled_start.tzinfo)]
    cancelled = [item for item in appointments if item.status == AppointmentStatus.CANCELLED]
    past = [item for item in appointments if item not in upcoming and item not in cancelled]

    upcoming_tab, past_tab, cancelled_tab = st.tabs(["Proximas", "Pasadas", "Canceladas"])
    upcoming_tab.dataframe(_appointments_dataframe(upcoming), width="stretch", hide_index=True)
    past_tab.dataframe(_appointments_dataframe(past), width="stretch", hide_index=True)
    cancelled_tab.dataframe(_appointments_dataframe(cancelled), width="stretch", hide_index=True)


def _render_edit_patient_form(service: PatientService, patient: Patient) -> None:
    with st.form(f"edit_patient_form_{patient.id}"):
        columns = st.columns(2)
        first_name = columns[0].text_input("Nombre", value=patient.first_name)
        last_name = columns[1].text_input("Apellidos", value=patient.last_name)
        columns = st.columns(2)
        phone = columns[0].text_input("Telefono", value=patient.phone or "")
        email = columns[1].text_input("Email", value=patient.email or "")
        columns = st.columns(2)
        status = columns[0].selectbox(
            "Estado",
            [item.value for item in PatientStatus],
            index=[item.value for item in PatientStatus].index(patient.status.value),
        )
        has_birth_date = columns[1].checkbox("Fecha de nacimiento registrada", value=patient.birth_date is not None)
        birth_date_value = (
            st.date_input("Fecha de nacimiento", value=patient.birth_date.date() if patient.birth_date else date.today())
            if has_birth_date
            else None
        )
        tags = st.text_input("Etiquetas separadas por coma", value=", ".join(patient.tags))
        notes = st.text_area("Observaciones operativas", value=patient.notes or "", height=100)
        submitted = st.form_submit_button("Guardar paciente")

    if submitted:
        try:
            service.update_patient(
                patient.id,
                {
                    "first_name": first_name,
                    "last_name": last_name,
                    "phone": phone,
                    "email": email,
                    "birth_date": _date_to_datetime(birth_date_value),
                    "status": PatientStatus(status),
                    "tags": [tag.strip() for tag in tags.split(",") if tag.strip()],
                    "notes": notes,
                },
            )
            st.session_state.patient_quick_action = None
            st.success("Paciente actualizado.")
            st.rerun()
        except (PatientServiceError, ValueError) as exc:
            st.error(str(exc))


def _guess_patient_name(search_text: str) -> tuple[str, str]:
    tokens = [token.strip() for token in search_text.split() if token.strip()]
    if not tokens:
        return "", ""
    if len(tokens) == 1:
        return tokens[0], ""
    return tokens[0], " ".join(tokens[1:])


def _date_to_datetime(value: date | None) -> datetime | None:
    return datetime.combine(value, time.min) if value else None


def _render_treatments(disabled: bool) -> None:
    if disabled:
        st.warning("El rol Auxiliar tiene acceso de consulta operativo. Cambia a Odontologo para modificar tratamientos.")
    service = TreatmentService()
    patient_service = PatientService()
    st.subheader("Tratamientos")

    catalog_tab, performed_tab, events_tab = st.tabs(["Catalogo", "Registrar realizado", "Realizados / eventos"])
    with catalog_tab:
        _render_treatment_catalog(service, disabled)
    with performed_tab:
        _render_register_performed_treatment(service, patient_service, disabled)
    with events_tab:
        _render_treatment_records(service, patient_service, disabled)


def _render_treatment_catalog(service: TreatmentService, disabled: bool) -> None:
    st.caption("Catalogo operativo: define tratamientos disponibles. No representa actividad realizada a pacientes.")
    columns = st.columns([3, 1])
    search_text = columns[0].text_input("Buscar en catalogo", placeholder="Nombre, categoria, codigo u observacion")
    include_inactive = columns[1].checkbox("Ver inactivos", value=True)
    catalog_items = service.search_catalog(search_text, include_inactive=include_inactive, limit=200)

    create_tab, edit_tab = st.tabs(["Alta catalogo", "Editar catalogo"])
    with create_tab:
        _render_create_catalog_item_form(service, disabled)
    with edit_tab:
        _render_edit_catalog_item_form(service, catalog_items, disabled)

    st.dataframe(_catalog_dataframe(catalog_items), width="stretch", hide_index=True)


def _render_create_catalog_item_form(service: TreatmentService, disabled: bool) -> None:
    with st.form("create_catalog_item_form", clear_on_submit=True):
        columns = st.columns(2)
        name = columns[0].text_input("Nombre", disabled=disabled)
        category = columns[1].text_input("Categoria", disabled=disabled)
        columns = st.columns(3)
        duration = columns[0].number_input("Duracion estandar min.", min_value=0, value=0, step=5, disabled=disabled)
        price = columns[1].number_input("Precio base", min_value=0.0, value=0.0, step=10.0, disabled=disabled)
        active = columns[2].checkbox("Activo", value=True, disabled=disabled)
        notes = st.text_area("Observaciones operativas", height=80, disabled=disabled)
        submitted = st.form_submit_button("Crear en catalogo", disabled=disabled)

    if submitted:
        try:
            service.create_catalog_item(
                name=name,
                category=category,
                default_duration_minutes=duration or None,
                base_price=price or None,
                active=active,
                notes=notes,
            )
            st.success("Tratamiento de catalogo creado.")
            st.rerun()
        except (TreatmentServiceError, ValueError) as exc:
            st.error(str(exc))


def _render_edit_catalog_item_form(service: TreatmentService, catalog_items: list, disabled: bool) -> None:
    if not catalog_items:
        st.info("No hay tratamientos de catalogo para editar.")
        return

    options = {f"{item.name} ({item.catalog_code})": item for item in catalog_items}
    selected_label = st.selectbox("Tratamiento de catalogo", list(options), disabled=disabled)
    selected = options[selected_label]
    with st.form(f"edit_catalog_item_form_{selected.id}"):
        columns = st.columns(2)
        name = columns[0].text_input("Nombre", value=selected.name, disabled=disabled)
        category = columns[1].text_input("Categoria", value=selected.category or "", disabled=disabled)
        columns = st.columns(3)
        duration = columns[0].number_input(
            "Duracion estandar min.",
            min_value=0,
            value=selected.default_duration_minutes or 0,
            step=5,
            disabled=disabled,
        )
        price = columns[1].number_input(
            "Precio base",
            min_value=0.0,
            value=selected.base_price or 0.0,
            step=10.0,
            disabled=disabled,
        )
        active = columns[2].checkbox("Activo", value=selected.active, disabled=disabled)
        notes = st.text_area("Observaciones operativas", value=selected.notes or "", height=80, disabled=disabled)
        submitted = st.form_submit_button("Guardar catalogo", disabled=disabled)

    if submitted:
        try:
            service.update_catalog_item(
                selected.id,
                {
                    "name": name,
                    "category": category,
                    "default_duration_minutes": duration or None,
                    "base_price": price or None,
                    "active": active,
                    "notes": notes,
                },
            )
            st.success("Tratamiento de catalogo actualizado.")
            st.rerun()
        except (TreatmentServiceError, ValueError) as exc:
            st.error(str(exc))


def _render_register_performed_treatment(
    service: TreatmentService,
    patient_service: PatientService,
    disabled: bool,
) -> None:
    st.caption("Registra actividad realizada a un paciente. No es obligatorio al completar una cita.")
    patients = patient_service.search_patients("", limit=200)
    catalog_items = service.search_catalog("", include_inactive=False, limit=200)
    if not patients:
        st.info("No hay pacientes disponibles.")
        return
    if not catalog_items:
        st.info("No hay tratamientos activos en catalogo. Crea primero un tratamiento de catalogo.")
        return

    patient_options = {f"{patient.last_name}, {patient.first_name} ({patient.patient_code})": patient for patient in patients}
    default_patient_label = next(iter(patient_options))
    selected_patient_id = st.session_state.selected_patient_id
    if selected_patient_id:
        for label, patient in patient_options.items():
            if str(patient.id) == selected_patient_id:
                default_patient_label = label
                break

    catalog_options = {f"{item.name} ({item.category or 'Sin categoria'})": item for item in catalog_items}
    with st.form("register_performed_treatment_form", clear_on_submit=True):
        patient_label = st.selectbox(
            "Paciente",
            list(patient_options),
            index=list(patient_options).index(default_patient_label),
            disabled=disabled,
        )
        selected_patient = patient_options[patient_label]
        appointment_options = {"Sin cita asociada": None}
        for appointment in service.list_patient_appointments(selected_patient.id, limit=50):
            appointment_options[
                f"{appointment.scheduled_start.strftime('%Y-%m-%d %H:%M')} - {appointment.reason or appointment.appointment_code}"
            ] = appointment

        columns = st.columns(3)
        catalog_label = columns[0].selectbox("Tratamiento", list(catalog_options), disabled=disabled)
        event_date = columns[1].date_input("Fecha realizada", value=date.today(), disabled=disabled)
        appointment_label = columns[2].selectbox("Cita asociada", list(appointment_options), disabled=disabled)
        notes = st.text_area("Observacion operativa", height=90, disabled=disabled)
        submitted = st.form_submit_button("Registrar realizado", disabled=disabled)

    if submitted:
        try:
            selected_catalog = catalog_options[catalog_label]
            selected_appointment = appointment_options[appointment_label]
            service.register_performed_treatment(
                patient_id=selected_patient.id,
                catalog_item_id=selected_catalog.id,
                event_date=datetime.combine(event_date, time(9, 0)),
                appointment_id=selected_appointment.id if selected_appointment else None,
                notes=notes,
                created_by=st.session_state.role,
            )
            st.success("Tratamiento realizado registrado.")
            st.rerun()
        except (TreatmentServiceError, ValueError) as exc:
            st.error(str(exc))


def _render_treatment_records(
    service: TreatmentService,
    patient_service: PatientService,
    disabled: bool,
) -> None:
    patients = patient_service.search_patients("", limit=200)
    patient_options = {"Todos": None}
    patient_options.update({f"{patient.last_name}, {patient.first_name} ({patient.patient_code})": patient for patient in patients})
    columns = st.columns([2, 2, 1, 1])
    patient_label = columns[0].selectbox("Filtrar por paciente", list(patient_options), disabled=disabled)
    treatment_query = columns[1].text_input("Filtrar tratamiento", disabled=disabled)
    start_date = columns[2].date_input("Desde", value=date.today() - timedelta(days=90), disabled=disabled)
    limit = columns[3].number_input("Max.", min_value=10, max_value=300, value=100, step=10, disabled=disabled)
    end_date = date.today() + timedelta(days=1)

    selected_patient = patient_options[patient_label]
    patient_id = selected_patient.id if selected_patient else None
    event_records = service.list_events(
        patient_id=patient_id,
        treatment_query=treatment_query,
        start_date=datetime.combine(start_date, time.min),
        end_date=datetime.combine(end_date, time.min),
        limit=int(limit),
    )
    treatment_records = service.list_treatment_records(
        patient_id=patient_id,
        treatment_query=treatment_query,
        start_date=datetime.combine(start_date, time.min),
        end_date=datetime.combine(end_date, time.min),
        limit=int(limit),
    )

    records_tab, events_tab = st.tabs(["Tratamientos realizados", "Eventos"])
    records_tab.dataframe(_treatment_records_dataframe(treatment_records), width="stretch", hide_index=True)
    events_tab.dataframe(_treatment_event_records_dataframe(event_records), width="stretch", hide_index=True)


def _render_analytics(disabled: bool) -> None:
    if disabled:
        st.warning("Analitica disponible para rol Odontologo o Admin.")
        return

    service = AnalyticsService()
    st.subheader("Analitica operativa")

    filter_columns = st.columns([1.4, 1, 1, 1, 1])
    period = filter_columns[0].selectbox(
        "Periodo",
        ["Semana actual", "Mes actual", "Ultimos 30 dias", "Ultimos 90 dias", "Personalizado"],
    )
    start_date, end_date = _analytics_period_window(period)
    if period == "Personalizado":
        range_columns = st.columns(2)
        start_date = range_columns[0].date_input("Desde", value=start_date)
        end_date = range_columns[1].date_input("Hasta", value=end_date)
        if end_date < start_date:
            st.error("La fecha final no puede ser anterior a la inicial.")
            return

    clinic_label = filter_columns[1].selectbox("Clinica", ["Todas", *CLINICS])
    chair_label = filter_columns[2].selectbox("Gabinete", ["Todos", *CHAIRS])
    professional_label = filter_columns[3].selectbox("Profesional", ["Todos", *PROFESSIONALS])
    status_label = filter_columns[4].selectbox("Estado", ["Todos", *[item.value for item in AppointmentStatus]])

    summary = service.summary(
        datetime.combine(start_date, time.min),
        datetime.combine(end_date + timedelta(days=1), time.min),
        filters=AnalyticsFilters(
            clinic=None if clinic_label == "Todas" else clinic_label,
            chair=None if chair_label == "Todos" else chair_label,
            professional=None if professional_label == "Todos" else professional_label,
            status=None if status_label == "Todos" else AppointmentStatus(status_label),
        ),
    )

    st.caption(
        f"Periodo analizado: {summary.start_date.date().isoformat()} - "
        f"{(summary.end_date - timedelta(days=1)).date().isoformat()}"
    )
    kpi_columns = st.columns(6)
    kpi_columns[0].metric("Citas", summary.total_appointments)
    kpi_columns[1].metric("Completadas", summary.completed_appointments, f"{summary.completion_rate:.0%}")
    kpi_columns[2].metric("Canceladas", summary.cancelled_appointments, f"{summary.cancellation_rate:.0%}")
    kpi_columns[3].metric("No asistencias", summary.no_show_appointments, f"{summary.no_show_rate:.0%}")
    occupation_label = "Sin base" if summary.occupation_rate is None else f"{summary.occupation_rate:.0%}"
    kpi_columns[4].metric("Ocupacion", occupation_label)
    kpi_columns[5].metric("Pacientes con actividad", summary.patients_with_recent_activity)

    st.caption(summary.occupation_basis)

    appointments_by_day_df = pd.DataFrame(summary.appointments_by_day)
    status_df = pd.DataFrame(summary.appointments_by_status)
    clinic_df = pd.DataFrame(summary.usage_by_clinic)
    chair_df = pd.DataFrame(summary.usage_by_chair)
    professional_df = pd.DataFrame(summary.usage_by_professional)
    treatments_df = pd.DataFrame(summary.frequent_treatments)
    evolution_df = pd.DataFrame(summary.treatment_evolution)

    agenda_tab, occupation_tab, treatments_tab, patients_tab, detail_tab = st.tabs(
        ["Citas", "Ocupacion", "Tratamientos", "Pacientes", "Detalle"]
    )

    with agenda_tab:
        chart_columns = st.columns(2)
        if appointments_by_day_df.empty:
            chart_columns[0].info("No hay citas en el periodo seleccionado.")
        else:
            chart_columns[0].plotly_chart(
                px.bar(appointments_by_day_df, x="date", y="appointments", title="Citas por dia"),
                use_container_width=True,
            )
        if status_df.empty:
            chart_columns[1].info("No hay estados de cita para mostrar.")
        else:
            chart_columns[1].plotly_chart(
                px.bar(status_df, x="status", y="count", title="Citas por estado"),
                use_container_width=True,
            )

    with occupation_tab:
        st.metric("Minutos ocupados", summary.occupied_minutes)
        st.metric("Minutos disponibles estimados", summary.available_minutes)
        usage_columns = st.columns(3)
        _render_usage_chart(usage_columns[0], clinic_df, "clinic", "Uso por clinica")
        _render_usage_chart(usage_columns[1], chair_df, "chair", "Uso por gabinete")
        _render_usage_chart(usage_columns[2], professional_df, "professional", "Uso por profesional")

    with treatments_tab:
        if treatments_df.empty:
            st.info("No hay tratamientos realizados completados en el periodo. No se usa el catalogo como actividad real.")
        else:
            st.plotly_chart(
                px.bar(treatments_df, x="treatment_type", y="count", title="Tratamientos realizados frecuentes"),
                use_container_width=True,
            )
        if evolution_df.empty:
            st.info("No hay eventos de tratamiento para evolucion temporal.")
        else:
            st.plotly_chart(
                px.line(evolution_df, x="date", y="events", title="Evolucion de eventos de tratamiento"),
                use_container_width=True,
            )

    with patients_tab:
        patient_rows = pd.DataFrame(
            [
                {"indicador": "Pacientes con actividad en periodo", "valor": summary.patients_with_recent_activity},
                {
                    "indicador": f"Pacientes sin actividad en {summary.recent_activity_days} dias",
                    "valor": summary.patients_without_recent_activity,
                },
                {"indicador": "Pacientes con proxima cita", "valor": summary.patients_with_upcoming_appointment},
            ]
        )
        st.dataframe(patient_rows, width="stretch", hide_index=True)
        st.caption("No se muestra ranking de pacientes para evitar exponer datos personales en analitica agregada.")

    with detail_tab:
        detail_df = pd.DataFrame(summary.detail_rows)
        if detail_df.empty:
            st.info("No hay detalle de citas para el periodo seleccionado.")
        else:
            st.dataframe(detail_df, width="stretch", hide_index=True)


def _analytics_period_window(period: str) -> tuple[date, date]:
    today = date.today()
    if period == "Mes actual":
        start = today.replace(day=1)
        if start.month == 12:
            next_month = start.replace(year=start.year + 1, month=1)
        else:
            next_month = start.replace(month=start.month + 1)
        return start, next_month - timedelta(days=1)
    if period == "Ultimos 30 dias":
        return today - timedelta(days=29), today
    if period == "Ultimos 90 dias":
        return today - timedelta(days=89), today
    if period == "Personalizado":
        return today - timedelta(days=6), today
    start = today - timedelta(days=today.weekday())
    return start, start + timedelta(days=6)


def _render_usage_chart(container, dataframe: pd.DataFrame, field_name: str, title: str) -> None:
    if dataframe.empty:
        container.info(f"Sin datos para {title.lower()}.")
        return
    container.plotly_chart(
        px.bar(dataframe, x=field_name, y="minutes", title=title),
        use_container_width=True,
    )


def _render_stock() -> None:
    st.subheader("Stock")
    st.info("Modulo visible para la navegacion futura. Proximamente: materiales, niveles minimos y alertas.")


def _render_configuration(disabled: bool) -> None:
    st.subheader("Configuracion")
    if disabled:
        st.warning("Solo Odontologo o Admin pueden modificar configuracion operativa.")
    st.write("Parametros operativos actuales")
    st.table(
        {
            "Parametro": ["Clinicas", "Gabinetes por clinica", "Profesionales", "Duracion estandar", "Estados de cita"],
            "Valor": [
                ", ".join(CLINICS),
                ", ".join(CHAIRS),
                ", ".join(PROFESSIONALS),
                f"{DEFAULT_APPOINTMENT_MINUTES} min",
                ", ".join(item.value for item in AppointmentStatus),
            ],
        }
    )
    st.caption("En esta fase la configuracion se mantiene local en codigo para evitar complejidad prematura. El siguiente paso natural es persistirla en una coleccion operational_settings.")


def _render_admin() -> None:
    st.subheader("Admin")
    if st.session_state.role != "Admin":
        st.warning("Selecciona rol Admin para acceder a la administracion tecnica.")
        return

    expected_pin = getenv("DENTAL_ADMIN_PIN", "admin")
    pin = st.text_input("PIN local de administrador", type="password")
    if pin != expected_pin:
        st.info("Login local simple para MVP. Evolucion prevista: autenticacion robusta y permisos persistentes.")
        return

    status = AdminService().get_system_status()
    columns = st.columns(4)
    columns[0].metric("Conexion MongoDB", "OK" if status.database.connected else "Error")
    columns[1].metric("Base activa", status.database.database_name)
    columns[2].metric("Modo demo", "Si" if status.demo_mode else "No")
    columns[3].metric("Ultima copia", status.last_backup)

    st.write("Documentos por coleccion")
    st.dataframe(
        pd.DataFrame(
            [{"collection": collection, "documents": count} for collection, count in status.document_counts.items()]
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.write("Zona tecnica")
    st.info("Herramientas destructivas no se ejecutan desde esta pantalla sin confirmacion explicita futura.")
    st.checkbox("Preparado para revisar indices")
    st.checkbox("Preparado para diagnostico de datos")
    st.checkbox("Preparado para mantenimiento controlado")


def _date_window(view_mode: str, selected_date: date) -> tuple[datetime, datetime]:
    if view_mode == "Semanal":
        start = selected_date - timedelta(days=selected_date.weekday())
        end = start + timedelta(days=7)
    elif view_mode == "Mensual":
        start = selected_date.replace(day=1)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
    else:
        start = selected_date
        end = selected_date + timedelta(days=1)
    return datetime.combine(start, time.min), datetime.combine(end, time.min)


def _overlapping_ids(appointments: list[Appointment]) -> set:
    overlapping = set()
    sorted_items = sorted(appointments, key=lambda item: item.scheduled_start)
    for index, appointment in enumerate(sorted_items):
        for candidate in sorted_items[index + 1 :]:
            if candidate.scheduled_start >= appointment.scheduled_end:
                break
            overlapping.add(appointment.id)
            overlapping.add(candidate.id)
    return overlapping


def _appointments_dataframe(appointments: list[Appointment]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "codigo": item.appointment_code,
                "inicio": _format_datetime(item.scheduled_start),
                "fin": _format_datetime(item.scheduled_end),
                "estado": item.status.value,
                "motivo": item.reason,
                "clinica": item.clinic,
                "gabinete": item.chair,
                "profesional": item.professional,
            }
            for item in appointments
        ]
    )


def _catalog_dataframe(catalog_items: list) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "codigo": item.catalog_code,
                "nombre": item.name,
                "categoria": item.category,
                "duracion_min": item.default_duration_minutes,
                "precio_base": item.base_price,
                "activo": "si" if item.active else "no",
            }
            for item in catalog_items
        ]
    )


def _treatment_records_dataframe(records: list) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "fecha": _format_datetime(record.treatment.planned_date or record.treatment.created_at),
                "paciente": _patient_name(record.patient),
                "tratamiento": record.treatment.treatment_type,
                "estado": record.treatment.status.value,
                "cita": record.appointment.appointment_code if record.appointment else "-",
                "ultimo_evento": record.latest_event.event_type.value if record.latest_event else "-",
                "observacion": record.treatment.notes or record.treatment.description,
            }
            for record in records
        ]
    )


def _treatment_event_records_dataframe(records: list) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "fecha": _format_datetime(record.event.event_date),
                "paciente": _patient_name(record.patient),
                "tratamiento": record.treatment.treatment_type if record.treatment else "-",
                "evento": record.event.event_type.value,
                "estado_nuevo": record.event.new_status.value if record.event.new_status else "-",
                "cita": record.appointment.appointment_code if record.appointment else "-",
                "observacion": record.event.description,
            }
            for record in records
        ]
    )


def _treatments_dataframe(treatments: list) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "codigo": item.treatment_code,
                "tipo": item.treatment_type,
                "estado": item.status.value,
                "planificado": _format_datetime(item.planned_date),
                "precio_estimado": item.estimated_price,
                "precio_final": item.final_price,
                "notas": item.notes,
            }
            for item in treatments
        ]
    )


def _events_dataframe(events: list) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "fecha": _format_datetime(item.event_date),
                "evento": item.event_type.value,
                "estado_anterior": item.previous_status.value if item.previous_status else None,
                "estado_nuevo": item.new_status.value if item.new_status else None,
                "descripcion": item.description,
                "usuario": item.created_by,
            }
            for item in events
        ]
    )


def _patient_name(patient: Patient | None) -> str:
    if patient is None:
        return "Paciente no encontrado"
    return f"{patient.first_name} {patient.last_name}"


def _weekday_label(value: date) -> str:
    labels = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]
    return labels[value.weekday()]


def _format_datetime(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M") if value else "-"


def _load_styles() -> None:
    st.markdown(
        """
        <style>
        .calendar-shell {
            width: 100%;
        }
        .calendar-hour {
            min-height: 3.2rem;
            padding-top: 0.35rem;
            color: #667085;
            font-size: 0.86rem;
            border-top: 1px solid #eaecf0;
        }
        .appointment-card {
            border-left: 4px solid #2f80ed;
            background: #f7fbff;
            padding: 0.45rem 0.55rem;
            margin: 0.15rem 0 0.35rem 0;
            border-radius: 6px;
            min-height: 3rem;
            box-shadow: inset 0 0 0 1px rgba(47, 128, 237, 0.08);
        }
        .appointment-card span {
            display: block;
            margin-top: 0.15rem;
        }
        .appointment-card.overlap {
            border-left-color: #d97706;
            background: #fff7ed;
        }
        .empty-slot {
            min-height: 3.2rem;
            border-top: 1px solid #edf2f7;
        }
        .month-day {
            min-height: 4.5rem;
            padding: 0.45rem;
            margin-bottom: 0.25rem;
            border: 1px solid #eaecf0;
            border-radius: 6px;
            background: #ffffff;
        }
        .month-day.muted {
            color: #98a2b3;
            background: #f9fafb;
        }
        .month-appointment {
            border-radius: 4px;
            background: #eff8ff;
            color: #175cd3;
            font-size: 0.78rem;
            margin: 0.12rem 0;
            padding: 0.12rem 0.25rem;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
