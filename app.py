import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

st.set_page_config(page_title="Trolley Availability & Line Capacity Ramp-Up", layout="wide")

st.title("📦 Trolley Availability vs. Production Demand (Up to CW8)")
st.markdown("Comparison between operational trolley availability (constrained by 2 units/week adjustment) and converted weekly production demand.")

# 1. Timeline Setup: Restricted up to CW8
weeks = [f"CW{i}" for i in range(46, 53)] + [f"CW{i}" for i in range(1, 9)]
n_weeks = len(weeks)

# 2. Simulation Logic for Trolleys
base = 35  # Base fleet availability
b1 = 24    # Batch 1
b2 = 30    # Batch 2 (arrives later, beyond CW8)

current_physical = base
current_operational = base
adjustment_rate = 2

phys_stock = []
op_stock = []
uph_capacity = []

for idx, w in enumerate(weeks):
    if idx == 7:  # Starting CW1
        current_physical += b1
        
    phys_stock.append(current_physical)
    
    # Continue adjusting by 2 units per week up to physical limits
    if current_operational < current_physical:
        current_operational = min(current_physical, current_operational + adjustment_rate)
    op_stock.append(current_operational)
    
    # Calculate UPH capacity based on ratio: 90 trolleys = 30 UPH
    calculated_uph = round((current_operational / 90.0) * 30, 1)
    uph_capacity.append(calculated_uph)

# 3. Weekly Production Data from Image (CW46 to CW8) and Conversion to Trolley Demand
# Raw weekly production total units
raw_production = [49, 69, 123, 147, 184, 196, 0, 0, 176, 199, 223, 246, 206, 280, 325]

# Conversion factor: Based on plant baseline (90 trolleys = 30 UPH, assuming operational hours factor)
# Adjust this factor if your specific weekly operating hours ratio differs.
production_to_trolley_factor = 0.25  # Converts weekly units to equivalent required trolleys
production_trolley_demand = [round(p * production_to_trolley_factor, 1) for p in raw_production]

df = pd.DataFrame({
    "Week": weeks,
    "Physical": phys_stock,
    "Operational": op_stock,
    "UPH": uph_capacity,
    "ProductionUnits": raw_production,
    "ProductionTrolleyDemand": production_trolley_demand
})

# 4. Professional Matplotlib Figure with Dual Axes
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 6.5), gridspec_kw={'height_ratios': [3, 0.7], 'hspace': 0.05}, sharex=True)

x = np.arange(n_weeks)
width = 0.65

# --- TOP CHART: PRIMARY AXIS (TROLLEYS BARS & PRODUCTION LINE) ---
ax1.bar(x, df["Operational"], width, label='Operational Available Trolleys', color='#1F4E79')
ax1.bar(x, df["Physical"] - df["Operational"], width, bottom=df["Operational"], 
        label='Pending Adjustment', color='#D9E1F2', alpha=0.8)

# Plot Converted Production Demand Line
prod_line_color = '#27AE60'  # Green line to clearly show demand vs capacity
ax1.plot(x, df["ProductionTrolleyDemand"], color=prod_line_color, marker='s', linewidth=2.2, markersize=5, 
         label='Production Demand (Converted to Trolleys)')

ax1.set_ylabel('Trolleys / Demand Equivalent', fontsize=11, fontweight='bold', color='#1F4E79')
ax1.set_title('Trolley Availability vs. Converted Weekly Production Demand (Up to CW8)', fontsize=13, fontweight='bold', pad=15, color='#1F4E79')
ax1.set_xticks(x)
ax1.set_xticklabels(weeks, rotation=45, ha='right', fontsize=9)

ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)
ax1.spines['left'].set_color('#BFBFBF')
ax1.spines['bottom'].set_color('#BFBFBF')
ax1.grid(axis='y', linestyle='--', alpha=0.4)

ax1.set_ylim(0, 96)
ax1.set_yticks(range(0, 91, 10))

# Annotate operational trolley numbers on top of bars
for i, v in enumerate(df["Operational"]):
    ax1.text(i, v + 0.8, str(v), ha='center', va='bottom', fontsize=7.5, fontweight='semibold', color='#333333')

# Annotate production demand values near markers
for i, val in enumerate(df["ProductionTrolleyDemand"]):
    if val > 0:
        ax1.text(i, val + 2.5, f"{raw_production[i]}u", ha='center', va='bottom', fontsize=6.5, fontweight='bold', color=prod_line_color)


# --- TOP CHART: SECONDARY AXIS (UPH CAPACITY LINE) ---
coral_color = '#D96852'

ax_uph = ax1.twinx()
ax_uph.plot(x, df["UPH"], color=coral_color, marker='o', linewidth=2.0, markersize=4, label='Line Capacity (UPH)', alpha=0.7)
ax_uph.set_ylabel('Line Capacity (UPH)', fontsize=11, fontweight='bold', color=coral_color)
ax_uph.tick_params(axis='y', labelcolor=coral_color)
ax_uph.set_ylim(0, 35)
ax_uph.spines['top'].set_visible(False)
ax_uph.spines['left'].set_visible(False)
ax_uph.spines['right'].set_color(coral_color)
ax_uph.grid(False)

# Combine legends cleanly on top left
lines_1, labels_1 = ax1.get_legend_handles_labels()
lines_2, labels_2 = ax_uph.get_legend_handles_labels()
ax1.legend(lines_1 + lines_2, labels_1 + labels_2, frameon=False, loc='upper left', fontsize=8.5)


# --- BOTTOM TRACKER: TIMELINE MILESTONES ---
# Row 1: Batch 1
ax2.barh(y=1, width=4, left=1, height=0.5, color='#FFF2CC', edgecolor='#D6B656', hatch='//')
ax2.text(3, 1, 'BATCH 1 Shipment +24', ha='center', va='center', fontsize=7.5, fontweight='bold', color='#7F6000')

ax2.barh(y=1, width=2, left=5, height=0.5, color='#FFE599', edgecolor='#D6B656')
ax2.text(6, 1, 'CUSTOMS', ha='center', va='center', fontsize=7, fontweight='bold', color='#7F6000')

# Styling bottom timeline tracker
ax2.set_yticks([])
ax2.set_xlim(-0.5, n_weeks - 0.5)
ax2.set_ylim(-0.5, 1.5)
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)
ax2.spines['left'].set_visible(False)
ax2.spines['bottom'].set_color('#BFBFBF')
ax2.grid(axis='x', linestyle=':', alpha=0.5)

plt.tight_layout()

# 4. Render in Streamlit
st.pyplot(fig)
plt.close(fig)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Base Fleet (CW46)", value="35 Units")
with col2:
    st.metric(label="Max Production Demand (CW8)", value="325 Units")
with col3:
    st.metric(label="Operational Capacity at CW8", value=f"{df['Operational'].iloc[-1]} Units")
