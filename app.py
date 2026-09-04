import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

st.set_page_config(page_title="Trolley Availability & Line Capacity Ramp-Up", layout="wide")

st.title("📦 Trolley Availability & Production Capacity Ramp-Up")
st.markdown("Operational readiness and line UPH capability constrained by a mechanical adjustment rate of **2 units/week** (Target: 90 trolleys for 30 UPH).")

# 1. Timeline Setup: Extended to CW15 of next year (reaching 20 UPH)
weeks = [f"CW{i}" for i in range(46, 53)] + [f"CW{i}" for i in range(1, 16)]
n_weeks = len(weeks)

# 2. Simulation Logic
physical = []
operational = []
base = 30
b1 = 24
b2 = 30

current_physical = base
current_operational = base
adjustment_rate = 2

phys_stock = []
op_stock = []
uph_capacity = []

for idx, w in enumerate(weeks):
    if idx == 7:  # Starting CW1
        current_physical += b1
    if idx == 14: # Starting CW8
        current_physical += b2
        
    phys_stock.append(current_physical)
    
    # Continue adjusting by 2 units per week up to operational limits
    if current_operational < current_physical:
        current_operational = min(current_physical, current_operational + adjustment_rate)
    op_stock.append(current_operational)
    
    # Calculate UPH capacity based on ratio: 90 trolleys = 30 UPH (Trolleys / 3)
    calculated_uph = round((current_operational / 90.0) * 30, 1)
    uph_capacity.append(calculated_uph)

df = pd.DataFrame({
    "Week": weeks,
    "Physical": phys_stock,
    "Operational": op_stock,
    "UPH": uph_capacity
})

# 3. Professional Matplotlib Figure with Dual Axes (Bars for Trolleys, Line for UPH)
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 6.5), gridspec_kw={'height_ratios': [3, 0.7], 'hspace': 0.05}, sharex=True)

x = np.arange(n_weeks)
width = 0.65

# --- TOP CHART: PRIMARY AXIS (TROLLEYS BARS) ---
ax1.bar(x, df["Operational"], width, label='Operational Available (Adjusted)', color='#1F4E79')
ax1.bar(x, df["Physical"] - df["Operational"], width, bottom=df["Operational"], 
        label='Pending Adjustment', color='#D9E1F2', alpha=0.8)

ax1.set_ylabel('Available Trolley', fontsize=11, fontweight='bold', color='#1F4E79')
ax1.set_title('Trolley Availability & Line Capacity Ramp-Up (Rate: 2 units/week)', fontsize=13, fontweight='bold', pad=15, color='#1F4E79')
ax1.set_xticks(x)
ax1.set_xticklabels(weeks, rotation=45, ha='right', fontsize=9)

ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)
ax1.spines['left'].set_color('#BFBFBF')
ax1.spines['bottom'].set_color('#BFBFBF')
ax1.grid(axis='y', linestyle='--', alpha=0.4)
ax1.set_ylim(0, max(df["Physical"]) + 10)

# Annotate trolley numbers on top of bars
for i, v in enumerate(df["Operational"]):
    ax1.text(i, v + 0.8, str(v), ha='center', va='bottom', fontsize=7.5, fontweight='semibold', color='#333333')


# --- TOP CHART: SECONDARY AXIS (UPH CAPACITY LINE) ---
# Using the requested Coral color #FF9E8A (with a slightly deeper shade for sharp text/line legibility: #D96852)
coral_color = '#D96852'

ax_uph = ax1.twinx()
ax_uph.plot(x, df["UPH"], color=coral_color, marker='o', linewidth=2.2, markersize=4.5, label='Line Capacity (UPH)')
ax_uph.set_ylabel('Line Capacity (UPH)', fontsize=11, fontweight='bold', color=coral_color)
ax_uph.tick_params(axis='y', labelcolor=coral_color)
ax_uph.set_ylim(0, 35)
ax_uph.spines['top'].set_visible(False)
ax_uph.spines['left'].set_visible(False)
ax_uph.spines['right'].set_color(coral_color)
ax_uph.grid(False)

# Annotate UPH values tightly below each point on the line
for i, uph in enumerate(df["UPH"]):
    ax_uph.text(i, uph - 0.8, f"{uph}", ha='center', va='top', fontsize=6.5, fontweight='bold', color=coral_color)

# Combine legends from both axes cleanly on top left
lines_1, labels_1 = ax1.get_legend_handles_labels()
lines_2, labels_2 = ax_uph.get_legend_handles_labels()
ax1.legend(lines_1 + lines_2, labels_1 + labels_2, frameon=False, loc='upper left', fontsize=9)


# --- BOTTOM TRACKER: TIMELINE MILESTONES ---
# Row 1: Batch 1
ax2.barh(y=1, width=4, left=1, height=0.5, color='#FFF2CC', edgecolor='#D6B656', hatch='//')
ax2.text(3, 1, 'BATCH 1 Shipment +24', ha='center', va='center', fontsize=7.5, fontweight='bold', color='#7F6000')

ax2.barh(y=1, width=2, left=5, height=0.5, color='#FFE599', edgecolor='#D6B656')
ax2.text(6, 1, 'CUSTOMS', ha='center', va='center', fontsize=7, fontweight='bold', color='#7F6000')

# Row 2: Batch 2
ax2.barh(y=0, width=4, left=8, height=0.5, color='#FFF2CC', edgecolor='#D6B656', hatch='//')
ax2.text(10, 0, 'BATCH 2 Shipment +30', ha='center', va='center', fontsize=7.5, fontweight='bold', color='#7F6000')

ax2.barh(y=0, width=2, left=12, height=0.5, color='#FFE599', edgecolor='#D6B656')
ax2.text(13, 0, 'CUSTOMS', ha='center', va='center', fontsize=7, fontweight='bold', color='#7F6000')

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

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(label="Base Fleet", value="30 Units (10.0 UPH)")
with col2:
    st.metric(label="Total Inflow Planned", value="54 Units (2 Batches)")
with col3:
    st.metric(label="Adjustment Bottleneck", value="2 Units / Week")
with col4:
    st.metric(label="Target Line Capacity", value="90 Units (30.0 UPH)")
