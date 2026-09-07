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
    type_col = st.sidebar.selectbox("Conveyor / Station Type Column", columns, index=columns.index(default_type) if default_type in columns else 0)
    severity_col = st.sidebar.selectbox("Severity Category Column", columns, index=columns.index(default_severity) if default_severity in columns else 0)

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
        df['Equipment_Type'] = df[type_col].astype(str).str.strip().str.upper()
        df['Severity'] = df[severity_col].apply(map_severity)

        # Enforce exact column order
        status_order = ['Open', 'Confirmation Pending', 'Closed']
        severity_order = ['Minor', 'Major', 'Critical']

        # --- SIDE-BY-SIDE LAYOUT FOR TABLES ---
        st.markdown("---")
        col_t1, col_t2 = st.columns(2)

        # TABLE 1: General Matrix (Fix Status vs. Severity Categories + Totals)
        with col_t1:
            st.markdown("### General Defects Matrix (Status vs. Severity)")
            table1 = pd.crosstab(
                df['Fix_Status'], 
                df['Severity'], 
                margins=True, 
                margins_name="Total"
            )
            
            # Reindex rows and columns cleanly
            row_idx = [r for r in status_order if r in table1.index]
            if 'Total' in table1.index: row_idx.append('Total')
            col_idx = [c for c in severity_order if c in table1.columns]
            if 'Total' in table1.columns: col_idx.append('Total')
            table1 = table1.reindex(index=row_idx, columns=col_idx, fill_value=0)

            # Styling table 1 with reference colors (Minor = Yellow, Major = Red, Critical = Black/Dark)
            def style_table1(val, col_name):
                if col_name == 'Minor':
                    return 'background-color: #FFF9C4; color: #000000; font-weight: bold;'
                elif col_name == 'Major':
                    return 'background-color: #FFCDD2; color: #000000; font-weight: bold;'
                elif col_name == 'Critical':
                    return 'background-color: #CFD8DC; color: #000000; font-weight: bold;'
                return ''

            st.dataframe(table1, use_container_width=True)

        # TABLE 2: Conveyor / Station Breakdown Matrix (Equipment Type vs. Status)
        with col_t2:
            st.markdown("### Conveyor / Station Breakdown Matrix")
            table2 = pd.crosstab(
                df['Equipment_Type'], 
                df['Fix_Status'], 
                margins=True, 
                margins_name="TOTAL"
            )
            
            # Reindex columns to Open, Confirmation Pending, Closed, TOTAL
            t2_cols = [c for c in status_order if c in table2.columns]
            if 'TOTAL' in table2.columns: t2_cols.append('TOTAL')
            table2 = table2.reindex(columns=t2_cols, fill_value=0)

            st.dataframe(table2, use_container_width=True)

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

        # Professional palette matching status colors
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
