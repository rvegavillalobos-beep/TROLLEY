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
    type_col = st.sidebar.selectbox("Conveyor / Station Type Column", columns, index=columns.index(default_type) if default_type in columns else 0)
    severity_col = st.sidebar.selectbox("Severity Category Column", columns, index=columns.index(default_severity) if default_severity in columns else 0)

    try:
        # Process dates
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col])
        df['Week'] = df[date_col].dt.strftime('W%V')

        # Clean/Normalize categorical fields
        df['Fix_Status'] = df[status_col].astype(str).str.strip().str.title()
        df['Equipment_Type'] = df[type_col].astype(str).str.strip().str.upper()
        df['Severity'] = df[severity_col].astype(str).str.strip().str.capitalize()

        # --- TABLE 1: General Matrix (Fix Status vs. Severity Categories + Totals) ---
        st.markdown("### 📋 Table 1: General Defects Matrix (Status vs. Severity)")
        
        table1 = pd.crosstab(
            df['Fix_Status'], 
            df['Severity'], 
            margins=True, 
            margins_name="Total"
        )
        
        # Style Table 1
        def color_table1(row):
            if row.name == 'Total':
                return ['background-color: #EAEDED; color: #2C3E50; font-weight: bold'] * len(row)
            return [''] * len(row)

        st.dataframe(table1.style.apply(color_table1, axis=1), use_container_width=True)

        # --- TABLE 2: Conveyor / Station Matrix (Equipment Type vs. Status & Severity) ---
        st.markdown("### 📋 Table 2: Conveyor / Station Breakdown Matrix")
        
        table2 = pd.crosstab(
            df['Equipment_Type'], 
            [df['Fix_Status'], df['Severity']], 
            margins=True, 
            margins_name="TOTAL"
        )
        
        st.dataframe(table2, use_container_width=True)

        # --- SECTION 3: Cumulative Stacked Area Chart ---
        st.markdown("### 📈 Defects Cumulated Over Time")
        
        pivot = pd.pivot_table(df, index='Week', columns='Fix_Status', values=date_col, aggfunc='count', fill_value=0)
        status_list = list(pivot.columns)
        cumulative_pivot = pivot.cumsum()

        fig, ax = plt.subplots(figsize=(11, 5.5), dpi=300)

        weeks = cumulative_pivot.index
        
        # Dynamically stack areas
        y_prev = np.zeros(len(weeks))
        colors = ['#C0392B', '#F39C12', '#27AE60', '#2980B9', '#8E44AD', '#34495E']
        
        for idx, col in enumerate(status_list):
            y_curr = y_prev + cumulative_pivot[col]
            color_val = colors[idx % len(colors)]
            ax.fill_between(weeks, y_prev, y_curr, label=f"{col} cumulated", color=color_val, alpha=0.9)
            ax.plot(weeks, y_curr, color='black', linewidth=0.8)
            y_prev = y_curr

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
