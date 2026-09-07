import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 1. Cargar tu archivo de Excel
# Reemplaza 'tu_archivo.xlsx' con la ruta de tu documento
df = pd.read_excel('tu_archivo.xlsx')

# 2. Asegurarte de que la columna de fecha esté en formato datetime
# Supongamos que tu columna de fecha se llama 'Occurrence date' o similar
date_col = [
    c for c in df.columns if 'date' in c.lower() or 'fecha' in c.lower()
][0]
df[date_col] = pd.to_datetime(df[date_col])

# 3. Extraer la semana del año (ej: 'W07', 'W08')
df['Week'] = df[date_col].dt.strftime('W%V')

# 4. Mapear o normalizar los estados de tu columna de estatus (ej. 'Fix Status')
# Ajusta los nombres según aparezcan exactamente en tu Excel
status_col = [
    c for c in df.columns if 'status' in c.lower() or 'estado' in c.lower()
][1]  # Ajusta el índice si es necesario


# Función de categorización para alinear con: Assigned, Resolved, Closed
def map_status(val):
  val_str = str(val).strip().lower()
  if 'clos' in val_str:
    return 'Closed'
  elif 'resol' in val_str or 'pend' in val_str:  # O el criterio que uses
    return 'Resolved'
  else:
    return 'Assigned'


df['Clean_Status'] = df[status_col].apply(map_status)

# 5. Crear tabla pivote por Semana y Estado, y calcular acumulados
pivot = pd.pivot_table(
    df,
    index='Week',
    columns='Clean_Status',
    values=date_col,
    aggfunc='count',
    fill_value=0,
)

# Asegurar que existan las 3 columnas
for col in ['Assigned', 'Resolved', 'Closed']:
  if col not in pivot.columns:
    pivot[col] = 0

# Reordenar columnas para el apilado correcto (Closed abajo, Assigned arriba)
pivot = pivot[['Closed', 'Resolved', 'Assigned']]

# Calcular la acumulación histórica (cumulada a lo largo de las semanas)
cumulative_pivot = pivot.cumsum()

# 6. Graficar con el estilo corporativo
fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

weeks = cumulative_pivot.index
y_closed = cumulative_pivot['Closed']
y_resolved = cumulative_pivot['Resolved'] + y_closed
y_assigned = cumulative_pivot['Assigned'] + y_resolved

# Colores basados en tu referencia visual
color_closed = '#556B2F'  # Verde oliva oscuro
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

# Líneas divisorias para mayor nitidez
ax.plot(weeks, y_closed, color='black', linewidth=0.8)
ax.plot(weeks, y_resolved, color='black', linewidth=0.8)
ax.plot(weeks, y_assigned, color='black', linewidth=0.8)

# Configuración estética de ejes y títulos
ax.set_title(
    'Assigned, resolved and closed defects cumulated over time',
    fontsize=12,
    fontweight='bold',
    loc='left',
    pad=15,
)
ax.yaxis.tick_right()  # Eje Y a la derecha como en tu ejemplo
ax.grid(axis='x', linestyle='--', alpha=0.3)
plt.xticks(rotation=0)

# Leyenda inferior horizontal
ax.legend(
    loc='upper center',
    bbox_to_anchor=(0.5, -0.15),
    ncol=3,
    frameon=False,
    fontsize=10,
)

plt.tight_layout()
plt.savefig('defects_cumulative_chart.png', dpi=300)
plt.show()
