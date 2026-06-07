import streamlit as st

from src.database.connection import get_database
from src.integrations.export_engine import ExportEngine
from src.integrations.import_engine import ImportEngine
from src.repositories.appointment_repository import AppointmentRepository
from src.repositories.patient_repository import PatientRepository
from src.services.database_status_service import DatabaseStatusService


st.set_page_config(
    page_title="Dental CRM MVP",
    page_icon="Dental",
    layout="wide",
)

st.title("Dental CRM MVP")
st.caption("Validacion de arranque robusto: Streamlit + MongoDB + Docker.")

status = DatabaseStatusService().get_status()

st.subheader("MongoDB")
st.write(f"Active database: `{status.database_name}`")

if status.connected:
    st.success("Sistema disponible. Conexion correcta con MongoDB.")
    if status.collections:
        st.write("Collections:")
        st.table({"name": status.collections})
    else:
        st.info("Connected. The active database does not have collections yet.")
else:
    st.error("MongoDB no esta disponible actualmente.")
    st.info(
        "El contenedor puede estar reiniciandose o MongoDB puede estar inicializando. "
        "Revisa los logs si el problema persiste."
    )
    st.code(status.error or "Unknown connection error")


st.divider()
st.subheader("Importar / Exportar datos")

if not status.connected:
    st.info("La importacion y exportacion requieren conexion activa con MongoDB.")
else:
    database = get_database()
    patient_repository = PatientRepository(database)
    appointment_repository = AppointmentRepository(database)
    import_engine = ImportEngine()
    export_engine = ExportEngine()

    import_tab, export_tab = st.tabs(["Importar demo", "Exportar"])

    with import_tab:
        entity = st.selectbox("Entidad", ["patients", "appointments"], key="import_entity")
        uploaded_file = st.file_uploader(
            "Archivo CSV o JSON demo",
            type=["csv", "json"],
            key="import_file",
        )

        if st.button("Ejecutar importacion", disabled=uploaded_file is None):
            source_format = uploaded_file.name.rsplit(".", 1)[-1].lower()
            repository = patient_repository if entity == "patients" else appointment_repository
            related_repositories = {"patients": patient_repository} if entity == "appointments" else None

            summary = import_engine.import_data(
                entity=entity,
                source_format=source_format,
                source=uploaded_file,
                repository=repository,
                related_repositories=related_repositories,
            )
            st.json(summary.to_dict())

    with export_tab:
        export_entity = st.selectbox("Entidad a exportar", ["patients", "appointments", "metrics"])
        export_format = st.selectbox("Formato", ["json", "csv"])

        if st.button("Ejecutar exportacion"):
            summary = export_engine.export_data(
                entity=export_entity,
                export_format=export_format,
                repositories={
                    "patients": patient_repository,
                    "appointments": appointment_repository,
                },
            )
            if summary.errors:
                st.error("La exportacion no se pudo completar.")
            else:
                st.success(f"Exportacion generada: {summary.file_path}")
            st.json(summary.to_dict())
