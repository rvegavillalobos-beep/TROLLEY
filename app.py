import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

st.set_page_config(page_title="Ramp-up de Trolleys", layout="wide")

st.title("📦 Ramp-up de Disponibilidad de Trolleys")
st.markdown("Visualización de inventario físico vs. capacidad operativa limitada por ajuste.")

# 1. Definición de la línea de tiempo (CW46 a CW13 del año siguiente)
semanas = [f"CW{i}" for i in range(46, 53)] + [f"CW{i}" for i in range(1, 14)]

# Lógica del modelo
base_trolleys = 30
tasa_ajuste = 2
ajustados_acumulados = 0

datos = []
for i, sem in enumerate(semanas):
    # Simulación de inventario físico acumulado según lotes y aduanas
    if i < 6: # Hasta CW51
        inventario_fisico = 30
    elif 6 <= i < 12: # Llega Batch 1 (24) en CW52
        inventario_fisico = 30 + 24
    else: # Llega Batch 2 (30) aprox en CW5
        inventario_fisico = 30 + 24 + 30

    # Capacidad limitada por el cuello de botella de ajuste (2 por semana)
    if i == 0:
        ajustados_acumulados = base_trolleys
    else:
        ajustados_acumulados = min(inventario_fisico, ajustados_acumulados + tasa_ajuste)

    datos.append({
        "Semana": sem,
        "Fisico": inventario_fisico,
        "Operativo": ajustados_acumulados
    })

df = pd.DataFrame(datos)

# 2. Generación de la gráfica con Matplotlib
fig, ax = plt.subplots(figsize=(12, 5))

x = np.arange(len(df["Semana"]))
width = 0.6

# Barras de inventario operativo (lo que está listo para usar)
ax.bar(x, df["Operativo"], width, label='Disponibles Operativos (Ajustados)', color='#2C3E50')
# Barras de respaldo o físico total en espera de ajuste
ax.bar(x, df["Fisico"] - df["Operativo"], width, bottom=df["Operativo"], 
       label='En espera de Ajuste / Tránsito', color='#BDC3C7', alpha=0.6)

ax.set_ylabel('Cantidad de Trolleys', fontsize=11, fontweight='bold', color='#333333')
ax.set_title('Ramp-up de Disponibilidad de Trolleys (Rate: 2 un/sem)', fontsize=13, fontweight='bold', pad=15)
ax.set_xticks(x)
ax.set_xticklabels(df["Semana"], rotation=45, ha='right', fontsize=9)
ax.legend(frameon=False, loc='upper left')

# Limpieza visual estilo Lean
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#CCCCCC')
ax.spines['bottom'].set_color('#CCCCCC')
ax.grid(axis='y', linestyle='--', alpha=0.3)

plt.tight_layout()

# 3. Mostrar la gráfica en Streamlit de forma segura
st.pyplot(fig)
plt.close(fig) # Cierra la figura para evitar fugas de memoria y errores de renderizado
