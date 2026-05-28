import pandas as pd
import streamlit as st

from generador_dashboard import analizar_dashboard, exportar_dashboard_excel, leer_archivo


st.set_page_config(
    page_title="DataSanity - Dashboard Generator",
    layout="wide",
)

st.markdown(
    """
    <style>

        .stApp {
            background: #f1faf6;
        }
        [data-testid="stAppViewContainer"] {
            background: #f1faf6;
        }
        .main {
            background: #f1faf6;
        }
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1280px;
        }
        .ds-hero {
            border: 1px solid #e6eaf0;
            border-radius: 10px;
            padding: 24px 26px;
            background: #ffffff;
            margin-bottom: 20px;
        }
        .ds-kicker {
            color: #4b6b8a;
            font-size: 0.84rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin-bottom: 6px;
        }
        .ds-title {
            color: #102033;
            font-size: 2.1rem;
            font-weight: 760;
            line-height: 1.16;
            margin-bottom: 8px;
        }
        .ds-subtitle {
            color: #4c5f73;
            font-size: 1.02rem;
            line-height: 1.55;
            max-width: 900px;
            margin-bottom: 0;
        }
        .ds-panel {
            border: 1px solid #e6eaf0;
            border-radius: 10px;
            padding: 16px 18px;
            background: #fbfcfe;
            height: 100%;
        }
        .ds-panel-title {
            color: #102033;
            font-weight: 720;
            margin-bottom: 6px;
        }
        .ds-panel-copy {
            color: #5a6b7c;
            font-size: 0.92rem;
            line-height: 1.45;
            margin: 0;
        }
        div[data-testid="stMetric"] {
            background: #20242c;
            border: 1px solid #353b46;
            border-radius: 10px;
            padding: 14px 16px;
        }
        div[data-testid="stMetric"] label,
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: #f4f7fb;
        }
        div[data-testid="stMetric"] label {
            opacity: 0.82;
        }
        div[data-testid="stDownloadButton"] button,
        div[data-testid="stButton"] button {
            border-radius: 8px;
            font-weight: 700;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="ds-hero">
        <div class="ds-kicker">DataSanity Dashboard Generator</div>
        <div class="ds-title">Convierte un Excel o CSV en un dashboard de negocio en segundos</div>
        <p class="ds-subtitle">
            Detecta columnas numéricas, fechas y categorías para generar KPIs, calidad de datos,
            rankings y evolución temporal sin configurar fórmulas manualmente.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

col_info1, col_info2, col_info3 = st.columns(3)
with col_info1:
    st.markdown(
        """
        <div class="ds-panel">
            <div class="ds-panel-title">KPIs automáticos</div>
            <p class="ds-panel-copy">Registros, columnas, valores vacíos, duplicados exactos y métricas numéricas.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col_info2:
    st.markdown(
        """
        <div class="ds-panel">
            <div class="ds-panel-title">Gráficos rápidos</div>
            <p class="ds-panel-copy">Tops por categoría y evolución temporal si existe una columna de fecha.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col_info3:
    st.markdown(
        """
        <div class="ds-panel">
            <div class="ds-panel-title">Excel descargable</div>
            <p class="ds-panel-copy">Exporta resumen, calidad, métricas, tops, evolución y base original.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown("### Carga y análisis")
st.caption("Sube tu archivo Excel o CSV para generar el dashboard automático.")

upload_col, guide_col = st.columns([1.25, 1])
with upload_col:
    archivo_cargado = st.file_uploader(
        "Archivo Excel o CSV",
        type=["xlsx", "xls", "csv"],
        help="Funciona mejor con columnas de fecha, categoría e importe.",
    )
with guide_col:
    st.markdown("**Qué busca la herramienta**")
    st.caption("Fechas para evolución temporal.")
    st.caption("Números para KPIs y totales.")
    st.caption("Categorías para rankings.")


def dataframe_visible(df):
    return df.copy().astype(str)


def pintar_dataframe(df, **kwargs):
    st.dataframe(dataframe_visible(df), **kwargs)


def pintar_barras(tabla, columna_categoria, columna_valor):
    chart_df = tabla[[columna_categoria, columna_valor]].copy()
    chart_df.columns = ["Categoria", "Valor"]
    chart_df["Categoria"] = chart_df["Categoria"].astype(str)
    chart_df["Valor"] = pd.to_numeric(chart_df["Valor"], errors="coerce").fillna(0)
    st.bar_chart(chart_df.set_index("Categoria")["Valor"])

if archivo_cargado is not None:
    try:
        df_original = leer_archivo(archivo_cargado)
    except Exception as error:
        st.error(f"No se pudo leer el archivo: {error}")
        st.stop()

    if df_original.empty:
        st.error("El archivo está vacío.")
        st.stop()

    st.subheader("Vista previa de la base original")
    pintar_dataframe(df_original.head(20), width="stretch")

    if st.button("Generar dashboard", type="primary"):
        resultado = analizar_dashboard(df_original)
        st.session_state["resultado_dashboard"] = resultado
else:
    st.info("Sube un archivo en el bloque de carga para iniciar el análisis.")

if "resultado_dashboard" in st.session_state:
    resultado = st.session_state["resultado_dashboard"]
    resumen = resultado["resumen"]

    st.success("Dashboard generado correctamente.")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Registros", resumen["registros"])
    col2.metric("Columnas", resumen["columnas"])
    col3.metric("Valores vacíos", resumen["valores_vacios"])
    col4.metric("Duplicados exactos", resumen["filas_duplicadas"])

    tab_resumen, tab_calidad, tab_metricas, tab_tops, tab_evolucion, tab_base = st.tabs(
        [
            "Resumen",
            "Calidad de datos",
            "Métricas numéricas",
            "Tops",
            "Evolución",
            "Base original",
        ]
    )

    with tab_resumen:
        st.subheader("Resumen ejecutivo")
        resumen_tabla = pd.DataFrame(
            [
                ["Columna fecha principal", resumen["columna_fecha_principal"] or "No detectada"],
                ["Columna importe principal", resumen["columna_importe_principal"] or "No detectada"],
                ["Columnas numéricas", ", ".join(map(str, resumen["columnas_numericas"])) or "No detectadas"],
                ["Columnas categóricas", ", ".join(map(str, resumen["columnas_categoricas"][:8])) or "No detectadas"],
            ],
            columns=["Elemento", "Valor"],
        )
        pintar_dataframe(resumen_tabla, width="stretch", hide_index=True)
        st.write(
            "El dashboard es automático y exploratorio. Sirve para entender rápido la base, detectar problemas "
            "y preparar una primera lectura de negocio."
        )

    with tab_calidad:
        st.subheader("Calidad de datos por columna")
        pintar_dataframe(resultado["calidad"], width="stretch", hide_index=True)
        if not resultado["calidad"].empty:
            pintar_barras(resultado["calidad"], "Columna", "Valores_Vacios")

    with tab_metricas:
        st.subheader("Métricas numéricas")
        if resultado["metricas"].empty:
            st.info("No se han detectado columnas numéricas suficientes.")
        else:
            pintar_dataframe(resultado["metricas"], width="stretch", hide_index=True)

    with tab_tops:
        st.subheader("Rankings automáticos")
        if not resultado["tops"]:
            st.info("No se han detectado columnas categóricas suficientes.")
        else:
            for nombre_columna, tabla in resultado["tops"].items():
                st.markdown(f"**Top por {nombre_columna}**")
                pintar_dataframe(tabla, width="stretch", hide_index=True)
                if tabla.shape[1] >= 2:
                    pintar_barras(tabla, tabla.columns[0], tabla.columns[1])

    with tab_evolucion:
        st.subheader("Evolución temporal")
        if resultado["evolucion"].empty:
            st.info("No se ha podido construir una evolución temporal.")
        else:
            pintar_dataframe(resultado["evolucion"], width="stretch", hide_index=True)
            if "Importe_Total" in resultado["evolucion"].columns:
                st.line_chart(resultado["evolucion"].set_index("Mes")["Importe_Total"])
            elif "Registros" in resultado["evolucion"].columns:
                st.line_chart(resultado["evolucion"].set_index("Mes")["Registros"])

    with tab_base:
        st.subheader("Base original")
        pintar_dataframe(resultado["base"].head(1000), width="stretch")

    archivo_excel = exportar_dashboard_excel(resultado)
    st.download_button(
        label="Descargar dashboard profesional (.xlsx)",
        data=archivo_excel,
        file_name="dashboard_automatico_datasanity.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )
