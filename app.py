from io import BytesIO
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title='Plant Defect Dashboard Automation', layout='wide')

st.title('📊 Plant Defect Management Dashboard')
st.markdown(
    'Automatización del reporte de defectos, tabla resumen y gráfico acumulado.'
)

st.sidebar.header('1. Carga de Archivo')
uploaded_file = st.sidebar.file_uploader(
    'Sube tu archivo Excel (.xlsx)', type=['xlsx', 'xls']
)

if uploaded_file is not None:
  try:
    df = pd.read_excel(uploaded_file, sheet_name=0)
    st.sidebar.success('¡Archivo cargado con éxito!')
  except Exception as e:
    st.error(f'Error al leer el archivo: {e}')
    st.stop()

  with st.expander('🔍 Vista previa de los datos detectados'):
    st.dataframe(df.head(5))

  columns = list(df.columns)
  st.sidebar.header('2. Mapeo de Columnas')

  default_date = 'Date measured' if 'Date measured' in columns else columns[0]
  default_status = 'Fix Status' if 'Fix Status' in columns else columns[0]
  default_type = 'Type' if 'Type' in columns else columns[0]

  date_col = st.sidebar.selectbox(
      'Columna de Fecha (Date measured)',
      columns,
      index=columns.index(default_date) if default_date in columns else 0,
  )
  status_col = st.sidebar.selectbox(
      'Columna de Estatus (Fix Status)',
      columns,
      index=columns.index(default_status) if default_status in columns else 0,
  )
  type_col = st.sidebar.selectbox(
      'Columna de Tipo/Categoría (Type)',
      columns,
      index=columns.index(default_type) if default_type in columns else 0,
  )

  try:
    # Procesar fechas y extraer semanas
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.dropna(subset=[date_col])
    df['Week'] = df[date_col].dt.strftime('W%V')


    # Normalizar estatus a los 3 estados requeridos
    def map_status(val):
      val_str = str(val).strip().lower()
      if 'clos' in val_str:
        return 'Closed'
      elif 'rem' in val_str or 'pend' in val_str or 'req' in val_str:
        return 'Resolved'
      else:
        return 'Assigned'


    df['Clean_Status'] = df[status_col].apply(map_status)

    # --- SECCIÓN 1: Tabla Resumen por Tipo y Estatus ---
    st.markdown('### 📋 Resumen de Defectos por Tipo y Estatus')
    summary_table = pd.crosstab(
        df['Clean_Status'], df[type_col], margins=True, margins_name='Total'
    )
    row_order = [
        r for r in ['Assigned', 'Resolved', 'Closed'] if r in summary_table.index
    ]
    if 'Total' in summary_table.index:
      row_order.append('Total')
    summary_table = summary_table.reindex(index=row_order, fill_value=0)
    st.dataframe(summary_table, use_container_width=True)

    # --- SECCIÓN 2: Gráfico de Áreas Acumuladas ---
    st.markdown(
        '### 📈 Assigned, resolved and closed defects cumulated over time'
    )

    pivot = pd.pivot_table(
        df,
        index='Week',
        columns='Clean_Status',
        values=date_col,
        aggfunc='count',
        fill_value=0,
    )
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

    # Colores corporativos idénticos al dashboard
    color_closed = '#556B2F'  # Verde oliva
    color_resolved = '#E69500'  # Naranja / Ámbar
    color_assigned = '#A00000'  # Rojo vino

    ax.fill_between(
        weeks,
        0,
        y_closed,
        label='Closed cumulated',
        color=color_closed,
        alpha=0.9,
    )
    ax.fill_between(
        weeks,
        y_closed,
        y_resolved,
        label='Resolved cumulated',
        color=color_resolved,
        alpha=0.9,
    )
    ax.fill_between(
        weeks,
        y_resolved,
        y_assigned,
        label='Assigned cumulated',
        color=color_assigned,
        alpha=0.9,
    )

    ax.plot(weeks, y_closed, color='black', linewidth=0.8)
    ax.plot(weeks, y_resolved, color='black', linewidth=0.8)
    ax.plot(weeks, y_assigned, color='black', linewidth=0.8)

    ax.yaxis.tick_right()
    ax.yaxis.set_label_position('right')
    ax.grid(axis='x', linestyle='--', alpha=0.3)
    ax.grid(axis='y', linestyle='--', alpha=0.3)

    ax.legend(
        loc='upper center',
        bbox_to_anchor=(0.5, -0.15),
        ncol=3,
        frameon=False,
        fontsize=10,
    )
    plt.xticks(rotation=45)
    plt.tight_layout()

    st.pyplot(fig)

    # Botón para descargar el gráfico listo para tus reportes
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
    buf.seek(0)
    st.sidebar.markdown('---')
    st.sidebar.download_button(
        label='📥 Descargar Gráfica (PNG)',
        data=buf,
        file_name='defects_cumulative_chart.png',
        mime='image/png',
    )

  except Exception as e:
    st.error(f'Ocurrió un error al procesar los datos: {e}')
else:
  st.info(
      '👈 Por favor, carga tu archivo Excel en la barra lateral para generar'
      ' el reporte.'
  )
