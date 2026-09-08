import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import io

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Defect Management Dashboard - Conveyors",
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

st.title("📊 Defect Management Dashboard - Conveyors")
st.caption("Upload your Excel file. All KPIs, tables and charts are calculated live from the **Data** sheet only.")

# ============================================================
# SIDEBAR - CACHE CONTROL (safety net)
# ============================================================
if st.sidebar.button("🔄 Clear cache & reload"):
    st.cache_data.clear()
    st.rerun()

# ============================================================
# FILE UPLOAD
# ============================================================
st.sidebar.header("📁 Upload File")
uploaded_file = st.sidebar.file_uploader("Select the Excel file (.xlsx)", type=["xlsx", "xls"])

if uploaded_file is None:
    st.info("👆 Upload an Excel file from the sidebar to get started.")
    st.stop()

file_bytes = uploaded_file.getvalue()

# NOTE: parameters do NOT start with "_", so Streamlit correctly includes
# the file content in the cache key. This ensures that every time you
# upload a modified Excel file, the data is recalculated (no stale cache).
@st.cache_data
def get_sheet_names(file_bytes):
    return pd.ExcelFile(io.BytesIO(file_bytes)).sheet_names

@st.cache_data
def load_data(file_bytes, sheet_name):
    df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name)
    df.columns = [str(c).strip() for c in df.columns]
    for col in ["Date Open", "Date Closed"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
        else:
            df[col] = pd.NaT
    return df

sheet_names = get_sheet_names(file_bytes)
default_data_sheet = "Data" if "Data" in sheet_names else sheet_names[0]

sheet_selected = st.sidebar.selectbox(
    "Sheet to analyze", sheet_names, index=sheet_names.index(default_data_sheet)
)
df_raw = load_data(file_bytes, sheet_selected)

required_cols = ["Conveyor", "Station", "Type", "Category", "Status", "Severity"]
missing = [c for c in required_cols if c not in df_raw.columns]
if missing:
    st.error(f"The selected sheet is missing required columns: {missing}. "
             f"Please make sure you selected the **Data** sheet.")
    st.stop()

df_data_full = df_raw.copy()
for col in ["Status", "Severity", "Type", "Category", "Responsible"]:
    if col in df_data_full.columns:
        df_data_full[col] = df_data_full[col].astype(str).str.strip().replace({"nan": None, "None": None})

# ============================================================
# HELPERS
# ============================================================
def fmt_num(v):
    if v is None:
        return ""
    if isinstance(v, float):
        if pd.isna(v):
            return ""
        if v.is_integer():
            return str(int(v))
        return f"{v:.1f}"
    return str(v)

def normalize_status_series(s):
    return s.astype(str).str.strip().str.lower().map(
        lambda v: "Open" if v == "open" else ("Closed" if v == "closed" else "Confirmation Pending")
    )

# ============================================================
# LIVE SUMMARY: KPIs + Status/Severity table + Element Type table
# 100% computed from the Data sheet - the Dashboard sheet is never read.
# ============================================================
def compute_live_summary(df):
    d = df.copy()
    d["StatusNorm"] = normalize_status_series(d["Status"])

    open_v = (d["StatusNorm"] == "Open").sum()
    pending_v = (d["StatusNorm"] == "Confirmation Pending").sum()
    closed_v = (d["StatusNorm"] == "Closed").sum()

    sev_order = ["Minor", "Major", "Critical"]
    status_order = ["Open", "Confirmation Pending", "Closed"]
    d["SeverityClean"] = d["Severity"].where(d["Severity"].isin(sev_order))

    pivot = pd.crosstab(d["StatusNorm"], d["SeverityClean"]).reindex(
        index=status_order, columns=sev_order, fill_value=0
    )
    pivot["Total"] = pivot.sum(axis=1)
    total_row = pivot.sum(axis=0)
    total_row.name = "Total"
    pivot = pd.concat([pivot, pd.DataFrame([total_row])])
    df_sev = pivot.reset_index().rename(columns={"index": "Status/Severity"})

    elem_rows = []
    for etype, g in d.groupby("Type"):
        elem_rows.append([
            etype,
            (g["StatusNorm"] == "Open").sum(),
            (g["StatusNorm"] == "Closed").sum(),
            (g["StatusNorm"] == "Confirmation Pending").sum(),
            (g["SeverityClean"] == "Minor").sum(),
            (g["SeverityClean"] == "Major").sum(),
            (g["SeverityClean"] == "Critical").sum(),
        ])
    df_elem = pd.DataFrame(elem_rows, columns=["Element Type", "Open", "Closed", "Pending", "Minor", "Major", "Critical"])
    df_elem = df_elem.sort_values("Open", ascending=False).reset_index(drop=True) if not df_elem.empty else df_elem
    total = ["TOTAL"] + [df_elem[c].sum() for c in ["Open", "Closed", "Pending", "Minor", "Major", "Critical"]]
    df_elem = pd.concat([df_elem, pd.DataFrame([total], columns=df_elem.columns)], ignore_index=True)

    return {"open": int(open_v), "pending": int(pending_v), "closed": int(closed_v),
            "severity_table": df_sev, "element_table": df_elem}

# ============================================================
# DYNAMIC BURNDOWN + FORECAST (computed live from Data: Status, Date Open, Date Closed)
# ============================================================
def compute_dynamic_burndown(df, forecast_periods=6):
    data = df.dropna(subset=["Date Open"]).copy()
    if data.empty or "Status" not in data.columns:
        return None, None, 0

    data["StatusNorm"] = normalize_status_series(data["Status"])

    start = data["Date Open"].min().normalize()
    today = pd.Timestamp(pd.Timestamp.now().date())
    end = min(today, max(start, today))

    checkpoints = pd.date_range(start=start, end=end, freq="W-SUN")
    if len(checkpoints) == 0:
        checkpoints = pd.DatetimeIndex([end])
    elif checkpoints[-1] < end:
        checkpoints = checkpoints.append(pd.DatetimeIndex([end]))

    date_open_vals = data["Date Open"].values
    date_closed_vals = data["Date Closed"].values
    status_vals = data["StatusNorm"].values

    open_arr, pending_arr, closed_arr = [], [], []
    for cp in checkpoints:
        cp_ts = np.datetime64(cp)
        opened_mask = date_open_vals <= cp_ts
        closed_mask = (~pd.isna(date_closed_vals)) & (date_closed_vals <= cp_ts)
        active_mask = opened_mask & ~closed_mask
        closed_arr.append(int(closed_mask.sum()))
        open_arr.append(int(((status_vals == "Open") & active_mask).sum()))
        pending_arr.append(int(((status_vals == "Confirmation Pending") & active_mask).sum()))

    hist = pd.DataFrame({
        "Date": checkpoints, "Open": open_arr,
        "Confirmation Pending": pending_arr, "Closed": closed_arr
    })
    # Week label shows only the calendar week number, no year (e.g. "CW24")
    hist["Week"] = hist["Date"].apply(lambda d: f"CW{d.isocalendar()[1]:02d}")

    total_defects = len(data)
    forecast_df = pd.DataFrame(columns=hist.columns)

    if len(hist) >= 2 and forecast_periods > 0:
        x = np.arange(len(hist))
        y = hist["Closed"].values.astype(float)
        slope, intercept = np.polyfit(x, y, 1)
        slope = max(slope, 0)

        last_open = hist["Open"].iloc[-1]
        last_pending = hist["Confirmation Pending"].iloc[-1]
        remaining_last = last_open + last_pending
        open_share = last_open / remaining_last if remaining_last > 0 else 0
        pending_share = last_pending / remaining_last if remaining_last > 0 else 0

        rows, last_date, last_closed = [], hist["Date"].iloc[-1], hist["Closed"].iloc[-1]
        for i in range(1, forecast_periods + 1):
            f_date = last_date + pd.Timedelta(weeks=i)
            f_x = len(hist) - 1 + i
            f_closed = min(max(intercept + slope * f_x, last_closed), total_defects)
            remaining = max(total_defects - f_closed, 0)
            rows.append({
                "Date": f_date,
                "Open": remaining * open_share,
                "Confirmation Pending": remaining * pending_share,
                "Closed": f_closed,
                "Week": f"CW{f_date.isocalendar()[1]:02d}"
            })
        forecast_df = pd.DataFrame(rows)

    return hist, forecast_df, total_defects

def render_dynamic_burndown_chart(hist, forecast_df):
    fig = go.Figure()

    # ---- Actual data (solid areas) - these are the only 3 entries kept in the legend ----
    fig.add_trace(go.Scatter(
        x=hist["Week"], y=hist["Closed"], name="Closed", legendgroup="Closed",
        mode="lines", stackgroup="actual",
        fillcolor="rgba(46,139,87,0.75)", line=dict(color="#2e8b57")
    ))
    fig.add_trace(go.Scatter(
        x=hist["Week"], y=hist["Confirmation Pending"], name="Confirmation Pending", legendgroup="Pending",
        mode="lines", stackgroup="actual",
        fillcolor="rgba(217,164,6,0.75)", line=dict(color="#d9a406")
    ))
    fig.add_trace(go.Scatter(
        x=hist["Week"], y=hist["Open"], name="Open", legendgroup="Open",
        mode="lines", stackgroup="actual",
        fillcolor="rgba(176,58,46,0.75)", line=dict(color="#b03a2e")
    ))

    if forecast_df is not None and not forecast_df.empty:
        last_row = hist.iloc[[-1]][["Week", "Open", "Confirmation Pending", "Closed"]]
        connect_df = pd.concat(
            [last_row, forecast_df[["Week", "Open", "Confirmation Pending", "Closed"]]],
            ignore_index=True
        )
        forecast_start_week = last_row["Week"].values[0]

        # ---- Forecast data (dashed, lighter areas) - hidden from legend to avoid clutter ----
        fig.add_trace(go.Scatter(
            x=connect_df["Week"], y=connect_df["Closed"], name="Closed", legendgroup="Closed",
            showlegend=False, mode="lines", stackgroup="forecast",
            fillcolor="rgba(46,139,87,0.25)", line=dict(color="#2e8b57", dash="dash")
        ))
        fig.add_trace(go.Scatter(
            x=connect_df["Week"], y=connect_df["Confirmation Pending"], name="Confirmation Pending",
            legendgroup="Pending", showlegend=False, mode="lines", stackgroup="forecast",
            fillcolor="rgba(217,164,6,0.25)", line=dict(color="#d9a406", dash="dash")
        ))
        fig.add_trace(go.Scatter(
            x=connect_df["Week"], y=connect_df["Open"], name="Open", legendgroup="Open",
            showlegend=False, mode="lines", stackgroup="forecast",
            fillcolor="rgba(176,58,46,0.25)", line=dict(color="#b03a2e", dash="dash")
        ))

        # ---- Vertical separator marking where the forecast begins ----
        fig.add_shape(
            type="line", xref="x", yref="paper",
            x0=forecast_start_week, x1=forecast_start_week, y0=0, y1=1,
            line=dict(color="#8a94a6", width=1, dash="dot")
        )

        # ---- "FORECAST" label placed ABOVE the chart area (top margin), clear of all lines ----
        forecast_weeks_list = connect_df["Week"].tolist()
        mid_week = forecast_weeks_list[len(forecast_weeks_list) // 2]
        fig.add_annotation(
            x=mid_week, y=1.08, xref="x", yref="paper",
            text="FORECAST", showarrow=False,
            font=dict(size=15, color="#3d4552", family="Arial Black"),
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#8a94a6", borderwidth=1, borderpad=6
        )

    fig.update_layout(
        title="Defect Status Trend & Burndown per Calendar Week",
        xaxis_title="Week", yaxis_title="Count",
        legend=dict(orientation="h", y=-0.2), height=460,
        margin=dict(t=80)  # extra top margin so the FORECAST label has room above the chart
    )
    st.plotly_chart(fig, use_container_width=True)

# ============================================================
# VISUAL COMPONENTS (tables)
# ============================================================
def kpi_card(title, value, color):
    st.markdown(f"""
    <div style="border:1px solid #d0d5dc; border-radius:6px; padding:15px; text-align:center; background-color:#f8f9fb;">
        <div style="font-size:13px; color:#5a6474; font-weight:600; letter-spacing:1px;">{title}</div>
        <div style="font-size:36px; font-weight:bold; color:{color};">{value}</div>
    </div>
    """, unsafe_allow_html=True)

STATUS_TEXT_COLOR = {"Open": "#b03a2e", "Confirmation Pending": "#9a6a06", "Closed": "#1e7e45", "Total": "#1f2c4c"}

def render_severity_table(df_sev):
    html = "<table style='width:100%; border-collapse:collapse; text-align:center; border:1px solid #c9ced6;'>"
    html += "<tr>" + "".join(
        f"<th style='background-color:#1f2c4c;color:#ffffff;padding:8px;border:1px solid #c9ced6;font-weight:600;'>{c}</th>"
        for c in df_sev.columns) + "</tr>"
    for idx, row in df_sev.iterrows():
        bg = "#f4f6f9" if idx % 2 == 0 else "#ffffff"
        html += f"<tr style='background-color:{bg};'>"
        for i, val in enumerate(row):
            col = df_sev.columns[i]
            if col == "Status/Severity":
                color, weight, display_val = STATUS_TEXT_COLOR.get(str(val).strip(), "#2c3e50"), "700", val
            else:
                color = "#2c3e50"
                weight = "700" if str(row["Status/Severity"]).strip() == "Total" else "500"
                display_val = fmt_num(val)
            html += f"<td style='padding:8px;border:1px solid #c9ced6;color:{color};font-weight:{weight};'>{display_val}</td>"
        html += "</tr>"
    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

def render_element_table(df_elem):
    html = "<table style='width:100%; border-collapse:collapse; text-align:center; border:1px solid #c9ced6;'>"
    html += ("<tr><th style='background-color:#1f2c4c;color:#ffffff;padding:8px;border:1px solid #c9ced6;font-weight:600;'>Element Type</th>"
              "<th colspan='3' style='background-color:#2f3f5c;color:#ffffff;padding:8px;border:1px solid #c9ced6;font-weight:600;'>STATUS BREAKDOWN</th>"
              "<th colspan='3' style='background-color:#2f3f5c;color:#ffffff;padding:8px;border:1px solid #c9ced6;font-weight:600;'>SEVERITY BREAKDOWN</th></tr>")
    html += "<tr><th style='padding:8px;border:1px solid #c9ced6;background-color:#e4e8ee;'></th>"
    for c in ["Open", "Closed", "Pending", "Minor", "Major", "Critical"]:
        html += f"<th style='padding:8px;border:1px solid #c9ced6;background-color:#e4e8ee;color:#1f2c4c;font-weight:600;'>{c}</th>"
    html += "</tr>"
    for idx, row in df_elem.iterrows():
        is_total = str(row["Element Type"]).strip().upper() == "TOTAL"
        bg = "#eef1f6" if is_total else ("#f4f6f9" if idx % 2 == 0 else "#ffffff")
        w = "700" if is_total else "500"
        html += f"<tr style='background-color:{bg};'>"
        html += f"<td style='padding:8px;border:1px solid #c9ced6;font-weight:{w};color:#1f2c4c;text-align:left;padding-left:12px;'>{row['Element Type']}</td>"
        for c in ["Open", "Closed", "Pending", "Minor", "Major", "Critical"]:
            html += f"<td style='padding:8px;border:1px solid #c9ced6;font-weight:{w};color:#2c3e50;'>{fmt_num(row[c])}</td>"
        html += "</tr>"
    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

def render_category_table(df_cat):
    html = "<table style='width:100%; border-collapse:collapse; text-align:center; border:1px solid #c9ced6;'>"
    html += "<tr>" + "".join(
        f"<th style='background-color:#1f2c4c;color:#ffffff;padding:8px;border:1px solid #c9ced6;font-weight:600;'>{c}</th>"
        for c in df_cat.columns) + "</tr>"
    for idx, row in df_cat.iterrows():
        is_total = str(row["Category"]).strip().upper() == "TOTAL"
        bg = "#eef1f6" if is_total else ("#f4f6f9" if idx % 2 == 0 else "#ffffff")
        w = "700" if is_total else "500"
        html += f"<tr style='background-color:{bg};'>"
        html += f"<td style='padding:8px;border:1px solid #c9ced6;font-weight:{w};color:#1f2c4c;text-align:left;padding-left:12px;'>{row['Category']}</td>"
        for c in df_cat.columns[1:]:
            val = row[c]
            display_val = f"{val:.1f}%" if c == "% of Total" else fmt_num(val)
            color = "#b03a2e" if c == "Critical" and isinstance(val, (int, float)) and val > 0 else "#2c3e50"
            html += f"<td style='padding:8px;border:1px solid #c9ced6;font-weight:{w};color:{color};'>{display_val}</td>"
        html += "</tr>"
    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

# ============================================================
# SIDEBAR - FORECAST SETTINGS
# ============================================================
st.sidebar.header("📈 Forecast Settings")
forecast_weeks = st.sidebar.slider("Forecast horizon (weeks)", min_value=0, max_value=12, value=6, step=1)

# ============================================================
# SECTION 1: EXECUTIVE SUMMARY - 100% LIVE FROM DATA SHEET
# ============================================================
st.header("📌 Executive Summary")
st.caption("All figures below are calculated live from the **Data** sheet. The Dashboard sheet (if present) is not used.")

summary = compute_live_summary(df_data_full)

c1, c2, c3 = st.columns(3)
with c1: kpi_card("OPEN DEFECTS", summary["open"], "#b03a2e")
with c2: kpi_card("PENDING CONFIRMATION", summary["pending"], "#9a6a06")
with c3: kpi_card("CLOSED DEFECTS", summary["closed"], "#1e7e45")

st.markdown("####")
left, right = st.columns([1, 1.3])

with left:
    st.subheader("Status / Severity")
    render_severity_table(summary["severity_table"])
    st.markdown("####")
    st.subheader("Element Type")
    render_element_table(summary["element_table"])

with right:
    hist, forecast_df, total_defects = compute_dynamic_burndown(df_data_full, forecast_periods=forecast_weeks)
    if hist is not None:
        render_dynamic_burndown_chart(hist, forecast_df)
        st.caption(
            "Solid areas = actual data, computed live from **Status**, **Date Open** and **Date Closed** "
            "in the Data sheet. Dashed/lighter areas = forecast based on the historical closure trend. "
            "Re-upload the Excel file after making changes in Data to refresh this chart."
        )
    else:
        st.info("Not enough data with valid **Date Open** values to build the trend chart.")

st.markdown("---")

# ============================================================
# SECTION 2: DETAILED ANALYSIS
# ============================================================
st.header("🔍 Detailed Analysis")

st.sidebar.header("🔎 Filters (Detailed Analysis)")

def multiselect_filter(label, col):
    if col in df_data_full.columns:
        options = sorted([o for o in df_data_full[col].dropna().unique().tolist()])
        return st.sidebar.multiselect(label, options, default=options)
    return None

type_sel = multiselect_filter("Type", "Type")
category_sel = multiselect_filter("Category", "Category")
status_sel = multiselect_filter("Status", "Status")
severity_sel = multiselect_filter("Severity", "Severity")
responsible_sel = multiselect_filter("Responsible", "Responsible")

mask = pd.Series(True, index=df_data_full.index)
if type_sel is not None: mask &= df_data_full["Type"].isin(type_sel)
if category_sel is not None: mask &= df_data_full["Category"].isin(category_sel)
if status_sel is not None: mask &= df_data_full["Status"].isin(status_sel)
if severity_sel is not None: mask &= df_data_full["Severity"].isin(severity_sel)
if responsible_sel is not None and "Responsible" in df_data_full.columns:
    mask &= df_data_full["Responsible"].isin(responsible_sel) | df_data_full["Responsible"].isna()

if "Date Open" in df_data_full.columns and df_data_full["Date Open"].notna().any():
    min_date = df_data_full["Date Open"].min().date()
    max_date = df_data_full["Date Open"].max().date()
    date_range = st.sidebar.date_input("Opening Date Range", value=(min_date, max_date),
                                        min_value=min_date, max_value=max_date)
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
        mask &= (df_data_full["Date Open"].dt.date >= start) & (df_data_full["Date Open"].dt.date <= end)

df_f = df_data_full[mask].copy()
st.sidebar.markdown("---")
st.sidebar.write(f"**Records displayed:** {len(df_f)} / {len(df_data_full)}")

COLOR_STATUS = {"Open": "#b03a2e", "Closed": "#1e7e45", "Confirmation pending": "#d9a406"}
COLOR_SEV = {"Minor": "#3a7ab0", "Major": "#d9a406", "Critical": "#b03a2e"}

c1, c2 = st.columns(2)
with c1:
    st.subheader("Status Distribution")
    status_counts = df_f["Status"].value_counts().reset_index()
    status_counts.columns = ["Status", "Count"]
    fig = px.pie(status_counts, names="Status", values="Count", hole=0.45, color="Status", color_discrete_map=COLOR_STATUS)
    fig.update_traces(textinfo="percent+value")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("Severity Distribution")
    if "Severity" in df_f.columns:
        sev_counts = df_f["Severity"].value_counts().reset_index()
        sev_counts.columns = ["Severity", "Count"]
        fig2 = px.bar(sev_counts, x="Severity", y="Count", color="Severity", text="Count", color_discrete_map=COLOR_SEV)
        fig2.update_layout(showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

c3, c4 = st.columns(2)
with c3:
    st.subheader("Status by Element Type")
    type_status = df_f.groupby(["Type", "Status"]).size().reset_index(name="Count")
    fig3 = px.bar(type_status, x="Type", y="Count", color="Status", barmode="stack", color_discrete_map=COLOR_STATUS)
    st.plotly_chart(fig3, use_container_width=True)

with c4:
    st.subheader("Top 15 Stations with Most Defects")
    if "Station" in df_f.columns:
        station_counts = df_f["Station"].value_counts().head(15).reset_index()
        station_counts.columns = ["Station", "Count"]
        fig4 = px.bar(station_counts, x="Count", y="Station", orientation="h", text="Count",
                      color="Count", color_continuous_scale="Reds")
        fig4.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
        st.plotly_chart(fig4, use_container_width=True)

st.markdown("---")
st.subheader("📂 Category Analysis")
st.caption("Breakdown of defects by root-cause category (e.g. Acceleration / Mechanical, Sensors, Parametrization).")

if "Category" in df_f.columns and df_f["Category"].notna().any():
    cat_base = df_f.dropna(subset=["Category"]).copy()
    cat_base["StatusNorm"] = cat_base["Status"].apply(
        lambda x: "Open" if str(x).strip().lower() == "open"
        else ("Closed" if str(x).strip().lower() == "closed" else "Confirmation Pending")
    )
    cat_summary = cat_base.groupby("Category").agg(
        Total=("Category", "size"),
        Open=("StatusNorm", lambda s: (s == "Open").sum()),
        Confirmation_Pending=("StatusNorm", lambda s: (s == "Confirmation Pending").sum()),
        Closed=("StatusNorm", lambda s: (s == "Closed").sum()),
        Critical=("Severity", lambda s: (s == "Critical").sum())
    ).reset_index().rename(columns={"Confirmation_Pending": "Confirmation Pending"})

    cat_summary["% of Total"] = (cat_summary["Total"] / cat_summary["Total"].sum() * 100).round(1)
    cat_summary = cat_summary.sort_values("Total", ascending=False).reset_index(drop=True)

    total_row = {
        "Category": "TOTAL", "Total": cat_summary["Total"].sum(), "Open": cat_summary["Open"].sum(),
        "Confirmation Pending": cat_summary["Confirmation Pending"].sum(), "Closed": cat_summary["Closed"].sum(),
        "Critical": cat_summary["Critical"].sum(), "% of Total": 100.0
    }
    cat_summary_display = pd.concat([cat_summary, pd.DataFrame([total_row])], ignore_index=True)
    cat_summary_display = cat_summary_display[["Category", "Total", "% of Total", "Open", "Confirmation Pending", "Closed", "Critical"]]

    col_tbl, col_charts = st.columns([1, 1.3])
    with col_tbl:
        render_category_table(cat_summary_display)
    with col_charts:
        fig_donut = px.pie(cat_summary, names="Category", values="Total", hole=0.45,
                            title="Defect Volume Share by Category",
                            color_discrete_sequence=["#2f3f5c", "#3a7ab0", "#8fa8c4", "#c9ced6"])
        fig_donut.update_traces(textinfo="percent+value")
        st.plotly_chart(fig_donut, use_container_width=True)

        cat_status_melt = cat_summary.melt(id_vars="Category", value_vars=["Open", "Confirmation Pending", "Closed"],
                                            var_name="Status", value_name="Count")
        fig_cat_status = px.bar(cat_status_melt, x="Category", y="Count", color="Status", barmode="stack",
                                 title="Resolution Status by Category", color_discrete_map=COLOR_STATUS)
        st.plotly_chart(fig_cat_status, use_container_width=True)
else:
    st.info("The Category column is not available or has no data in the current filtered selection.")

if "Responsible" in df_f.columns and df_f["Responsible"].notna().any():
    st.markdown("---")
    st.subheader("👷 Workload by Responsible")
    resp = df_f.dropna(subset=["Responsible"]).groupby(["Responsible", "Status"]).size().reset_index(name="Count")
    fig6 = px.bar(resp, x="Responsible", y="Count", color="Status", barmode="stack", color_discrete_map=COLOR_STATUS)
    st.plotly_chart(fig6, use_container_width=True)

st.markdown("---")
st.subheader("📋 Record Details")
search = st.text_input("Search in Conveyor / Station / Comments")
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
    st.download_button("⬇️ Download Filtered CSV", data=csv, file_name="filtered_defects.csv", mime="text/csv")
with col_dl2:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df_show.to_excel(writer, index=False, sheet_name="Data")
    st.download_button("⬇️ Download Filtered Excel", data=buffer.getvalue(), file_name="filtered_defects.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
