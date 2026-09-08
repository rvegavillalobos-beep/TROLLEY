import streamlit as st
import pandas as pd
import plotly.express as px
import io

# ============================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================
st.set_page_config(
    page_title="Dashboard de Defectos - Transportadores",
    layout="wide",
    page_icon="📊"
)

st.markdown("""
<style>
    .stMetric {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 10px;
        border: 1px solid #e0e0e0;
    }
    h1, h2, h3 { color: #1f2c4c; }
</style>
""", unsafe_allow_html=True)

st.title("📊 Dashboard de Gestión de Defectos - Transportadores")
st.caption("Carga tu archivo Excel para visualizar el estado de los defectos en tiempo real.")

# ============================================================
# CARGA DE ARCHIVO
# ============================================================
st.sidebar.header("📁 Cargar archivo")
uploaded_file = st.sidebar.file_uploader("Selecciona el archivo Excel (.xlsx)", type=["xlsx", "xls"])

@st.cache_data
def get_sheet_names(file):
    return pd.ExcelFile(file).sheet_names

@st.cache_data
def load_data(file, sheet_name):
    df = pd.read_excel(file, sheet_name=sheet_name)
    df.columns = [str(c).strip() for c in df.columns]
    for col in ["Date Open", "Date Closed"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

if uploaded_file is None:
    st.info("👆 Carga un archivo Excel desde la barra lateral para comenzar.")
    st.stop()

sheet_names = get_sheet_names(uploaded_file)
default_sheet = "Data" if "Data" in sheet_names else sheet_names[0]
sheet_selected = st.sidebar.selectbox(
    "Hoja a analizar", sheet_names, index=sheet_names.index(default_sheet)
)

df_raw = load_data(uploaded_file, sheet_selected)

required_cols = ["Conveyor", "Station", "Type", "Category", "Status", "Severity"]
missing = [c for c in required_cols if c not in df_raw.columns]
if missing:
    st.error(f"Faltan columnas requeridas en la hoja seleccionada: {missing}")
    st.stop()

df = df_raw.copy()
for col in ["Status", "Severity", "Type", "Category", "Responsible"]:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip().replace({"nan": None, "None": None})

# ============================================================
# FILTROS
# ============================================================
st.sidebar.header("🔎 Filtros")

def multiselect_filter(label, col):
    if col in df.columns:
        options = sorted([o for o in df[col].dropna().unique().tolist()])
        return st.sidebar.multiselect(label, options, default=options)
    return None

type_sel = multiselect_filter("Tipo (Type)", "Type")
status_sel = multiselect_filter("Estatus (Status)", "Status")
severity_sel = multiselect_filter("Severidad (Severity)", "Severity")
responsible_sel = multiselect_filter("Responsable", "Responsible")

mask = pd.Series(True, index=df.index)
if type_sel is not None:
    mask &= df["Type"].isin(type_sel)
if status_sel is not None:
    mask &= df["Status"].isin(status_sel)
if severity_sel is not None:
    mask &= df["Severity"].isin(severity_sel)
if responsible_sel is not None and "Responsible" in df.columns:
    mask &= df["Responsible"].isin(responsible_sel) | df["Responsible"].isna()

if "Date Open" in df.columns and df["Date Open"].notna().any():
    min_date = df["Date Open"].min().date()
    max_date = df["Date Open"].max().date()
    date_range = st.sidebar.date_input(
        "Rango de fecha de apertura",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
        mask &= (df["Date Open"].dt.date >= start) & (df["Date Open"].dt.date <= end)

df_f = df[mask].copy()
st.sidebar.markdown("---")
st.sidebar.write(f"**Registros mostrados:** {len(df_f)} / {len(df)}")

# ============================================================
# KPIs
# ============================================================
total = len(df_f)
status_lower = df_f["Status"].str.lower().fillna("")
severity_lower = df_f["Severity"].str.lower().fillna("") if "Severity" in df_f.columns else pd.Series("", index=df_f.index)

open_count = (status_lower == "open").sum()
pending_count = status_lower.str.contains("pending", na=False).sum()
closed_count = (status_lower == "closed").sum()
critical_open = ((status_lower != "closed") & (severity_lower == "critical")).sum()

avg_days = None
if "Date Open" in df_f.columns and "Date Closed" in df_f.columns:
    closed_mask = df_f["Date Closed"].notna() & df_f["Date Open"].notna()
    if closed_mask.any():
        avg_days = (df_f.loc[closed_mask, "Date Closed"] - df_f.loc[closed_mask, "Date Open"]).dt.days.mean()

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Total defectos", total)
col2.metric("Abiertos", open_count)
col3.metric("Pend. Confirmación", pending_count)
col4.metric("Cerrados", closed_count)
col5.metric("Críticos activos", critical_open)
col6.metric("Días prom. resolución", f"{avg_days:.1f}" if avg_days is not None else "N/A")

st.markdown("---")

COLOR_STATUS = {"Open": "#e74c3c", "Closed": "#2ecc71", "Confirmation pending": "#f39c12"}
COLOR_SEV = {"Minor": "#3498db", "Major": "#f39c12", "Critical": "#e74c3c"}

# ============================================================
# GRÁFICOS - FILA 1
# ============================================================
c1, c2 = st.columns(2)

with c1:
    st.subheader("Distribución por Estatus")
    status_counts = df_f["Status"].value_counts().reset_index()
    status_counts.columns = ["Status", "Count"]
    fig = px.pie(status_counts, names="Status", values="Count", hole=0.45,
                 color="Status", color_discrete_map=COLOR_STATUS)
    fig.update_traces(textinfo="percent+value")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("Distribución por Severidad")
    if "Severity" in df_f.columns:
        sev_counts = df_f["Severity"].value_counts().reset_index()
        sev_counts.columns = ["Severity", "Count"]
        fig2 = px.bar(sev_counts, x="Severity", y="Count", color="Severity",
                      text="Count", color_discrete_map=COLOR_SEV)
        fig2.update_layout(showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

# ============================================================
# GRÁFICOS - FILA 2
# ============================================================
c3, c4 = st.columns(2)

with c3:
    st.subheader("Estatus por Tipo de Elemento")
    if "Type" in df_f.columns:
        type_status = df_f.groupby(["Type", "Status"]).size().reset_index(name="Count")
        fig3 = px.bar(type_status, x="Type", y="Count", color="Status", barmode="stack",
                      color_discrete_map=COLOR_STATUS)
        st.plotly_chart(fig3, use_container_width=True)

with c4:
    st.subheader("Top 15 Estaciones con más Defectos")
    if "Station" in df_f.columns:
        station_counts = df_f["Station"].value_counts().head(15).reset_index()
        station_counts.columns = ["Station", "Count"]
        fig4 = px.bar(station_counts, x="Count", y="Station", orientation="h",
                      text="Count", color="Count", color_continuous_scale="Reds")
        fig4.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
        st.plotly_chart(fig4, use_container_width=True)

# ============================================================
# TENDENCIA SEMANAL
# ============================================================
st.subheader("📈 Tendencia de Defectos por Semana")
if "Date Open" in df_f.columns and df_f["Date Open"].notna().any():
    df_trend = df_f.copy()
    df_trend["Week"] = df_trend["Date Open"].dt.to_period("W").astype(str)
    trend = df_trend.groupby(["Week", "Status"]).size().reset_index(name="Count")
    fig5 = px.line(trend, x="Week", y="Count", color="Status", markers=True,
                   color_discrete_map=COLOR_STATUS)
    st.plotly_chart(fig5, use_container_width=True)
else:
    st.info("No hay suficientes datos de fecha de apertura para mostrar la tendencia.")

# ============================================================
# CARGA DE TRABAJO POR RESPONSABLE
# ============================================================
if "Responsible" in df_f.columns and df_f["Responsible"].notna().any():
    st.subheader("👷 Carga de Trabajo por Responsable")
    resp = df_f.dropna(subset=["Responsible"]).groupby(["Responsible", "Status"]).size().reset_index(name="Count")
    fig6 = px.bar(resp, x="Responsible", y="Count", color="Status", barmode="stack",
                  color_discrete_map=COLOR_STATUS)
    st.plotly_chart(fig6, use_container_width=True)

st.markdown("---")

# ============================================================
# TABLA DE DETALLE
# ============================================================
st.subheader("📋 Detalle de Registros")
search = st.text_input("Buscar en Conveyor / Estación / Comentarios")
df_show = df_f.copy()
if search:
    mask_search = pd.Series(False, index=df_show.index)
    for col in ["Conveyor", "Station", "Comments"]:
        if col in df_show.columns:
            mask_search |= df_show[col].astype(str).str.contains(search, case=False, na=False)
    df_show = df_show[mask_search]

st.dataframe(df_show, use_container_width=True, height=400)

# ============================================================
# DESCARGA DE DATOS FILTRADOS
# ============================================================
col_dl1, col_dl2 = st.columns(2)
with col_dl1:
    csv = df_show.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ Descargar CSV filtrado", data=csv,
                        file_name="defectos_filtrados.csv", mime="text/csv")

with col_dl2:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df_show.to_excel(writer, index=False, sheet_name="Data")
    st.download_button("⬇️ Descargar Excel filtrado", data=buffer.getvalue(),
                        file_name="defectos_filtrados.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
