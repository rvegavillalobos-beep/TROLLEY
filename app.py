from io import BytesIO
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title='Defects Cumulative Chart Automation', layout='wide'
)

st.title('📊 Generador de Gráfico Acumulado de Defects')
st.markdown(
    'Sube tu archivo de Excel con la pestaña **Fault Status** para generar'
    ' automáticamente el gráfico de áreas acumuladas.'
)

# Sidebar para subida de archivos
st.sidebar.header('1. Carga de Archivo')
uploaded_file = st.sidebar.file_uploader(
    'Sube tu archivo Excel (.xlsx)', type=['xlsx', 'xls']
)

if uploaded_file is not None:
  try:
    # Leer el archivo Excel (puedes especificar la hoja si es necesario, por defecto lee la activa)
    df = pd.read_excel(uploaded_file, sheet_name=0)
    st.sidebar.success('¡Archivo cargado con éxito!')
  except Exception as e:
    st.error(f'Error al leer el archivo: {e}')
    st.stop()

  # Mostrar vista previa de los datos para confirmar
  with st.expander('🔍 Vista previa de los datos detectados'):
    st.dataframe(df.head(5))

  # Detectar automáticamente o permitir seleccionar las columnas basándonos en tu estructura
  columns = list(df.columns)

  st.sidebar.header('2. Configuración de Columnas')

  # Valores por defecto basados en tu imagen ('Date measured' y 'Fix Status')
  default_date = (
      'Date measured' if 'Date measured' in columns else columns[0]
  )
  default_status = 'Fix Status' if 'Fix Status' in columns else columns[0]

  date_col = st.sidebar.selectbox(
      'Columna de Fecha',
      columns,
      index=columns.index(default_date) if default_date in columns else 0,
  )
  status_col = st.sidebar.selectbox(
      'Columna de Estatus',
      columns,
      index=columns.index(default_status) if default_status in columns else 0,
  )

  try:
    # Procesar fechas y extraer semana del año (W07, W08, etc.)
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.dropna(
        subset=[date_col]
    )  # Eliminar filas sin fecha para evitar errores
    df['Week'] = df[date_col].dt.strftime('W%V')

    # Mapeo exacto según tus estados en 'Fix Status' (Open, Remeasure req, Closed)
    def map_status(val):
      val_str = str(val).strip().lower()
      if 'clos' in val_str:
        return 'Closed'  # Cerrados (Verde base)
      elif 'rem' in val_str or 'pend' in val_str or 'req' in val_str:
        return 'Resolved'  # Pendientes de confirmación / Remeasure (Naranja)
      else:
        return 'Assigned'  # Open / Encontrados (Rojo arriba)

    df['Clean_Status'] = df[status_col].apply(map_status)

    # Crear la tabla pivote agrupada por semana y estatus
    pivot = pd.pivot_table(
        df,
        index='Week',
        columns='Clean_Status',
        values=date_col,
        aggfunc='count',
        fill_value=0,
    )

    # Asegurar que existan las 3 columnas necesarias
    for col in ['Closed', 'Resolved', 'Assigned']:
      if col not in pivot.columns:
        pivot[col] = 0

    # Ordenar columnas para el gráfico apilado
    pivot = pivot[['Closed', 'Resolved', 'Assigned']]

    # Calcular acumulación histórica a lo largo de las semanas
    cumulative_pivot = pivot.cumsum()

    if cumulative_pivot.empty:
      st.warning(
          'No hay suficientes datos con fechas válidas para generar el gráfico.'
      )
      st.stop()

    # --- Generar Gráfico ---
    st.subheader(
        '📈 Assigned, resolved and closed defects cumulated over time'
    )

    fig, ax = plt.subplots(figsize=(11, 6), dpi=300)

    weeks = cumulative_pivot.index
    y_closed = cumulative_pivot['Closed']
    y_resolved = cumulative_pivot['Resolved'] + y_closed
    y_assigned = cumulative_pivot['Assigned'] + y_resolved

    # Colores corporativos idénticos a tu referencia visual
    color_closed = '#556B2F'  # Verde oliva (Closed)
    color_resolved = '#E69500'  # Naranja / Ámbar (Pendiente / Remeasure)
    color_assigned = '#A00000'  # Rojo vino (Open / Assigned)

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
        label='Resolved / Pending cumulated',
        color=color_resolved,
        alpha=0.9,
    )
    ax.fill_between(
        weeks,
        y_resolved,
        y_assigned,
        label='Assigned / Open cumulated',
        color=color_assigned,
        alpha=0.9,
    )

    # Líneas de contorno finas para mayor definición
    ax.plot(weeks, y_closed, color='black', linewidth=0.8)
    ax.plot(weeks, y_resolved, color='black', linewidth=0.8)
    ax.plot(weeks, y_assigned, color='black', linewidth=0.8)

    # Configuración estética (Eje Y a la derecha como tu ejemplo)
    ax.yaxis.tick_right()
    ax.yaxis.set_label_position('right')
    ax.grid(axis='x', linestyle='--', alpha=0.3)
    ax.grid(axis='y', linestyle='--', alpha=0.3)

    # Leyenda inferior centrada
    ax.legend(
        loc='upper center',
        bbox_to_anchor=(0.5, -0.18),
        ncol=3,
        frameon=False,
        fontsize=11,
    )

    plt.xticks(rotation=45)
    plt.tight_layout()

    # Mostrar gráfico en Streamlit
    st.pyplot(fig)

    # Botón de descarga de la gráfica en alta calidad
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
    st.error(f'Ocurrió un error al procesar el archivo: {e}')
else:
  st.info(
      '👈 Por favor, carga tu archivo de Excel en la barra lateral para'
      ' visualizar el reporte.'
  )
