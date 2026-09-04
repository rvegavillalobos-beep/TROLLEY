import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

st.set_page_config(page_title="Trolley Availability & Line Capacity Ramp-Up", layout="wide")

st.title("📦 Trolley Availability & Production Capacity Ramp-Up")
st.markdown("Operational readiness and line UPH capability constrained by a mechanical adjustment rate of **2 units/week** (Target: 90 trolleys for 30 UPH).")

# 1. Timeline Setup (CW46 to CW13 of next year)
weeks = [f"CW{i}" for i in range(46, 53)] + [f"CW{i}" for i in range(1, 14)]
n_weeks = len(weeks)

# 2. Simulation Logic
# Base inventory: 30 trolleys
# Batch 1: 24 units -> Shipment CW47-CW50 (4 weeks), Customs Clearance CW51-CW52 (2 weeks), Physical stock updates at CW1 (index 7)
# Batch 2: 30 units -> Shipment CW2-CW5 (4 weeks), Customs Clearance CW6-CW7 (2 weeks), Physical stock updates at CW8 (index 14)
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
    
    if current_operational < current_physical:
        current_operational = min(current_physical, current_operational + adjustment_rate)
    op_stock.append(current_operational)
    
    # Calculate UPH capacity based on ratio: 90 trolleys = 30 UPH (i.e., Trolleys / 3)
    calculated_uph = round((current_operational / 90.0) * 30, 1)
    uph_capacity.append(calculated_uph)

df = pd.DataFrame({
    "Week": weeks,
    "Physical": phys_stock,
    "Operational": op_stock,
    "UPH": uph_capacity
})

# 3. Professional Matplotlib Figure with Twin Axes for Capacity (UPH)
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 6.2), gridspec_kw={'height_ratios': [3, 0.7], 'hspace': 0.05}, sharex=True)

x = np.arange(n_weeks)
width = 0.65

# --- TOP CHART: BAR CHART FOR INVENTORY & LINE CAPACITY ---
ax1.bar(x, df["Operational"], width, label='Operational Available (Adjusted)', color='#1F4E79')
ax1.bar(x, df["Physical"] - df["Operational"], width, bottom=df["Operational"], 
        label='Pending Adjustment', color='#D9E1F2', alpha=0.8)

ax1.set_ylabel('Available Trolley', fontsize=11, fontweight='bold', color='#262626')
ax1.set_title('Trolley Availability & Line Capacity Ramp-Up (Rate: 2 units/week)', fontsize=13, fontweight='bold', pad=15, color='#1F4E79')
ax1.set_xticks(x)
ax1.set_xticklabels(weeks, rotation=45, ha='right', fontsize=9)
ax1.legend(frameon=False, loc='upper left', fontsize=10)

ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)
ax1.spines['left'].set_color('#BFBFBF')
ax1.spines['bottom'].set_color('#BFBFBF')
ax1.grid(axis='y', linestyle='--', alpha=0.4)

# Annotate specific operational values and UPH capacity equivalent on top of bars
for i, (v, uph) in enumerate(zip(df["Operational"], df["UPH"])):
    ax1.text(i, v + 0.8, f"{v}\n({uph} UPH)", ha='center', va='bottom', fontsize=7.5, fontweight='semibold', color='#333333')

ax1.set_ylim(0, max(df["Physical"]) + 8)


# --- BOTTOM TRACKER: TIMELINE MILESTONES (UPDATED LABELS) ---
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
    st.metric(label="Base Fleet", value="30 Units (10 UPH)")
with col2:
    st.metric(label="Total Inflow Planned", value="54 Units (2 Batches)")
with col3:
    st.metric(label="Adjustment Bottleneck", value="2 Units / Week")
with col4:
    st.metric(label="Target Line Capacity", value="90 Units (30 UPH)")
