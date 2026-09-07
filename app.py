import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO

st.set_page_config(page_title="Defects Cumulative Chart Automation", layout="wide")

st.title("📊 Generador de Gráfico Acumulado de Defects")
st.markdown("Sube tu archivo de Excel de seguimiento de issues/defectos para automatizar el gráfico de áreas acumuladas.")

# Sidebar para subida de archivos y configuración
st.sidebar.header("1. Carga de Archivo")
uploaded_file = st.sidebar.file_uploader("Sube tu archivo Excel (.xlsx)", type=["xlsx", "xls"])

# Validar si el archivo fue subido antes de intentar leerlo
if uploaded_file is not None:
    try:
        # Leer directamente desde el objeto subido
        df = pd.read_excel(uploaded_file)
        st.sidebar.success("¡Archivo cargado con éxito!")
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        st.stop()
else:
    st.info("👈 Por favor, sube tu archivo Excel en la barra lateral para empezar.")
    st.stop()  # Detiene la ejecución para evitar errores de variables vacías

# --- El resto de tu código sigue aquí a partir de 'df' ---
