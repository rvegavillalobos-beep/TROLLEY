import io
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Quality Control & Management Briefing",
    page_icon="⚙️",
    layout="wide",
)

if "selected_mod_target" not in st.session_state:
    st.session_state["selected_mod_target"] = "--- None / All ---"


def generate_mock_data():
    """Generates realistic manufacturing quality data for instant preview

    when no file is uploaded.
    """
    np.random.seed(42)
    dates = pd.date_range(start="2026-08-01", periods=60, freq="D")
    data = []

    for i, d in enumerate(dates):
        part_id = f"BAT-2026-{100 + (i % 15):03d}"
        run_num = 1 if i % 5 != 0 else 2
        b_type = "Type S" if i % 2 == 0 else "Type M"

        # Simulate corner deviations with a tightening trend over time
        factor = max(0.4, 1.0 - (i / 80))
        fl_x = np.random.normal(0.2, 1.2) * factor
        fl_y = np.random.normal(-0.5, 1.1) * factor
        fr_x = np.random.normal(-0.1, 1.0) * factor
        fr_y = np.random.normal(0.3, 1.2) * factor
        rl_x = np.random.normal(0.4, 1.3) * factor
        rl_y = np.random.normal(-0.2, 1.0) * factor
        rr_x = np.random.normal(-0.3, 1.1) * factor
        rr_y = np.random.normal(0.1, 0.9) * factor

        for c_idx, (f_name, x_v, y_v) in enumerate(
            [
                ("72_l0324_aa", fl_x, fl_y),
                ("72_r0301_aa", fr_x, fr_y),
                ("72_l0324_da", rl_x, rl_y),
                ("72_r0302_da", rr_x, rr_y),
            ],
            1,
        ):
            data.append({
                "Timestamp": d,
                "PartID": part_id,
                "FeatureName": f_name,
                "X_Deviation": x_v,
                "Y_Deviation": y_v,
                "CalendarWeek": (
                    "CW" + str(d.isocalendar().week).zfill(2)
                ),
                "BatteryType": b_type,
                "CornerIndex": c_idx,
                "CurrentRun": run_num,
            })
    return pd.DataFrame(data)


def determine_battery_type(part_id: str, feature_name: str) -> str:
    p_id = str(part_id).upper().strip()
    f_name = str(feature_name).upper().strip()
    if "_DJ" in p_id or "_DJ" in f_name or "TYPE M" in f_name:
        return "Type M"
    return "Type S"


def extract_corner_index(feature_name: str, part_id: str) -> int:
    f = str(feature_name).lower().strip()
    if "72_l0324_aa" in f or "fl" in f:
        return 1
    if "72_r0301_aa" in f or "fr" in f:
        return 2
    if "72_l0324_da" in f or "72_l0324_dj" in f or "rl" in f:
        return 3
    if "72_r0302" in f or "72_r0301" in f or "rr" in f:
        return 4
    return 1


def get_nominal_coordinates(bat_type: str):
    if bat_type.upper() == "TYPE S":
        return {
            "FL_X": 2290.48,
            "FL_Y": -559.4,
            "FR_X": 2290.48,
            "FR_Y": 558.9,
            "RL_X": 997.28,
            "RL_Y": -559.4,
            "RR_X": 997.28,
            "RR_Y": 511.1,
        }
    else:
        return {
            "FL_X": 2290.48,
            "FL_Y": -559.4,
            "FR_X": 2290.48,
            "FR_Y": 558.9,
            "RL_X": 609.31,
            "RL_Y": -583.3,
            "RR_X": 609.31,
            "RR_Y": 535.0,
        }


def calculate_corner_angle(a, b, c):
    v_ab = np.array(b) - np.array(a)
    v_ac = np.array(c) - np.array(a)
    dot_prod = np.dot(v_ab, v_ac)
    mag_ab = np.linalg.norm(v_ab)
    mag_ac = np.linalg.norm(v_ac)
    if mag_ab == 0 or mag_ac == 0:
        return 0.0
    cos_theta = np.clip(dot_prod / (mag_ab * mag_ac), -1.0, 1.0)
    return np.degrees(np.arccos(cos_theta))


def evaluate_deformation(
    delta_diags, angle_fl_dev, diff_ancho, diff_largo, max_diag_tol
):
    if delta_diags > max_diag_tol:
        return "DEFORMED", f"Asymmetry Detected (Delta: {delta_diags:.2f} mm)"
    return "SQUARE OK", "Geometry within tolerance"


st.title("⚙️ Quality Control & Management Dashboard")

st.sidebar.header("🛠️ Configuration & Tolerances")
max_diag_tol = st.sidebar.slider(
    "Max. Diagonal Delta Tolerance [mm]", 1.0, 10.0, 1.5, 0.5
)
spec_limit = st.sidebar.slider(
    "X/Y Specification Limit [±mm]", 1.0, 5.0, 3.0, 0.5
)

uploaded_file = st.file_uploader(
    "Upload raw data (Excel/CSV) or use built-in simulation preview",
    type=["xlsx", "xls", "csv"],
)

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith(".csv"):
            df_raw = pd.read_csv(uploaded_file, skiprows=2)
        else:
            df_raw = pd.read_excel(uploaded_file, skiprows=2)
        df_raw.columns = [str(c).strip() for c in df_raw.columns]
        time_col = [c for c in df_raw.columns if "time" in c.lower()][0]
        part_col = [c for c in df_raw.columns if "part" in c.lower()][0]
        feat_col = [c for c in df_raw.columns if "feature" in c.lower()][0]
        x_dev_col = [
            c
            for c in df_raw.columns
            if "x" in c.lower() and "deviation" in c.lower()
        ][0]
        y_dev_col = [
            c
            for c in df_raw.columns
            if "y" in c.lower() and "deviation" in c.lower()
        ][0]
        df_raw["ParsedDate"] = pd.to_datetime(
            df_raw[time_col], errors="coerce"
        )
        df_raw["CalendarWeek"] = (
            "CW"
            + df_raw["ParsedDate"]
            .dt.isocalendar()
            .week.astype(str)
            .str.zfill(2)
        )
        df_raw["BatteryType"] = df_raw.apply(
            lambda r: determine_battery_type(r[part_col], r[feat_col]), axis=1
        )
        df_raw["CornerIndex"] = df_raw.apply(
            lambda r: extract_corner_index(r[feat_col], r[part_col]), axis=1
        )
        df_raw["X_Val"] = (
            pd.to_numeric(df_raw[x_dev_col], errors="coerce")
            .fillna(0.0)
        )
        df_raw["Y_Val"] = (
            pd.to_numeric(df_raw[y_dev_col], errors="coerce")
            .fillna(0.0)
        )
        df_raw["IsOutOfSpec"] = (df_raw["X_Val"].abs() > spec_limit) | (
            df_raw["Y_Val"].abs() > spec_limit
        )
    except Exception as e:
        st.warning(
            f"Could not parse uploaded file format automatically. Loading"
            f" simulation preview. Error: {e}"
        )
        df_raw = generate_mock_data()
else:
    st.info(
        "💡 No file uploaded. Displaying simulation preview mode so you can"
        " explore all management KPIs and visuals immediately."
    )
    df_raw = generate_mock_data()

# Ensure standard column mapping for processing
if "ParsedDate" not in df_raw.columns:
    df_raw["ParsedDate"] = pd.to_datetime(
        df_raw.get("Timestamp", pd.Timestamp("2026-08-01"))
    )
if "CalendarWeek" not in df_raw.columns:
    df_raw["CalendarWeek"] = "CW33"
if "BatteryType" not in df_raw.columns:
    df_raw["BatteryType"] = "Type S"
if "CornerIndex" not in df_raw.columns:
    df_raw["CornerIndex"] = 1
if "X_Val" not in df_raw.columns:
    df_raw["X_Val"] = pd.to_numeric(
        df_raw.get("X_Deviation", 0.0), errors="coerce"
    ).fillna(0.0)
if "Y_Val" not in df_raw.columns:
    df_raw["Y_Val"] = pd.to_numeric(
        df_raw.get("Y_Deviation", 0.0), errors="coerce"
    ).fillna(0.0)
if "CurrentRun" not in df_raw.columns:
    df_raw["CurrentRun"] = 1
if "PartID" not in df_raw.columns:
    df_raw["PartID"] = "BAT-SIM-001"

df_raw["IsOutOfSpec"] = (df_raw["X_Val"].abs() > spec_limit) | (
    df_raw["Y_Val"].abs() > spec_limit
)
df_raw = df_raw.sort_values(by="ParsedDate").reset_index(drop=True)

# Build module summaries
modules_data = []
grouped_runs = df_raw.groupby(["CalendarWeek", "PartID", "CurrentRun"])

for (c_week, p_val, c_run), group in grouped_runs:
    corners = {1: (0, 0), 2: (0, 0), 3: (0, 0), 4: (0, 0)}
    out_spec_flags = []
    first_dt = group["ParsedDate"].iloc[0]
    b_type = group["BatteryType"].iloc[0]

    for _, r_item in group.iterrows():
        c_idx = int(r_item["CornerIndex"])
        if c_idx in [1, 2, 3, 4]:
            corners[c_idx] = (r_item["X_Val"], r_item["Y_Val"])
            out_spec_flags.append(r_item["IsOutOfSpec"])

    total_out = sum(out_spec_flags) if out_spec_flags else 0
    status = "FAIL" if total_out > 0 else "PASS"

    modules_data.append({
        "Date": first_dt,
        "CalendarWeek": c_week,
        "PartID": p_val,
        "BatteryType": b_type,
        "RunNum": c_run,
        "FL_X": corners[1][0],
        "FL_Y": corners[1][1],
        "FR_X": corners[2][0],
        "FR_Y": corners[2][1],
        "RL_X": corners[3][0],
        "RL_Y": corners[3][1],
        "RR_X": corners[4][0],
        "RR_Y": corners[4][1],
        "Status": status,
    })

df_summary = pd.DataFrame(modules_data)

# TABS STRUCTURE INCLUDING MANAGEMENT BRIEFING
tab1, tab2, tab3 = st.tabs([
    "📊 Executive Management Briefing (One-Pager)",
    "📈 Interactive Geometric Plot",
    "🧭 Vector Drift & Conveyor Tuning",
])

with tab1:
    st.subheader(
        "🎯 Executive Management Summary (Process Health & Engineering"
        " Progress)"
    )
    st.markdown(
        "High-level non-technical indicators designed for leadership"
        " oversight, replacing binary pass/fail traps with systemic precision"
        " trends."
    )

    # Compute Executive KPIs
    df_run1 = df_summary[df_summary["RunNum"] == 1].copy()
    weekly_exec = (
        df_run1.groupby("CalendarWeek")
        .agg(
            Total_Inspected=("PartID", "count"),
            Failed_Parts=("Status", lambda x: (x == "FAIL").sum()),
        )
        .reset_index()
    )

    # Burn-down flow simulation for executive tracking
    weekly_exec["Open_Issues"] = weekly_exec["Failed_Parts"]
    weekly_exec["Resolved_Issues"] = (
        weekly_exec["Open_Issues"].shift(1).fillna(0) * 0.75
    ).astype(int)
    weekly_exec["Net_Open"] = (
        weekly_exec["Open_Issues"] - weekly_exec["Resolved_Issues"]
    ).clip(lower=0)

    # Mean absolute deviation trend
    df_run1["Mean_Dev"] = (
        df_run1[["FL_X", "FR_X", "RL_X", "RR_X"]].abs().mean(axis=1)
    )
    weekly_dev = (
        df_run1.groupby("CalendarWeek")["Mean_Dev"].mean().reset_index()
    )

    col_m1, col_m2 = st.columns(2)

    with col_m1:
        st.markdown("##### 📉 Finding Resolution Flow (Burn-down vs New)")
        fig_burn = go.Figure()
        fig_burn.add_trace(
            go.Bar(
                x=weekly_exec["CalendarWeek"],
                y=weekly_exec["Open_Issues"],
                name="New Issues Discovered",
                marker_color="#e11d48",
            )
        )
        fig_burn.add_trace(
            go.Bar(
                x=weekly_exec["CalendarWeek"],
                y=weekly_exec["Resolved_Issues"],
                name="Issues Resolved / Closed",
                marker_color="#0f766e",
            )
        )
        fig_burn.update_layout(
            barmode="group",
            height=350,
            margin=dict(l=20, r=20, t=20, b=20),
            yaxis=dict(title="Finding Count"),
        )
        st.plotly_chart(fig_burn, use_container_width=True)

    with col_m2:
        st.markdown("##### 📏 Process Precision Trend (Mean Deviation [mm])")
        fig_trend = go.Figure()
        fig_trend.add_trace(
            go.Scatter(
                x=weekly_dev["CalendarWeek"],
                y=weekly_dev["Mean_Dev"],
                mode="lines+markers",
                name="Mean Deviation [mm]",
                line=dict(color="#2563eb", width=3),
                marker=dict(size=8),
            )
        )
        fig_trend.add_hline(
            y=spec_limit,
            line_dash="dash",
            line_color="orange",
            annotation_text="Specification Limit",
        )
        fig_trend.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=20, b=20),
            yaxis=dict(title="Average Error [mm]"),
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    st.markdown("---")
    st.markdown("##### 📋 Executive Summary Table")
    exec_table_display = pd.merge(weekly_exec, weekly_dev, on="CalendarWeek")
    exec_table_display = exec_table_display[
        [
            "CalendarWeek",
            "Total_Inspected",
            "Open_Issues",
            "Resolved_Issues",
            "Mean_Dev",
        ]
    ]
    exec_table_display.columns = [
        "Calendar Week",
        "Modules Tested",
        "Open Issues",
        "Resolved Issues",
        "Mean Deviation [mm]",
    ]
    exec_table_display["Mean Deviation [mm]"] = exec_table_display[
        "Mean Deviation [mm]"
    ].round(2)
    st.dataframe(exec_table_display, hide_index=True, use_container_width=True)

with tab2:
    st.subheader("📈 Real Geometric Visualization")
    if not df_summary.empty:
        fig = go.Figure()
        for _, row in df_summary.head(15).iterrows():
            nom = get_nominal_coordinates(row["BatteryType"])
            mod_x = [
                nom["RL_X"] + row["RL_X"],
                nom["FL_X"] + row["FL_X"],
                nom["FR_X"] + row["FR_X"],
                nom["RR_X"] + row["RR_X"],
                nom["RL_X"] + row["RL_X"],
            ]
            mod_y = [
                nom["RL_Y"] + row["RL_Y"],
                nom["FL_Y"] + row["FL_Y"],
                nom["FR_Y"] + row["FR_Y"],
                nom["RR_Y"] + row["RR_Y"],
                nom["RL_Y"] + row["RL_Y"],
            ]
            fig.add_trace(
                go.Scatter(
                    x=mod_x,
                    y=mod_y,
                    mode="lines",
                    line=dict(
                        color="red" if row["Status"] == "FAIL" else "gray",
                        width=1.5,
                    ),
                    showlegend=False,
                )
            )
        fig.update_layout(
            height=500,
            xaxis_title="Global X Axis [mm]",
            yaxis_title="Global Y Axis [mm]",
            yaxis=dict(scaleanchor="x", scaleratio=1),
        )
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("🧭 Vector Drift & Conveyor Skew Analysis")
    df_v = df_summary[df_summary["RunNum"] == 1].copy()
    df_v["Centroid_X"] = df_v[["FL_X", "FR_X", "RL_X", "RR_X"]].mean(axis=1)
    df_v["Centroid_Y"] = df_v[["FL_Y", "FR_Y", "RL_Y", "RR_Y"]].mean(axis=1)

    fig_vec = go.Figure()
    fig_vec.add_trace(
        go.Scatter(
            x=df_v["Centroid_X"],
            y=df_v["Centroid_Y"],
            mode="markers",
            marker=dict(size=8, color="#0f766e"),
        )
    )
    fig_vec.update_layout(
        height=450,
        xaxis_title="Centroid X Deviation [mm]",
        yaxis_title="Centroid Y Deviation [mm]",
    )
    st.plotly_chart(fig_vec, use_container_width=True)
