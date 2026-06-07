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
from src.services.analytics_service import AnalyticsService
from src.services.appointment_service import AgendaFilters, AppointmentService
from src.services.database_status_service import DatabaseStatusService
from src.services.patient_service import PatientService
from src.services.treatment_service import TreatmentService


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
    view_mode, selected_date, filters = _agenda_controls()
    start_date, end_date = _date_window(view_mode, selected_date)
    rows = service.list_with_patients(start_date, end_date, filters)

    create_tab, view_tab = st.tabs(["Crear cita", f"Vista {view_mode.lower()}"])
    with create_tab:
        _render_create_appointment_form(service, patient_service, selected_date)

    with view_tab:
        if view_mode == "Diaria":
            _render_daily_agenda(rows, service)
        else:
            _render_period_agenda(rows, view_mode)


def _agenda_controls() -> tuple[str, date, AgendaFilters]:
    columns = st.columns([1, 1, 1, 1, 1])
    with columns[0]:
        view_mode = st.radio("Vista", ["Diaria", "Semanal", "Mensual"], horizontal=True)
    with columns[1]:
        selected_date = st.date_input("Fecha", value=date.today())
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

    with st.form("create_appointment_form", clear_on_submit=True):
        columns = st.columns(3)
        patient_label = columns[0].selectbox("Paciente", list(patient_options))
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


def _render_daily_agenda(rows: list[dict], service: AppointmentService) -> None:
    appointments = [row["appointment"] for row in rows]
    overlapping_ids = _overlapping_ids(appointments)

    if not rows:
        st.info("No hay citas para los filtros seleccionados.")
        return

    for hour in range(OPERATING_DAY_START, OPERATING_DAY_END):
        hour_rows = [
            row
            for row in rows
            if row["appointment"].scheduled_start.hour == hour
        ]
        with st.container():
            hour_column, content_column = st.columns([1, 6])
            hour_column.markdown(f"**{hour:02d}:00**")
            if not hour_rows:
                content_column.markdown("<div class='empty-slot'></div>", unsafe_allow_html=True)
                continue
            with content_column:
                for row in hour_rows:
                    _render_appointment_card(row["appointment"], row["patient"], service, row["appointment"].id in overlapping_ids)


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
            st.session_state.section = "Pacientes"
            st.rerun()


def _render_period_agenda(rows: list[dict], view_mode: str) -> None:
    if not rows:
        st.info("No hay citas para el periodo seleccionado.")
        return

    data = [
        {
            "fecha": row["appointment"].scheduled_start.date().isoformat(),
            "hora": row["appointment"].scheduled_start.strftime("%H:%M"),
            "paciente": _patient_name(row["patient"]),
            "motivo": row["appointment"].reason,
            "clinica": row["appointment"].clinic,
            "gabinete": row["appointment"].chair,
            "profesional": row["appointment"].professional,
            "estado": row["appointment"].status.value,
        }
        for row in rows
    ]
    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
    chart_data = pd.DataFrame(data).groupby(["fecha", "estado"]).size().reset_index(name="citas")
    st.plotly_chart(px.bar(chart_data, x="fecha", y="citas", color="estado", title=f"Citas - vista {view_mode.lower()}"), use_container_width=True)


def _render_patients() -> None:
    service = PatientService()
    st.subheader("Pacientes")
    search_text = st.text_input("Buscar por nombre, apellidos o telefono")
    patients = service.search_patients(search_text, limit=100)

    list_tab, create_tab, detail_tab = st.tabs(["Listado", "Alta", "Ficha"])
    with list_tab:
        _render_patient_list(patients)
    with create_tab:
        _render_create_patient_form(service)
    with detail_tab:
        _render_patient_profile(service)


def _render_patient_list(patients: Iterable[Patient]) -> None:
    for patient in patients:
        columns = st.columns([4, 2, 2, 1])
        columns[0].markdown(f"**{patient.last_name}, {patient.first_name}**")
        columns[1].write(patient.phone or "-")
        columns[2].write(patient.status.value)
        if columns[3].button("Abrir", key=f"patient-open-{patient.id}"):
            st.session_state.selected_patient_id = str(patient.id)
            st.rerun()


def _render_create_patient_form(service: PatientService) -> None:
    with st.form("create_patient_form", clear_on_submit=True):
        columns = st.columns(2)
        first_name = columns[0].text_input("Nombre")
        last_name = columns[1].text_input("Apellidos")
        columns = st.columns(2)
        phone = columns[0].text_input("Telefono")
        email = columns[1].text_input("Email")
        tags = st.text_input("Etiquetas separadas por coma")
        notes = st.text_area("Observaciones operativas", height=100)
        submitted = st.form_submit_button("Crear paciente")

    if submitted:
        if not first_name.strip() or not last_name.strip():
            st.error("Nombre y apellidos son obligatorios.")
            return
        patient = service.create_patient(
            first_name,
            last_name,
            phone=phone,
            email=email,
            notes=notes,
            tags=[tag.strip() for tag in tags.split(",") if tag.strip()],
        )
        st.session_state.selected_patient_id = str(patient.id)
        st.success("Paciente creado.")


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
    columns = st.columns(4)
    columns[0].metric("Citas", profile.activity.appointments_count)
    columns[1].metric("Tratamientos", profile.activity.treatments_count)
    columns[2].metric("Ultima cita", _format_datetime(profile.activity.last_appointment_at))
    columns[3].metric("Proxima cita", _format_datetime(profile.activity.next_appointment_at))

    quick = st.columns(3)
    if quick[0].button("Crear cita para paciente"):
        st.session_state.section = "Agenda"
        st.rerun()
    if quick[1].button("Registrar tratamiento"):
        st.session_state.section = "Tratamientos"
        st.rerun()

    with st.expander("Editar datos basicos"):
        status_value = st.selectbox("Estado", [item.value for item in PatientStatus], index=[item.value for item in PatientStatus].index(patient.status.value))
        notes = st.text_area("Observaciones", value=patient.notes or "")
        if st.button("Guardar cambios paciente"):
            service.update_patient(patient.id, {"status": PatientStatus(status_value), "notes": notes or None})
            st.success("Paciente actualizado.")
            st.rerun()

    appointments_tab, treatments_tab, events_tab = st.tabs(["Historico citas", "Historico tratamientos", "Actividad"])
    appointments_tab.dataframe(_appointments_dataframe(profile.appointments), use_container_width=True, hide_index=True)
    treatments_tab.dataframe(_treatments_dataframe(profile.treatments), use_container_width=True, hide_index=True)
    events_tab.dataframe(_events_dataframe(profile.treatment_events), use_container_width=True, hide_index=True)


def _render_treatments(disabled: bool) -> None:
    if disabled:
        st.warning("El rol Auxiliar tiene acceso de consulta operativo. Cambia a Odontologo para modificar tratamientos.")
    service = TreatmentService()
    patient_service = PatientService()
    st.subheader("Tratamientos")

    create_tab, catalog_tab = st.tabs(["Registrar tratamiento", "Consulta / catalogo"])
    with create_tab:
        _render_create_treatment_form(service, patient_service, disabled)
    with catalog_tab:
        treatments = service.list_treatments(limit=200)
        st.dataframe(_treatments_dataframe(treatments), use_container_width=True, hide_index=True)

        selected = st.selectbox("Actualizar estado", ["Selecciona", *[item.treatment_code for item in treatments]], disabled=disabled)
        if selected != "Selecciona":
            treatment = next(item for item in treatments if item.treatment_code == selected)
            status = st.selectbox("Nuevo estado", [item.value for item in TreatmentStatus])
            note = st.text_input("Nota de cambio")
            if st.button("Guardar estado", disabled=disabled):
                service.update_status(treatment.id, TreatmentStatus(status), description=note, created_by=st.session_state.role)
                st.success("Tratamiento actualizado.")
                st.rerun()


def _render_create_treatment_form(
    service: TreatmentService,
    patient_service: PatientService,
    disabled: bool,
) -> None:
    patients = patient_service.search_patients("", limit=200)
    options = {f"{patient.last_name}, {patient.first_name} ({patient.patient_code})": patient for patient in patients}
    if not options:
        st.info("No hay pacientes disponibles.")
        return

    default_label = next(iter(options))
    selected_patient_id = st.session_state.selected_patient_id
    if selected_patient_id:
        for label, patient in options.items():
            if str(patient.id) == selected_patient_id:
                default_label = label
                break

    with st.form("create_treatment_form", clear_on_submit=True):
        patient_label = st.selectbox("Paciente", list(options), index=list(options).index(default_label), disabled=disabled)
        columns = st.columns(3)
        treatment_type = columns[0].text_input("Tipo tratamiento", disabled=disabled)
        planned_date = columns[1].date_input("Fecha planificada", value=date.today(), disabled=disabled)
        estimated_price = columns[2].number_input("Precio estimado", min_value=0.0, value=0.0, step=10.0, disabled=disabled)
        description = st.text_area("Descripcion", disabled=disabled)
        notes = st.text_area("Notas", disabled=disabled)
        submitted = st.form_submit_button("Registrar tratamiento", disabled=disabled)

    if submitted:
        if not treatment_type.strip():
            st.error("El tipo de tratamiento es obligatorio.")
            return
        service.create_treatment(
            options[patient_label].id,
            treatment_type,
            description=description,
            planned_date=datetime.combine(planned_date, time(9, 0)),
            estimated_price=estimated_price or None,
            notes=notes,
            created_by=st.session_state.role,
        )
        st.success("Tratamiento registrado.")


def _render_analytics(disabled: bool) -> None:
    if disabled:
        st.warning("Analitica disponible para rol Odontologo o Admin.")
        return

    service = AnalyticsService()
    st.subheader("Analitica semanal")
    reference_date = st.date_input("Semana de referencia", value=date.today())
    summary = service.weekly_summary(datetime.combine(reference_date, time(12, 0)))

    columns = st.columns(3)
    columns[0].metric("Pacientes activos", summary.active_patients)
    columns[1].metric("Cancelaciones", summary.cancellations)
    columns[2].metric("Periodo", f"{summary.start_date.date()} / {summary.end_date.date()}")

    status_df = pd.DataFrame(summary.appointments_by_status)
    occupation_df = pd.DataFrame(summary.occupation)
    treatments_df = pd.DataFrame(summary.frequent_treatments)
    evolution_df = pd.DataFrame(summary.treatment_evolution)

    if not status_df.empty:
        st.plotly_chart(px.bar(status_df, x="status", y="count", title="Citas por estado"), use_container_width=True)
    if not occupation_df.empty:
        st.plotly_chart(px.bar(occupation_df, x="date", y="minutes", color="status", title="Ocupacion por dia"), use_container_width=True)
    if not treatments_df.empty:
        st.plotly_chart(px.bar(treatments_df, x="treatment_type", y="count", title="Tratamientos frecuentes"), use_container_width=True)
    if not evolution_df.empty:
        st.plotly_chart(px.line(evolution_df, x="date", y="count", color="event_type", title="Evolucion temporal"), use_container_width=True)

    st.dataframe(status_df, use_container_width=True, hide_index=True)


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


def _format_datetime(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M") if value else "-"


def _load_styles() -> None:
    st.markdown(
        """
        <style>
        .appointment-card {
            border-left: 4px solid #2f80ed;
            background: #f7fbff;
            padding: 0.55rem 0.75rem;
            margin: 0.15rem 0 0.35rem 0;
            border-radius: 6px;
        }
        .appointment-card span {
            margin-left: 0.5rem;
        }
        .appointment-card.overlap {
            border-left-color: #d97706;
            background: #fff7ed;
        }
        .empty-slot {
            min-height: 1.75rem;
            border-top: 1px solid #edf2f7;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
