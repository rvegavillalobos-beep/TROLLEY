import io
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ---------------------------------------------------------
# 1. GENERACIÓN / CARGA DE DATOS (Simulación basada en el reporte real)
# ---------------------------------------------------------
np.random.seed(42)
n_samples = 120

# Fechas de junio a agosto de 2026 (CW23 a CW34)
dates = pd.date_range(start="2026-06-01", end="2026-08-20", periods=n_samples)
calendar_weeks = [
    "CW" + str(d.isocalendar().week).zfill(2) for d in dates
]

# Simulación de tendencias basadas en el análisis real:
# - Centroid X: Sesgo negativo constante (-2 a -8 mm)
# - Centroid Y: Transición de negativo/neutro a positivo fuerte en agosto (+1 a +3 mm)
trend_factor = np.linspace(0, 1, n_samples)
centroid_x = -3.5 + np.random.normal(0, 1.2, n_samples) - (trend_factor * 1.5)
centroid_y = -0.5 + (trend_factor * 2.5) + np.random.normal(0, 0.8, n_samples)

magnitude_r = np.sqrt(centroid_x**2 + centroid_y**2)
status = np.where(magnitude_r > 3.0, "FAIL", "PASS")

df_report = pd.DataFrame({
    "Date": dates,
    "CalendarWeek": calendar_weeks,
    "Centroid_X": centroid_x,
    "Centroid_Y": centroid_y,
    "Magnitude": magnitude_r,
    "Status": status,
})

# Agrupado semanal para tendencias
df_weekly = (
    df_report.groupby("CalendarWeek")
    .agg(
        Mean_X=("Centroid_X", "mean"),
        Mean_Y=("Centroid_Y", "mean"),
        Mean_Mag=("Magnitude", "mean"),
        Fail_Rate=(
            "Status",
            lambda x: (sum(x == "FAIL") / len(x)) * 100,
        ),
    )
    .reset_index()
)

# ---------------------------------------------------------
# 2. DISEÑO DEL ONE-PAGER (Matplotlib GridSpec)
# ---------------------------------------------------------
fig = plt.figure(figsize=(14, 9), constrained_layout=True)
fig.patch.set_facecolor("#f8fafc")  # Fondo gris muy suave profesional
gs = gridspec.GridSpec(3, 3, figure=fig)

# Estilo global
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
primary_color = "#0f766e"  # Teal industrial
accent_color = "#e11d48"   # Rojo alerta
neutral_dark = "#1e293b"

# --- TÍTULO Y ENCABEZADO ---
ax_title = fig.add_subplot(gs[0, :])
ax_title.axis("off")
ax_title.text(
    0.0,
    0.7,
    "AUTOMATED CONVEYOR SYSTEM: LONGITUDINAL & LATERAL DRIFT REPORT",
    fontsize=16,
    weight="bold",
    color=neutral_dark,
)
ax_title.text(
    0.0,
    0.3,
    "Analysis Window: June 2026 – August 2026 (CW23 to CW34) | Plant Operations & Quality Control",
    fontsize=10,
    color="#64748b",
)
ax_title.axhline(0, color="#cbd5e1", linewidth=1.5)

# --- GRÁFICA 1: TENDENCIA TEMPORAL DE CENTROIDES (X e Y) ---
ax1 = fig.add_subplot(gs[1, :2])
ax1.plot(
    df_report["Date"],
    df_report["Centroid_X"],
    color="#0284c7",
    alpha=0.6,
    label="Centroid X (Longitudinal)",
)
ax1.plot(
    df_report["Date"],
    df_report["Centroid_Y"],
    color="#d97706",
    alpha=0.6,
    label="Centroid Y (Lateral)",
)
ax1.axhline(0, color="gray", linestyle="--", alpha=0.7)
ax1.set_title(
    "Temporal Drift Evolution (Daily Scatter)",
    fontsize=11,
    weight="bold",
    color=neutral_dark,
)
ax1.set_ylabel("Deviation [mm]", fontsize=9)
ax1.legend(loc="upper left", frameon=True, facecolor="white", fontsize=8)
ax1.tick_params(axis="both", labelsize=8)

# --- GRÁFICA 2: MAGNITUD DE ERROR PROMEDIO SEMANAL ---
ax2 = fig.add_subplot(gs[1, 2])
ax2.bar(
    df_weekly["CalendarWeek"],
    df_weekly["Mean_Mag"],
    color=primary_color,
    alpha=0.85,
)
ax2.axhline(
    3.0,
    color=accent_color,
    linestyle=":",
    linewidth=2,
    label="Tolerance Limit (3mm)",
)
ax2.set_title(
    "Weekly Mean Error Magnitude (R)",
    fontsize=11,
    weight="bold",
    color=neutral_dark,
)
ax2.set_ylabel("Mean Magnitude [mm]", fontsize=9)
ax2.tick_params(axis="x", rotation=45, labelsize=7)
ax2.tick_params(axis="y", labelsize=8)
ax2.legend(loc="upper right", fontsize=7)

# --- GRÁFICA 3: MAPA DE DISPERSIÓN ESPACIAL (X vs Y) Y CAMBIO DE FASE ---
ax3 = fig.add_subplot(gs[2, :2])
scatter = ax3.scatter(
    df_report["Centroid_X"],
    df_report["Centroid_Y"],
    c=pd.to_datetime(df_report["Date"]).astype(int),
    cmap="viridis",
    s=35,
    alpha=0.8,
    edgecolors="w",
    linewidth=0.5,
)
ax3.axhline(0, color="gray", linestyle="--", alpha=0.5)
ax3.axvline(0, color="gray", linestyle="--", alpha=0.5)
ax3.set_title(
    "Spatial Phase Shift (Color = Time Progression: June ➔ August)",
    fontsize=11,
    weight="bold",
    color=neutral_dark,
)
ax3.set_xlabel("Mean X Deviation [mm] (-X Front / +X Back)", fontsize=9)
ax3.set_ylabel("Mean Y Deviation [mm] (-Y Left / +Y Right)", fontsize=9)
cbar = plt.colorbar(scatter, ax=ax3, orientation="horizontal", pad=0.18, aspect=40)
cbar.set_label("Timeline Progression (June to August)", fontsize=8)
cbar.ax.tick_params(labelsize=7)
ax3.tick_params(axis="both", labelsize=8)

# --- CAJA DE TEXTO: RESUMEN EJECUTIVO Y TENDENCIAS ---
ax_text = fig.add_subplot(gs[2, 2])
ax_text.axis("off")

summary_text = (
    "EXECUTIVE ENGINEERING INSIGHTS:\n\n"
    "• Systematic Longitudinal Bias:\n"
    "  Centroid X consistently holds a negative offset\n"
    "  (-3mm to -8mm), indicating a repetitive\n"
    "  mechanical stop or pneumatic dwell timing error.\n\n"
    "• August Lateral Phase Shift:\n"
    "  Centroid Y shifts aggressively toward positive\n"
    "  values (+1mm to +3mm) starting in CW31–CW34.\n"
    "  This points to thermal expansion of fixtures or\n"
    "  wear on side-guide rollers during peak heat.\n\n"
    "• Action Plan:\n"
    "  1. Recalibrate pneumatic stoppers on line 2.\n"
    "  2. Inspect roller guide clearances for thermal drift."
)

ax_text.text(
    0.0,
    1.0,
    summary_text,
    fontsize=9,
    verticalalignment="top",
    horizontalalignment="left",
    family="monospace",
    bbox=dict(
        boxstyle="round,pad=0.6",
        facecolor="#ffffff",
        edgecolor="#cbd5e1",
        linewidth=1,
    ),
)

# Guardar imagen de alta calidad
plt.savefig(
    "Quality_Drift_OnePager.png",
    dpi=300,
    bbox_inches="tight",
    facecolor=fig.get_facecolor(),
)
plt.show()
print("¡Reporte One-Pager generado y guardado exitosamente como 'Quality_Drift_OnePager.png'!")
