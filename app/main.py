import streamlit as st

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
