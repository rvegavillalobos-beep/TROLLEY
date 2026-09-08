import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from openpyxl import load_workbook
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
    .stMetric { background-color: #f8f9fa; border-radius: 10px; padding: 10px; border: 1px solid #e0e0e0; }
    h1, h2, h3 { color: #1f2c4c; }
    table { font-size: 14px; }
</style>
""", unsafe_allow_html=True)

st.title("📊 Dashboard de Gestión de Defectos - Transportadores")
st.caption("Carga tu archivo Excel para visualizar el resumen ejecutivo y el análisis detallado.")

# ============================================================
# CARGA DE ARCHIVO
# ============================================================
st.sidebar.header("📁 Cargar archivo")
uploaded_file = st.sidebar.file_uploader("Selecciona el archivo Excel (.xlsx)", type=["xlsx", "xls"])

if uploaded_file is None:
    st.info("👆 Carga un archivo Excel desde la barra lateral para comenzar.")
    st.stop()

file_bytes = uploaded_file.read()

@st.cache_data
def get_sheet_names(_bytes):
    return pd.ExcelFile(io.BytesIO(_bytes)).sheet_names

@st.cache_data
def load_data(_bytes, sheet_name):
    df = pd.read_excel(io.BytesIO(_bytes), sheet_name=sheet_name)
    df.columns = [str(c).strip() for c in df.columns]
    for col in ["Date Open", "Date Closed"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

# ============================================================
# LECTURA DEL RESUMEN EJECUTIVO (pestaña "Dashboard")
# ============================================================
def find_cell(ws, target):
    target = str(target).strip().lower()
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and cell.value.strip().lower() == target:
                return cell.row, cell.column
    return None

def get_value(ws, r, c):
    return ws.cell(row=r, column=c).value

@st.cache_data
def parse_dashboard_sheet(_bytes, sheet_name="Dashboard"):
    try:
        wb = load_workbook(io.BytesIO(_bytes), data_only=True)
    except Exception:
        return None
    if sheet_name not in wb.sheetnames:
        return None
    ws = wb[sheet_name]
    result = {}

    for label, key in [("OPEN DEFECTS", "open"), ("PENDING CONFIRMATION", "pending"), ("CLOSED DEFECTS", "closed")]:
        pos = find_cell(ws, label)
        if pos:
            r, c = pos
            result[key] = get_value(ws, r + 1, c)

    pos = find_cell(ws, "Status / Severity")
    if pos:
        r, c = pos
        rows = ["Open", "Confirmation Pending", "Closed", "Total"]
        data = []
        for i, row_label in enumerate(rows, start=1):
            vals = [get_value(ws, r + i, c + j) for j in range(1, 5)]
            data.append([row_label] + vals)
        result["severity_table"] = pd.DataFrame(data, columns=["Status/Severity", "Minor", "Major", "Critical", "Total"])

    pos = find_cell(ws, "Element Type")
    if pos:
        r, c = pos
        rows_data, i = [], 2
        while True:
            label = get_value(ws, r + i, c)
            if label is None or str(label).strip() == "":
                break
            vals = [get_value(ws, r + i, c + j) for j in range(1, 7)]
            rows_data.append([label] + vals)
            i += 1
        result["element_table"] = pd.DataFrame(
            rows_data, columns=["Element Type", "Open", "Closed", "Pending", "Minor", "Major", "Critical"]
        )

    pos = find_cell(ws, "Week")
    if pos:
        r, c = pos
        weeks, i = [], 1
        while True:
            wk = get_value(ws, r + i, c)
            if wk is None or str(wk).strip() == "":
                break
            weeks.append([wk, get_value(ws, r + i, c + 1), get_value(ws, r + i, c + 2), get_value(ws, r + i, c + 3)])
            i += 1
        result["week_table"] = pd.DataFrame(weeks, columns=["Week", "Closed", "Confirmation Pending", "Open"])

    return result if result else None

def compute_fallback_summary(df):
    df_tmp = df.copy()
    df_tmp["StatusNorm"] = df_tmp["Status"].astype(str).apply(
        lambda x: "Open" if x.strip().lower() == "open"
        else ("Closed" if x.strip().lower() == "closed" else "Confirmation Pending")
    )
    open_v = (df_tmp["StatusNorm"] == "Open").sum()
    pending_v = (df_tmp["StatusNorm"] == "Confirmation Pending").sum()
    closed_v = (df_tmp["StatusNorm"] == "Closed").sum()

    sev_order, status_order = ["Minor", "Major", "Critical"], ["Open", "Confirmation Pending", "Closed"]
    pivot = pd.crosstab(df_tmp["StatusNorm"], df_tmp["Severity"]).reindex(
        index=status_order, columns=sev_order, fill_value=0
    )
    pivot["Total"] = pivot.sum(axis=1)
    total_row = pivot.sum(axis=0)
    total_row.name = "Total"
    pivot = pd.concat([pivot, pd.DataFrame([total_row])])
    df_sev = pivot.reset_index().rename(columns={"index": "Status/Severity"})

    elem_rows = []
    for etype, g in df_tmp.groupby("Type"):
        elem_rows.append([
            etype, (g["StatusNorm"] == "Open").sum(), (g["StatusNorm"] == "Closed").sum(),
            (g["StatusNorm"] == "Confirmation Pending").sum(),
            (g["Severity"] == "Minor").sum(), (g["Severity"] == "Major").sum(), (g["Severity"] == "Critical").sum()
        ])
    df_elem = pd.DataFrame(elem_rows, columns=["Element Type", "Open", "Closed", "Pending", "Minor", "Major", "Critical"])
    total = ["TOTAL"] + [df_elem[c].sum() for c in ["Open", "Closed", "Pending", "Minor", "Major", "Critical"]]
    df_elem = pd.concat([df_elem, pd.DataFrame([total], columns=df_elem.columns)], ignore_index=True)

    return {"open": open_v, "pending": pending_v, "closed": closed_v,
            "severity_table": df_sev, "element_table": df_elem, "week_table": None}

# ============================================================
# COMPONENTES VISUALES DEL RESUMEN EJECUTIVO
# ============================================================
def kpi_card(title, value, color):
    st.markdown(f"""
    <div style="border:1px solid #ccc; border-radius:6px; padding:15px; text-align:center; background-color:#fafafa;">
        <div style="font-size:13px; color:#555; font-weight:600; letter-spacing:1px;">{title}</div>
        <div style="font-size:36px; font-weight:bold; color:{color};">{value}</div>
    </div>
    """, unsafe_allow_html=True)

def render_severity_table(df_sev):
    row_colors = {"Open": "#e74c3c", "Confirmation Pending": "#f39c12", "Closed": "#2ecc71", "Total": "#1f2c4c"}
    html = "<table style='width:100%; border-collapse:collapse; text-align:center;'>"
    html += "<tr>" + "".join(
        f"<th style='background-color:#1f2c4c;color:white;padding:6px;border:1px solid #ddd;'>{c}</th>"
        for c in df_sev.columns) + "</tr>"
    for _, row in df_sev.iterrows():
        html += "<tr>"
        for i, val in enumerate(row):
            col = df_sev.columns[i]
            color = row_colors.get(str(val), "#2c3e50") if col == "Status/Severity" else "#2c3e50"
            weight = "700" if col == "Status/Severity" else "500"
            html += f"<td style='padding:6px;border:1px solid #ddd;color:{color};font-weight:{weight};'>{val}</td>"
        html += "</tr>"
    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

def render_element_table(df_elem):
    html = "<table style='width:100%; border-collapse:collapse; text-align:center;'>"
    html += ("<tr><th style='background-color:#1f2c4c;color:white;padding:6px;border:1px solid #ddd;'>Element Type</th>"
              "<th colspan='3' style='background-color:#34495e;color:white;padding:6px;border:1px solid #ddd;'>STATUS BREAKDOWN</th>"
              "<th colspan='3' style='background-color:#34495e;color:white;padding:6px;border:1px solid #ddd;'>SEVERITY BREAKDOWN</th></tr>")
    html += "<tr><th style='padding:6px;border:1px solid #ddd;'></th>"
    for c in ["Open", "Closed", "Pending", "Minor", "Major", "Critical"]:
        html += f"<th style='padding:6px;border:1px solid #ddd;background-color:#ecf0f1;'>{c}</th>"
    html += "</tr>"
    for _, row in df_elem.iterrows():
        is_total = str(row["Element Type"]).strip().upper() == "TOTAL"
        w = "700" if is_total else "500"
        html += f"<tr><td style='padding:6px;border:1px solid #ddd;font-weight:{w};color:#2c3e50;'>{row['Element Type']}</td>"
        for c in ["Open", "Closed", "Pending", "Minor", "Major", "Critical"]:
            html += f"<td style='padding:6px;border:1px solid #ddd;font-weight:{w};'>{row[c]}</td>"
        html += "</tr>"
    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

def render_burndown_chart(df_week, title_suffix=""):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_week["Week"], y=df_week["Closed"], name="Closed", mode="lines",
                              stackgroup="one", fillcolor="rgba(46,204,113,0.85)", line=dict(color="#2ecc71")))
    fig.add_trace(go.Scatter(x=df_week["Week"], y=df_week["Confirmation Pending"], name="Confirmation Pending",
                              mode="lines", stackgroup="one", fillcolor="rgba(243,156,18,0.85)", line=dict(color="#f39c12")))
    fig.add_trace(go.Scatter(x=df_week["Week"], y=df_week["Open"], name="Open", mode="lines",
                              stackgroup="one", fillcolor="rgba(231,76,60,0.85)", line=dict(color="#e74c3c")))
    fig.update_layout(
        title=f"Defect Status Trend & Burndown per Calendar Week{title_suffix}",
        xaxis_title="Week", yaxis_title="Count",
        legend=dict(orientation="h", y=-0.2), height=430
    )
    st.plotly_chart(fig, use_container_width=True)

# ============================================================
# SECCIÓN 1: RESUMEN EJECUTIVO (parte principal)
# ============================================================
st.header("📌 Resumen Ejecutivo")

sheet_names = get_sheet_names(file_bytes)
summary = parse_dashboard_sheet(file_bytes, "Dashboard") if "Dashboard" in sheet_names else None

fallback_used = False
if summary is None:
    default_sheet = "Data" if "Data" in sheet_names else sheet_names[0]
    df_for_fallback = load_data(file_bytes, default_sheet)
    if all(c in df_for_fallback.columns for c in ["Type", "Status", "Severity"]):
        summary = compute_fallback_summary(df_for_fallback)
        fallback_used = True

if summary:
    if fallback_used:
        st.warning("No se encontró (o no se pudo interpretar) la pestaña **Dashboard**. "
                    "Se calculó un resumen equivalente a partir de la pestaña **Data**. "
                    "La gráfica de tendencia semanal no está disponible en este modo.")

    c1, c2, c3 = st.columns(3)
    with c1: kpi_card("OPEN DEFECTS", summary.get("open", "N/A"), "#e74c3c")
    with c2: kpi_card("PENDING CONFIRMATION", summary.get("pending", "N/A"), "#f39c12")
    with c3: kpi_card("CLOSED DEFECTS", summary.get("closed", "N/A"), "#2ecc71")

    st.markdown("####")
    left, right = st.columns([1, 1.3])

    with left:
        st.subheader("Status / Severity")
        if summary.get("severity_table") is not None:
            render_severity_table(summary["severity_table"])
        st.markdown("####")
        st.subheader("Element Type")
        if summary.get("element_table") is not None:
            render_element_table(summary["element_table"])

    with right:
        if summary.get("week_table") is not None:
            render_burndown_chart(summary["week_table"])
        else:
            st.info("La gráfica de tendencia semanal (Burndown) requiere la pestaña **Dashboard** "
                    "con la tabla de semanas (Week / Closed / Confirmation Pending / Open) en el Excel original.")
else:
    st.error("No fue posible generar el resumen ejecutivo con este archivo. Verifica que contenga "
              "la pestaña **Dashboard** o una pestaña **Data** con las columnas requeridas.")

st.markdown("---")

# ============================================================
# SECCIÓN 2: ANÁLISIS DETALLADO (pestaña Data)
# ============================================================
st.header("🔍 Análisis Detallado")

default_sheet = "Data" if "Data" in sheet_names else sheet_names[0]
sheet_selected = st.sidebar.selectbox(
    "Hoja a analizar (Análisis Detallado)", sheet_names, index=sheet_names.index(default_sheet)
)
df_raw = load_data(file_bytes, sheet_selected)

required_cols = ["Conveyor", "Station", "Type", "Category", "Status", "Severity"]
missing = [c for c in required_cols if c not in df_raw.columns]
if missing:
    st.error(f"Faltan columnas requeridas en la hoja seleccionada: {missing}")
    st.stop()

df = df_raw.copy()
for col in ["Status", "Severity", "Type", "Category", "Responsible"]:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip().replace({"nan": None, "None": None})

# ---- Filtros ----
st.sidebar.header("🔎 Filtros (Análisis Detallado)")

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
if type_sel is not None: mask &= df["Type"].isin(type_sel)
if status_sel is not None: mask &= df["Status"].isin(status_sel)
if severity_sel is not None: mask &= df["Severity"].isin(severity_sel)
if responsible_sel is not None and "Responsible" in df.columns:
    mask &= df["Responsible"].isin(responsible_sel) | df["Responsible"].isna()

if "Date Open" in df.columns and df["Date Open"].notna().any():
    min_date, max_date = df["Date Open"].min().date(), df["Date Open"].max().date()
    date_range = st.sidebar.date_input("Rango de fecha de apertura", value=(min_date, max_date),
                                        min_value=min_date, max_value=max_date)
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
        mask &= (df["Date Open"].dt.date >= start) & (df["Date Open"].dt.date <= end)

df_f = df[mask].copy()
st.sidebar.markdown("---")
st.sidebar.write(f"**Registros mostrados:** {len(df_f)} / {len(df)}")

COLOR_STATUS = {"Open": "#e74c3c", "Closed": "#2ecc71", "Confirmation pending": "#f39c12"}
COLOR_SEV = {"Minor": "#3498db", "Major": "#f39c12", "Critical": "#e74c3c"}

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

c3, c4 = st.columns(2)
with c3:
    st.subheader("Estatus por Tipo de Elemento")
    type_status = df_f.groupby(["Type", "Status"]).size().reset_index(name="Count")
    fig3 = px.bar(type_status, x="Type", y="Count", color="Status", barmode="stack",
                  color_discrete_map=COLOR_STATUS)
    st.plotly_chart(fig3, use_container_width=True)

with c4:
    st.subheader("Top 15 Estaciones con más Defectos")
    if "Station" in df_f.columns:
        station_counts = df_f["Station"].value_counts().head(15).reset_index()
        station_counts.columns = ["Station", "Count"]
        fig4 = px.bar(station_counts, x="Count", y="Station", orientation="h", text="Count",
                      color="Count", color_continuous_scale="Reds")
        fig4.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
        st.plotly_chart(fig4, use_container_width=True)

st.subheader("📈 Tendencia de Defectos por Semana (calculado desde Data)")
if "Date Open" in df_f.columns and df_f["Date Open"].notna().any():
    df_trend = df_f.copy()
    df_trend["Week"] = df_trend["Date Open"].dt.to_period("W").astype(str)
    trend = df_trend.groupby(["Week", "Status"]).size().reset_index(name="Count")
    fig5 = px.line(trend, x="Week", y="Count", color="Status", markers=True, color_discrete_map=COLOR_STATUS)
    st.plotly_chart(fig5, use_container_width=True)
else:
    st.info("No hay suficientes datos de fecha de apertura para mostrar la tendencia.")

if "Responsible" in df_f.columns and df_f["Responsible"].notna().any():
    st.subheader("👷 Carga de Trabajo por Responsable")
    resp = df_f.dropna(subset=["Responsible"]).groupby(["Responsible", "Status"]).size().reset_index(name="Count")
    fig6 = px.bar(resp, x="Responsible", y="Count", color="Status", barmode="stack", color_discrete_map=COLOR_STATUS)
    st.plotly_chart(fig6, use_container_width=True)

st.markdown("---")
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

col_dl1, col_dl2 = st.columns(2)
with col_dl1:
    csv = df_show.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ Descargar CSV filtrado", data=csv, file_name="defectos_filtrados.csv", mime="text/csv")
with col_dl2:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df_show.to_excel(writer, index=False, sheet_name="Data")
    st.download_button("⬇️ Descargar Excel filtrado", data=buffer.getvalue(), file_name="defectos_filtrados.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
