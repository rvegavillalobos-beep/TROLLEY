import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# 1. Definición de la línea de tiempo (ejemplo con semanas del año)
semanas = [f"CW{i}" for i in range(46, 53)] + [f"CW{i}" for i in range(1, 14)]

# Supongamos que partimos de una base inicial y modelamos la llegada de los lotes:
# Base: 30 trolleys desde el inicio.
# Batch 1: 24 trolleys (llega en CW46, disponible tras aduana).
# Batch 2: 30 trolleys (llega en CW2, disponible tras aduana en CW7).

n = len(semanas)
fisico = []
disponible = []

# Lógica de simulación para el DataFrame
base_trolleys = 30
batch1_llegada = 0 # CW46
batch1_liberacion = 3 # CW52 (ejemplo basado en tu imagen)
batch2_llegada = 8 # CW2
batch2_liberacion = 13 # CW7

# Tasa de ajuste de 2 unidades por semana por tu equipo
tasa_ajuste = 2
ajustados_acumulados = 0

datos = []
for i, sem in enumerate(semanas):
    # Simulación simple de inventario físico en planta
    # (Esto se puede ajustar según tus semanas exactas de calendario)
    if i < 7: # Del CW46 al CW52
        inventario_fisico = 30 + (24 if i >= 0 else 0) # Ejemplo esquemático
    else:
        inventario_fisico = 30 + 24 + 30

    # Capacidad limitada por el cuello de botella de ajuste mecánico
    if i > 0:
        ajustados_acumulados = min(inventario_fisico, ajustados_acumulados + tasa_ajuste)
    else:
        ajustados_acumulados = base_trolleys # Arranque con la base

    datos.append({
        "Semana": sem,
        "Fisico": inventario_fisico,
        "Operativo": ajustados_acumulados
    })

df = pd.DataFrame(datos)

# 2. Plotting con estilo Lean / Industrial Minimalista
fig, ax = plt.subplots(figsize=(14, 6))

x = np.arange(len(df["Semana"]))
width = 0.6

# Barras de inventario operativo (lo que realmente importa para la operación)
rects1 = ax.bar(x, df["Operativo"], width, label='Disponibles Operativos (Ajustados)', color='#2C3E50')
# Barras de respaldo o físico total con transparencia
rects2 = ax.bar(x, df["Fisico"] - df["Operativo"], width, bottom=df["Operativo"], 
                label='En espera de Ajuste / Tránsito', color='#BDC3C7', alpha=0.5)

ax.set_ylabel('Cantidad de Trolleys', fontsize=11, fontweight='bold', color='#333333')
ax.set_title('Ramp-up de Disponibilidad de Trolleys (Rate: 2 unds / semana)', fontsize=14, fontweight='bold', pad=20)
ax.set_xticks(x)
ax.set_xticklabels(df["Semana"], rotation=45, ha='right', fontsize=9)
ax.legend(frameon=False, loc='upper left')

# Limpieza visual estilo Lean (quitar bordes innecesarios)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#CCCCCC')
ax.spines['bottom'].set_color('#CCCCCC')
ax.grid(axis='y', linestyle='--', alpha=0.3)

plt.tight_layout()
plt.show()
