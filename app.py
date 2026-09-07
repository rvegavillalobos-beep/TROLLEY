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

    date_col = 'Date Open' if 'Date Open' in df.columns else df.columns[6]
    status_col = 'Status' if 'Status' in df.columns else 'Status'
    type_col = 'Type' if 'Type' in df.columns else 'Type'
    severity_col = 'Severity' if 'Severity' in df.columns else 'Severity'

    try:
        # Process dates
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col])
        df['Week'] = df[date_col].dt.strftime('W%V')

        # Clean/Normalize categorical fields strictly
        df['Clean_Status'] = df[status_col].astype(str).str.strip().str.title()
        df['Element_Type'] = df[type_col].astype(str).str.strip().str.upper()
        df['Severity'] = df[severity_col].astype(str).str.strip().str.capitalize()

        status_order = ['Open', 'Confirmation Pending', 'Closed']
        severity_order = ['Minor', 'Major', 'Critical']

        st.markdown("---")

        # --- TABLE 1: General Matrix (Fix Status vs. Severity) matching exact image structure ---
        st.markdown("### General Defects Matrix (Status vs. Severity)")
        
        t1_data = pd.crosstab(df['Clean_Status'], df['Severity'], margins=True, margins_name="Total")
        
        # Exact row and col normalization for Table 1
        t1_rows = ['Open', 'Confirmation Pending', 'Closed', 'Total']
        t1_cols = ['Minor', 'Major', 'Critical', 'Total']
        t1_data = t1_data.reindex(index=t1_rows, columns=t1_cols, fill_value=0)

        # Render Table 1 using precise HTML styling matching the colors in the user's template
        t1_html = """
        <style>
        .matrix-table {
            border-collapse: collapse;
            font-family: sans-serif;
            font-size: 14px;
            text-align: center;
            margin-bottom: 20px;
        }
        .matrix-table th, .matrix-table td {
            border: 1px solid #000000;
            padding: 6px 12px;
        }
        .th-minor { background-color: #FFFF00; color: #000000; font-weight: bold; }
        .th-major { background-color: #FF0000; color: #FFFFFF; font-weight: bold; }
        .th-critical { background-color: #000000; color: #FFFFFF; font-weight: bold; }
        .th-total { background-color: #FFFFFF; color: #000000; font-weight: bold; }
        .row-header { background-color: #FFFFFF; font-weight: bold; text-align: left; }
        </style>
        <table class="matrix-table">
            <thead>
                <tr>
                    <th class="row-header"></th>
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

        # --- TABLE 2: Element Type Breakdown Matrix matching exact second image structure ---
        st.markdown("### Element Type Breakdown Matrix")

        t2_status = pd.crosstab(df['Element_Type'], df['Clean_Status'])
        t2_severity = pd.crosstab(df['Element_Type'], df['Severity'])
        
        # Explicit element types sequence from user template image
        explicit_types = ['TR', 'TL', 'TU', 'TQ', 'TH', 'TV', 'FC', 'Station']
        
        # Combine status & severity columns in the exact order requested
        t2_html = """
        <table class="matrix-table">
            <thead>
                <tr>
                    <th rowspan="2" class="row-header" style="vertical-align: middle; background-color: #FFFFFF;">Element Type</th>
                    <th colspan="3" style="background-color: #FFFFFF; border-bottom: 1px solid #000;">Status</th>
                    <th colspan="3" style="background-color: #FFFFFF; border-bottom: 1px solid #000;">Severity</th>
                </tr>
                <tr>
                    <th style="background-color: #92D050; color: #000000;">Open</th>
                    <th style="background-color: #FF0000; color: #FFFFFF;">Closed</th>
                    <th style="background-color: #FFC000; color: #000000;">Confirmation Pending</th>
                    <th class="th-minor">Minor</th>
                    <th class="th-major">Major</th>
                    <th class="th-critical">Critical</th>
                </tr>
            </thead>
            <tbody>
        """

        totals = {'Open': 0, 'Closed': 0, 'Confirmation Pending': 0, 'Minor': 0, 'Major': 0, 'Critical': 0}

        # Add explicit types present in data or template
        all_types = list(dict.fromkeys(explicit_types + list(df['Element_Type'].unique())))

        for etype in all_types:
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

        # TOTAL Row for Table 2
        t2_html += f"""
                <tr style="font-weight: bold;">
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
        
        pivot = pd.pivot_table(df, index='Week', columns='Clean_Status', values=date_col, aggfunc='count', fill_value=0)
        for s in status_order:
            if s not in pivot.columns: pivot[s] = 0
        pivot = pivot[status_order]
        cumulative_pivot = pivot.cumsum()

        fig, ax = plt.subplots(figsize=(11, 4.5), dpi=300)

        weeks = cumulative_pivot.index
        y_open = cumulative_pivot['Open']
        y_conf = cumulative_pivot['Confirmation Pending'] + y_open
        y_closed = cumulative_pivot['Closed'] + y_conf

        color_open = '#92D050'   # Green
        color_conf = '#FFC000'   # Yellow/Amber
        color_closed = '#FF0000' # Red

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
