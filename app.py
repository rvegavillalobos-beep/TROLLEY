from io import BytesIO
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Plant Defect Management Dashboard", layout="wide")

st.title("📊 Plant Defect Management Dashboard")
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

    with st.expander("🔍 Data Preview"):
        st.dataframe(df.head(5))

    columns = list(df.columns)
    st.sidebar.header("2. Column Mapping")

    default_date = 'Date measured' if 'Date measured' in columns else columns[0]
    default_status = 'Fix Status' if 'Fix Status' in columns else columns[0]
    default_type = 'Type' if 'Type' in columns else (columns[2] if len(columns) > 2 else columns[0])
    default_severity = 'Magnitude [m/s^2]' if 'Magnitude [m/s^2]' in columns else (columns[1] if len(columns) > 1 else columns[0])

    date_col = st.sidebar.selectbox("Date Column", columns, index=columns.index(default_date) if default_date in columns else 0)
    status_col = st.sidebar.selectbox("Status Column", columns, index=columns.index(default_status) if default_status in columns else 0)
    type_col = st.sidebar.selectbox("Type Column (e.g., TL, TR, TQ)", columns, index=columns.index(default_type) if default_type in columns else 0)
    severity_col = st.sidebar.selectbox("Severity / Magnitude Column", columns, index=columns.index(default_severity) if default_severity in columns else 0)

    try:
        # Process dates
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col])
        df['Week'] = df[date_col].dt.strftime('W%V')

        # Normalize statuses
        def map_status(val):
            val_str = str(val).strip().lower()
            if 'clos' in val_str:
                return 'Closed'
            elif 'conf' in val_str or 'pend' in val_str or 'rem' in val_str or 'req' in val_str:
                return 'Resolved'
            else:
                return 'Assigned'

        df['Clean_Status'] = df[status_col].apply(map_status)
        df['Equipment_Type'] = df[type_col].astype(str).str.strip().str.upper()
        df['Severity'] = df[severity_col].astype(str).str.strip().str.capitalize()

        # --- SECTION 1: Hierarchical Defect Matrix (Type & Severity) ---
        st.markdown("### 📋 Defects Matrix by Status, Type, and Severity")
        
        # Create multi-index crosstab table grouped by Type and Severity
        matrix_table = pd.crosstab(
            df['Clean_Status'], 
            [df['Equipment_Type'], df['Severity']], 
            margins=True, 
            margins_name="Total"
        )
        
        # Ensure proper row order
        desired_rows = [r for r in ['Assigned', 'Resolved', 'Closed'] if r in matrix_table.index]
        if 'Total' in matrix_table.index:
            desired_rows.append('Total')
        matrix_table = matrix_table.reindex(index=desired_rows, fill_value=0)

        # Apply professional conditional styling
        def color_status_rows(row):
            if row.name == 'Assigned':
                return ['background-color: #FADBD8; color: #78281F; font-weight: bold'] * len(row)
            elif row.name == 'Resolved':
                return ['background-color: #FCF3CF; color: #7D6608; font-weight: bold'] * len(row)
            elif row.name == 'Closed':
                return ['background-color: #D4EFDF; color: #145A32; font-weight: bold'] * len(row)
            elif row.name == 'Total':
                return ['background-color: #EAEDED; color: #2C3E50; font-weight: bold'] * len(row)
            return [''] * len(row)

        styled_matrix = matrix_table.style.apply(color_status_rows, axis=1)
        st.dataframe(styled_matrix, use_container_width=True)

        # --- SECTION 2: Cumulative Stacked Area Chart ---
        st.markdown("### 📈 Assigned, Resolved and Closed Defects Cumulated Over Time")
        
        pivot = pd.pivot_table(df, index='Week', columns='Clean_Status', values=date_col, aggfunc='count', fill_value=0)
        for col in ['Closed', 'Resolved', 'Assigned']:
            if col not in pivot.columns:
                pivot[col] = 0
        pivot = pivot[['Closed', 'Resolved', 'Assigned']]
        cumulative_pivot = pivot.cumsum()

        fig, ax = plt.subplots(figsize=(11, 5.5), dpi=300)

        weeks = cumulative_pivot.index
        y_closed = cumulative_pivot['Closed']
        y_resolved = cumulative_pivot['Resolved'] + y_closed
        y_assigned = cumulative_pivot['Assigned'] + y_resolved

        # Corporate color palette
        color_closed = '#27AE60'   # Green (Closed)
        color_resolved = '#F39C12' # Amber (Confirmation pending)
        color_assigned = '#C0392B' # Red (Open)

        ax.fill_between(weeks, 0, y_closed, label='Closed cumulated', color=color_closed, alpha=0.9)
        ax.fill_between(weeks, y_closed, y_resolved, label='Resolved / Confirmation pending cumulated', color=color_resolved, alpha=0.9)
        ax.fill_between(weeks, y_resolved, y_assigned, label='Assigned / Open cumulated', color=color_assigned, alpha=0.9)

        ax.plot(weeks, y_closed, color='black', linewidth=0.8)
        ax.plot(weeks, y_resolved, color='black', linewidth=0.8)
        ax.plot(weeks, y_assigned, color='black', linewidth=0.8)

        ax.yaxis.tick_right()
        ax.yaxis.set_label_position("right")
        ax.grid(axis='x', linestyle='--', alpha=0.3)
        ax.grid(axis='y', linestyle='--', alpha=0.3)

        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=3, frameon=False, fontsize=10)
        plt.xticks(rotation=45)
        plt.tight_layout()

        st.pyplot(fig)

        # Download button for chart
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=300, bbox_inches="tight")
        buf.seek(0)
        st.sidebar.markdown("---")
        st.sidebar.download_button(label="📥 Download Chart (PNG)", data=buf, file_name="defects_cumulative_chart.png", mime="image/png")

    except Exception as e:
        st.error(f"Error processing data: {e}")
else:
    st.info("👈 Please upload your Excel tracking file in the sidebar to generate the professional dashboard.")
