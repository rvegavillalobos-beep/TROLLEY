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

    # Standardized column mapping based on your explicit layout
    date_col = 'Date Open' if 'Date Open' in df.columns else df.columns[6]
    status_col = 'Status' if 'Status' in df.columns else 'Status'
    type_col = 'Type' if 'Type' in df.columns else 'Type'
    severity_col = 'Severity' if 'Severity' in df.columns else 'Severity'

    try:
        # Process dates
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col])
        df['Week'] = df[date_col].dt.strftime('W%V')

        # Clean/Normalize categorical fields
        df['Clean_Status'] = df[status_col].astype(str).str.strip().str.title()
        df['Element_Type'] = df[type_col].astype(str).str.strip().str.upper()
        df['Severity'] = df[severity_col].astype(str).str.strip().str.capitalize()

        status_order = ['Open', 'Confirmation pending', 'Closed']
        severity_order = ['Minor', 'Major', 'Critical']

        st.markdown("---")

        # --- TABLE 1: General Defects Matrix (Status vs. Severity) ---
        st.markdown("### General Defects Matrix (Status vs. Severity)")
        
        t1_data = pd.crosstab(df['Clean_Status'], df['Severity'], margins=True, margins_name="Total")
        t1_rows = [r for r in status_order if r in t1_data.index]
        if 'Total' in t1_data.index: t1_rows.append('Total')
        t1_cols = [c for c in severity_order if c in t1_data.columns]
        if 'Total' in t1_data.columns: t1_cols.append('Total')
        t1_data = t1_data.reindex(index=t1_rows, columns=t1_cols, fill_value=0)

        def style_table1(val):
            # Apply background colors to specific headers/cells for visual fidelity
            return ''

        # We style using pandas styler for a clean professional look
        styled_t1 = t1_data.style.background_gradient(cmap='YlOrRd', subset=pd.IndexSlice[['Open', 'Confirmation pending', 'Closed'], [c for c in severity_order if c in t1_data.columns]], low=0.1, high=0.5)
        st.dataframe(t1_data, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # --- TABLE 2: Element Type Breakdown Matrix ---
        st.markdown("### Element Type Breakdown Matrix")

        # Build pivot for Status and Severity per Element Type
        t2_status = pd.crosstab(df['Element_Type'], df['Clean_Status'])
        t2_severity = pd.crosstab(df['Element_Type'], df['Severity'])
        
        # Merge them into a single comprehensive dataframe matching your layout
        t2_combined = pd.concat([t2_status, t2_severity], axis=1)
        
        # Ensure all standard columns exist
        for col in status_order + severity_order:
            if col not in t2_combined.columns:
                t2_combined[col] = 0
                
        t2_combined = t2_combined[status_order + severity_order]
        
        # Append TOTAL row
        total_row = pd.DataFrame(t2_combined.sum(axis=0)).T
        total_row.index = ['TOTAL']
        t2_combined = pd.concat([t2_combined, total_row])

        st.dataframe(t2_combined, use_container_width=True)

        # --- SECTION 3: Cumulative Stacked Area Chart ---
        st.markdown("---")
        st.markdown("### Defects Cumulated Over Time")
        
        pivot = pd.pivot_table(df, index='Week', columns='Clean_Status', values=date_col, aggfunc='count', fill_value=0)
        for s in status_order:
            if s not in pivot.columns: pivot[s] = 0
        pivot = pivot[status_order]
        cumulative_pivot = pivot.cumsum()

        fig, ax = plt.subplots(figsize=(11, 4.5), dpi=300)

        weeks = cumulative_pivot.index
        y_open = cumulative_pivot['Open']
        y_conf = cumulative_pivot['Confirmation pending'] + y_open
        y_closed = cumulative_pivot['Closed'] + y_conf

        color_open = '#C0392B'   # Red (Open)
        color_conf = '#F39C12'   # Yellow/Amber (Confirmation pending)
        color_closed = '#27AE60' # Green (Closed)

        ax.fill_between(weeks, 0, y_open, label='Open cumulated', color=color_open, alpha=0.9)
        ax.fill_between(weeks, y_open, y_conf, label='Confirmation pending cumulated', color=color_conf, alpha=0.9)
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
