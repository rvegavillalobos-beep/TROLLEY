from io import BytesIO
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Plant Defect Management Dashboard", layout="wide")

st.title("Plant Defect Management Dashboard")
st.markdown("Automated tracking system for industrial automation, conveyor lines, and installation defects.")

st.sidebar.header("1. File Upload")
uploaded_file = st.sidebar.file_uploader("Upload tracking Excel file (.xlsx)", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file, sheet_name=0)
        st.sidebar.success("File successfully loaded!")
    except Exception as e:
        st.error(f"Error reading file: {e}")
        st.stop()

    with st.expander("Data Preview"):
        st.dataframe(df.head(5))

    columns = list(df.columns)
    st.sidebar.header("2. Column Mapping")

    default_date = 'Date measured' if 'Date measured' in columns else columns[0]
    default_status = 'Fix Status' if 'Fix Status' in columns else columns[0]
    default_type = 'Type' if 'Type' in columns else (columns[2] if len(columns) > 2 else columns[0])
    default_severity = 'Magnitude [m/s^2]' if 'Magnitude [m/s^2]' in columns else (columns[1] if len(columns) > 1 else columns[0])

    date_col = st.sidebar.selectbox("Date Column", columns, index=columns.index(default_date) if default_date in columns else 0)
    status_col = st.sidebar.selectbox("Status Column", columns, index=columns.index(default_status) if default_status in columns else 0)
    type_col = st.sidebar.selectbox("Element Type Column", columns, index=columns.index(default_type) if default_type in columns else 0)
    severity_col = st.sidebar.selectbox("Severity Column", columns, index=columns.index(default_severity) if default_severity in columns else 0)

    try:
        # Process dates
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col])
        df['Week'] = df[date_col].dt.strftime('W%V')

        # Clean/Normalize categorical fields strictly to the 3 states & 3 severities
        def map_status(val):
            val_str = str(val).strip().lower()
            if 'clos' in val_str:
                return 'Closed'
            elif 'conf' in val_str or 'pend' in val_str:
                return 'Confirmation Pending'
            else:
                return 'Open'

        def map_severity(val):
            val_str = str(val).strip().lower()
            if 'crit' in val_str:
                return 'Critical'
            elif 'maj' in val_str:
                return 'Major'
            else:
                return 'Minor'

        df['Fix_Status'] = df[status_col].apply(map_status)
        df['Element_Type'] = df[type_col].astype(str).str.strip().str.upper()
        df['Severity'] = df[severity_col].apply(map_severity)

        status_order = ['Open', 'Confirmation Pending', 'Closed']
        severity_order = ['Minor', 'Major', 'Critical']

        st.markdown("---")

        # --- TABLE 1: General Matrix (Fix Status vs. Severity) ---
        st.markdown("### General Defects Matrix (Status vs. Severity)")
        
        t1_data = pd.crosstab(df['Fix_Status'], df['Severity'], margins=True, margins_name="Total")
        t1_rows = [r for r in status_order if r in t1_data.index]
        if 'Total' in t1_data.index: t1_rows.append('Total')
        t1_cols = [c for c in severity_order if c in t1_data.columns]
        if 'Total' in t1_data.columns: t1_cols.append('Total')
        t1_data = t1_data.reindex(index=t1_rows, columns=t1_cols, fill_value=0)

        # Render Table 1 with exact header styling matching reference image
        t1_html = f"""
        <style>
        .custom-table {{
            border-collapse: collapse;
            width: 100%;
            font-family: sans-serif;
            font-size: 14px;
            text-align: center;
        }}
        .custom-table th, .custom-table td {{
            border: 1px solid #b0bec5;
            padding: 8px 12px;
        }}
        .custom-table th {{
            color: #000000;
            font-weight: bold;
        }}
        .th-minor {{ background-color: #FFEE58; }}
        .th-major {{ background-color: #EF5350; color: #ffffff !important; }}
        .th-critical {{ background-color: #212121; color: #ffffff !important; }}
        .th-total {{ background-color: #CFD8DC; }}
        .row-header {{ background-color: #ECEFF1; font-weight: bold; text-align: left; }}
        </style>
        <table class="custom-table">
            <thead>
                <tr>
                    <th class="row-header">Fix Status</th>
                    <th class="th-minor">Minor</th>
                    <th class="th-major">Major</th>
                    <th class="th-critical">Critical</th>
                    <th class="th-total">Total</th>
                </tr>
            </thead>
            <tbody>
        """
        for r in t1_rows:
            t1_html += f"<tr><td class='row-header'>{r}</td>"
            for c in t1_cols:
                val = t1_data.loc[r, c] if r in t1_data.index and c in t1_data.columns else 0
                t1_html += f"<td>{val}</td>"
            t1_html += "</tr>"
        t1_html += "</tbody></table>"
        st.markdown(t1_html, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # --- TABLE 2: Element Type Breakdown Matrix (Status & Severity split) ---
        st.markdown("### Element Type Breakdown Matrix")

        t2_status = pd.crosstab(df['Element_Type'], df['Fix_Status'])
        t2_severity = pd.crosstab(df['Element_Type'], df['Severity'])
        
        # Combine both breakdowns side-by-side per element type
        types_list = sorted(list(df['Element_Type'].unique()))
        
        t2_html = f"""
        <table class="custom-table">
            <thead>
                <tr>
                    <th rowspan="2" class="row-header" style="vertical-align: middle;">Element Type</th>
                    <th colspan="3" style="background-color: #CFD8DC;">Status</th>
                    <th colspan="3" style="background-color: #CFD8DC;">Severity</th>
                </tr>
                <tr>
                    <th class="th-open" style="background-color: #81C784;">Open</th>
                    <th class="th-closed" style="background-color: #E57373;">Closed</th>
                    <th class="th-conf" style="background-color: #FFD54F;">Confirmation Pending</th>
                    <th class="th-minor">Minor</th>
                    <th class="th-major">Major</th>
                    <th class="th-critical">Critical</th>
                </tr>
            </thead>
            <tbody>
        """

        totals = {'Open': 0, 'Closed': 0, 'Confirmation Pending': 0, 'Minor': 0, 'Major': 0, 'Critical': 0}

        for etype in types_list:
            o_val = int(t2_status.loc[etype, 'Open']) if etype in t2_status.index and 'Open' in t2_status.columns else 0
            c_val = int(t2_status.loc[etype, 'Closed']) if etype in t2_status.index and 'Closed' in t2_status.columns else 0
            cp_val = int(t2_status.loc[etype, 'Confirmation Pending']) if etype in t2_status.index and 'Confirmation Pending' in t2_status.columns else 0
            
            min_val = int(t2_severity.loc[etype, 'Minor']) if etype in t2_severity.index and 'Minor' in t2_severity.columns else 0
            maj_val = int(t2_severity.loc[etype, 'Major']) if etype in t2_severity.index and 'Major' in t2_severity.columns else 0
            crit_val = int(t2_severity.loc[etype, 'Critical']) if etype in t2_severity.index and 'Critical' in t2_severity.columns else 0

            totals['Open'] += o_val
            totals['Closed'] += c_val
            totals['Confirmation Pending'] += cp_val
            totals['Minor'] += min_val
            totals['Major'] += maj_val
            totals['Critical'] += crit_val

            t2_html += f"""
                <tr>
                    <td class="row-header">{etype}</td>
                    <td>{o_val}</td>
                    <td>{c_val}</td>
                    <td>{cp_val}</td>
                    <td>{min_val}</td>
                    <td>{maj_val}</td>
                    <td>{crit_val}</td>
                </tr>
            """

        # TOTAL Row
        t2_html += f"""
                <tr style="font-weight: bold; background-color: #ECEFF1;">
                    <td class="row-header">TOTAL</td>
                    <td>{totals['Open']}</td>
                    <td>{totals['Closed']}</td>
                    <td>{totals['Confirmation Pending']}</td>
                    <td>{totals['Minor']}</td>
                    <td>{totals['Major']}</td>
                    <td>{totals['Critical']}</td>
                </tr>
            </tbody>
        </table>
        """
        st.markdown(t2_html, unsafe_allow_html=True)

        # --- SECTION 3: Cumulative Stacked Area Chart ---
        st.markdown("---")
        st.markdown("### Defects Cumulated Over Time")
        
        pivot = pd.pivot_table(df, index='Week', columns='Fix_Status', values=date_col, aggfunc='count', fill_value=0)
        for s in status_order:
            if s not in pivot.columns: pivot[s] = 0
        pivot = pivot[status_order]
        cumulative_pivot = pivot.cumsum()

        fig, ax = plt.subplots(figsize=(11, 4.5), dpi=300)

        weeks = cumulative_pivot.index
        y_open = cumulative_pivot['Open']
        y_conf = cumulative_pivot['Confirmation Pending'] + y_open
        y_closed = cumulative_pivot['Closed'] + y_conf

        color_open = '#C0392B'   # Red
        color_conf = '#F39C12'   # Amber / Yellow
        color_closed = '#27AE60' # Green

        ax.fill_between(weeks, 0, y_open, label='Open cumulated', color=color_open, alpha=0.9)
        ax.fill_between(weeks, y_open, y_conf, label='Confirmation Pending cumulated', color=color_conf, alpha=0.9)
        ax.fill_between(weeks, y_conf, y_closed, label='Closed cumulated', color=color_closed, alpha=0.9)

        ax.plot(weeks, y_open, color='black', linewidth=0.8)
        ax.plot(weeks, y_conf, color='black', linewidth=0.8)
        ax.plot(weeks, y_closed, color='black', linewidth=0.8)

        ax.yaxis.tick_right()
        ax.yaxis.set_label_position("right")
        ax.grid(axis='x', linestyle='--', alpha=0.3)
        ax.grid(axis='y', linestyle='--', alpha=0.3)

        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=3, frameon=False, fontsize=10)
        plt.xticks(rotation=45)
        plt.tight_layout()

        st.pyplot(fig)

        # Download button for chart
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=300, bbox_inches="tight")
        buf.seek(0)
        st.sidebar.markdown("---")
        st.sidebar.download_button(label="Download Chart (PNG)", data=buf, file_name="defects_cumulative_chart.png", mime="image/png")

    except Exception as e:
        st.error(f"Error processing data: {e}")
else:
    st.info("Please upload your Excel tracking file in the sidebar to generate the professional dashboard.")
