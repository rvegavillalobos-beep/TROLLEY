import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 1. GENERACIÓN DE DATOS SIMULADOS (Con cálculo explícito de Ángulo)
np.random.seed(42)
n_samples = 120

dates = pd.date_range(start="2026-06-01", end="2026-08-20", periods=n_samples)
calendar_weeks = ["CW" + str(d.isocalendar().week).zfill(2) for d in dates]

trend_factor = np.linspace(0, 1, n_samples)
centroid_x = -3.5 + np.random.normal(0, 1.2, n_samples) - (trend_factor * 1.5)
centroid_y = -0.5 + (trend_factor * 2.5) + np.random.normal(0, 0.8, n_samples)
magnitude_r = np.sqrt(centroid_x**2 + centroid_y**2)

# Cálculo real del ángulo en grados [-180, 180] y su conversión a radianes para el diagrama polar
angle_deg = np.arctan2(centroid_y, centroid_x) * (180 / np.pi)

status = np.where(magnitude_r > 3.0, "FAIL", "PASS")

df_report = pd.DataFrame({
    "Date": dates,
    "CalendarWeek": calendar_weeks,
    "Centroid_X": centroid_x,
    "Centroid_Y": centroid_y,
    "Magnitude": magnitude_r,
    "Angle": angle_deg,
    "Status": status,
})

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

# 2. CONFIGURACIÓN DE LA FIGURA (4 Filas x 3 Columnas)
fig = plt.figure(figsize=(14, 11), facecolor="white")
gs = gridspec.GridSpec(4, 3, figure=fig, hspace=0.45, wspace=0.3)

primary_color = "#0f766e"
accent_color = "#e11d48"
neutral_dark = "#111827"
time_index = np.arange(len(df_report))

# --- TÍTULO Y ENCABEZADO (Fila 0) ---
ax_title = fig.add_subplot(gs[0, :])
ax_title.set_facecolor("white")
ax_title.axis("off")
ax_title.text(
    0.0,
    0.7,
    "AUTOMATED CONVEYOR SYSTEM: LONGITUDINAL & LATERAL DRIFT REPORT",
    fontsize=15,
    weight="bold",
    color=neutral_dark,
)
ax_title.text(
    0.0,
    0.2,
    "Analysis Window: June 2026 – August 2026 (CW23 to CW34) | Plant Operations & Quality Control",
    fontsize=10,
    color="#4b5563",
)
ax_title.axhline(0, color="#d1d5db", linewidth=1.5)

# --- GRÁFICA 1: TENDENCIA TEMPORAL (Fila 1, Cols 0-1) ---
ax1 = fig.add_subplot(gs[1, :2])
ax1.set_facecolor("white")
ax1.plot(
    df_report["Date"],
    df_report["Centroid_X"],
    color="#0284c7",
    alpha=0.8,
    label="Centroid X (Longitudinal)",
    linewidth=1.5,
)
ax1.plot(
    df_report["Date"],
    df_report["Centroid_Y"],
    color="#d97706",
    alpha=0.8,
    label="Centroid Y (Lateral)",
    linewidth=1.5,
)
ax1.axhline(0, color="#9ca3af", linestyle="--", alpha=0.8)
ax1.set_title(
    "Temporal Drift Evolution (Daily Scatter)",
    fontsize=11,
    weight="bold",
    color=neutral_dark,
)
ax1.set_ylabel("Deviation [mm]", fontsize=9, color=neutral_dark)
ax1.legend(
    loc="upper left",
    frameon=True,
    facecolor="white",
    edgecolor="#d1d5db",
    fontsize=8,
)
ax1.tick_params(axis="both", labelsize=8, colors=neutral_dark)
ax1.grid(True, linestyle=":", alpha=0.5, color="#e5e7eb")

# --- GRÁFICA 2: MAGNITUD SEMANAL (Fila 1, Col 2) ---
ax2 = fig.add_subplot(gs[1, 2])
ax2.set_facecolor("white")
ax2.bar(
    df_weekly["CalendarWeek"],
    df_weekly["Mean_Mag"],
    color=primary_color,
    alpha=0.9,
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
ax2.set_ylabel("Mean Magnitude [mm]", fontsize=9, color=neutral_dark)
ax2.tick_params(axis="x", rotation=45, labelsize=7, colors=neutral_dark)
ax2.tick_params(axis="y", labelsize=8, colors=neutral_dark)
ax2.legend(loc="upper right", fontsize=7)
ax2.grid(True, linestyle=":", alpha=0.5, color="#e5e7eb")

# --- GRÁFICA 3: MAPA DE DISPERSIÓN ESPACIAL (Fila 2, Cols 0-1) ---
ax3 = fig.add_subplot(gs[2, :2])
ax3.set_facecolor("white")
scatter = ax3.scatter(
    df_report["Centroid_X"],
    df_report["Centroid_Y"],
    c=time_index,
    cmap="viridis",
    s=40,
    alpha=0.85,
    edgecolors="#374151",
    linewidth=0.6,
)
ax3.axhline(0, color="#9ca3af", linestyle="--", alpha=0.8)
ax3.axvline(0, color="#9ca3af", linestyle="--", alpha=0.8)
ax3.set_title(
    "Spatial Phase Shift (Color = Time Progression: June ➔ August)",
    fontsize=11,
    weight="bold",
    color=neutral_dark,
)
ax3.set_xlabel(
    "Mean X Deviation [mm] (-X Front / +X Back)", fontsize=9, color=neutral_dark
)
ax3.set_ylabel(
    "Mean Y Deviation [mm] (-Y Left / +Y Right)", fontsize=9, color=neutral_dark
)
ax3.tick_params(axis="both", labelsize=8, colors=neutral_dark)
ax3.grid(True, linestyle=":", alpha=0.5, color="#e5e7eb")

# --- GRÁFICA 4: DIAGRAMA POLAR / ROSA DE VIENTOS (Fila 2, Col 2) ---
ax_polar = fig.add_subplot(gs[2, 2], projection="polar")
ax_polar.set_facecolor("white")
# Convertir ángulo a radianes para Matplotlib polar
theta_rad = np.radians(df_report["Angle"])
polar_scatter = ax_polar.scatter(
    theta_rad,
    df_report["Magnitude"],
    c=time_index,
    cmap="viridis",
    s=35,
    alpha=0.85,
    edgecolors="#374151",
    linewidth=0.5,
)
ax_polar.set_title(
    "Polar Drift / Wind Rose (Angle vs R)",
    fontsize=11,
    weight="bold",
    color=neutral_dark,
    pad=15,
)
ax_polar.tick_params(axis="both", labelsize=7, colors=neutral_dark)
ax_polar.grid(True, linestyle=":", alpha=0.5, color="#e5e7eb")

# Barra de color compartida para las gráficas espaciales
cbar_ax = fig.add_axes([0.13, 0.48, 0.54, 0.02])
cbar = fig.colorbar(scatter, cax=cbar_ax, orientation="horizontal")
cbar.set_label(
    "Timeline Progression (June [Dark] to August [Bright])", fontsize=8
)
cbar.ax.tick_params(labelsize=7)

# --- CAJA DE TEXTO: RESUMEN EJECUTIVO (Fila 3, todo el ancho) ---
ax_text = fig.add_subplot(gs[3, :])
ax_text.set_facecolor("white")
ax_text.axis("off")

summary_text = (
    "EXECUTIVE ENGINEERING INSIGHTS & DRIFT ANALYSIS:\n\n"
    "• Longitudinal Chronical Bias (X): Centroid X maintains a persistent negative offset (-3mm to -8mm) across the entire window, indicating an unresolved pneumatic stop or dwell timing issue.\n"
    "• Lateral Phase Shift (Y & Angle): June data shows clustering in Q3 (-Y / -140°), whereas August data aggressively migrates to Q2 (+Y / +130°). This confirms a physical shift in side-guide alignment or thermal fixture expansion.\n"
    "• Action Plan: 1. Recalibrate longitudinal pneumatic stoppers. 2. Inspect roller guide clearances for thermal drift during peak ambient temperatures."
)

ax_text.text(
    0.0,
    0.9,
    summary_text,
    fontsize=9,
    verticalalignment="top",
    horizontalalignment="left",
    family="monospace",
    color=neutral_dark,
    bbox=dict(
        boxstyle="round,pad=0.8",
        facecolor="#f9fafb",
        edgecolor="#d1d5db",
        linewidth=1,
    ),
)

# Guardar con fondo blanco garantizado
plt.savefig(
    "Quality_Drift_OnePager_Polar.png",
    dpi=300,
    bbox_inches="tight",
    facecolor="white",
    edgecolor="none",
)
plt.show()
print("Reporte generado con éxito: 'Quality_Drift_OnePager_Polar.png'")
