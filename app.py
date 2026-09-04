import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

st.set_page_config(page_title="Trolley Availability Ramp-Up", layout="wide")

st.title("📦 Trolley Availability Ramp-Up & Capacity Plan")
st.markdown("Operational readiness tracking constrained by a mechanical adjustment rate of **2 units/week**.")

# 1. Timeline Setup (CW46 to CW13 of next year)
weeks = [f"CW{i}" for i in range(46, 53)] + [f"CW{i}" for i in range(1, 14)]
n_weeks = len(weeks)

# 2. Simulation Logic aligned precisely with constraints:
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

for idx, w in enumerate(weeks):
    if idx == 7:  # Starting CW1
        current_physical += b1
    if idx == 14: # Starting CW8
        current_physical += b2
        
    phys_stock.append(current_physical)
    
    if current_operational < current_physical:
        current_operational = min(current_physical, current_operational + adjustment_rate)
    op_stock.append(current_operational)

df = pd.DataFrame({
    "Week": weeks,
    "Physical": phys_stock,
    "Operational": op_stock
})

# 3. Professional Matplotlib Figure with Tight Subplot Spacing
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 5.8), gridspec_kw={'height_ratios': [3, 0.7], 'hspace': 0.05}, sharex=True)

x = np.arange(n_weeks)
width = 0.65

# --- TOP CHART: BAR CHART FOR INVENTORY ---
ax1.bar(x, df["Operational"], width, label='Operational Available (Adjusted)', color='#1F4E79')
ax1.bar(x, df["Physical"] - df["Operational"], width, bottom=df["Operational"], 
        label='Pending Adjustment', color='#D9E1F2', alpha=0.8)

ax1.set_ylabel('Available Trolley', fontsize=11, fontweight='bold', color='#262626')
ax1.set_title('Trolley Availability Ramp-Up & Bottleneck Control (Rate: 2 units/week)', fontsize=13, fontweight='bold', pad=15, color='#1F4E79')
ax1.set_xticks(x)
ax1.set_xticklabels(weeks, rotation=45, ha='right', fontsize=9)
ax1.legend(frameon=False, loc='upper left', fontsize=10)

ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)
ax1.spines['left'].set_color('#BFBFBF')
ax1.spines['bottom'].set_color('#BFBFBF')
ax1.grid(axis='y', linestyle='--', alpha=0.4)

for i, v in enumerate(df["Operational"]):
    ax1.text(i, v + 0.8, str(v), ha='center', va='bottom', fontsize=8, fontweight='semibold', color='#333333')


# --- BOTTOM TRACKER: TIMELINE MILESTONES (CLEANED UP) ---
# Row 1: Batch 1 (Shipment width 4 at left 1, Customs width 2 at left 5)
ax2.barh(y=1, width=4, left=1, height=0.5, color='#FFF2CC', edgecolor='#D6B656', hatch='//')
ax2.text(3, 1, 'SHIPMENT (24 u)', ha='center', va='center', fontsize=7.5, fontweight='bold', color='#7F6000')

ax2.barh(y=1, width=2, left=5, height=0.5, color='#FFE599', edgecolor='#D6B656')
ax2.text(6, 1, 'CUSTOMS', ha='center', va='center', fontsize=7, fontweight='bold', color='#7F6000')

# Row 2: Batch 2 (Shipment width 4 at left 8, Customs width 2 at left 12)
ax2.barh(y=0, width=4, left=8, height=0.5, color='#FFF2CC', edgecolor='#D6B656', hatch='//')
ax2.text(10, 0, 'SHIPMENT (30 u)', ha='center', va='center', fontsize=7.5, fontweight='bold', color='#7F6000')

ax2.barh(y=0, width=2, left=12, height=0.5, color='#FFE599', edgecolor='#D6B656')
ax2.text(13, 0, 'CUSTOMS', ha='center', va='center', fontsize=7, fontweight='bold', color='#7F6000')

# Styling bottom timeline tracker (removed redundant left labels)
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

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Base Fleet", value="30 Units")
with col2:
    st.metric(label="Total Inflow Planned", value="54 Units (2 Batches)")
with col3:
    st.metric(label="Adjustment Bottleneck", value="2 Units / Week")
