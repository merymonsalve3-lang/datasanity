import streamlit as st


pages = [
    st.Page("pages/00_Auditoria_de_datos.py", title="Auditoría de datos"),
    st.Page("pages/01_Buscador_de_duplicados.py", title="Buscador de duplicados"),
    st.Page("pages/02_Generador_dashboard.py", title="Generador dashboard"),
]

navigation = st.navigation(pages)
navigation.run()
