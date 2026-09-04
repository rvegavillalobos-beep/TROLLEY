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

# 2. Simulation Logic
# Base inventory: 30 trolleys
# Batch 1: 24 units (Shipped CW46-49, Customs CW50-52)
# Batch 2: 30 units (Shipped CW2-CW6, Customs CW7-8)
physical = []
operational = []
base = 30
b1 = 24
b2 = 30

# Inventory milestone thresholds simulation
current_physical = base
current_operational = base
adjustment_rate = 2

op_stock = []
phys_stock = []

for idx, w in enumerate(weeks):
    # Physical stock arrivals simulation based on diagram logic
    if idx == 6: # CW52 (Batch 1 fully cleared)
        current_physical += b1
    if idx == 13: # CW7 (Batch 2 fully cleared)
        current_physical += b2
        
    phys_stock.append(current_physical)
    
    # Operational stock governed by the adjustment bottleneck (2 units / week)
    if current_operational < current_physical:
        current_operational = min(current_physical, current_operational + adjustment_rate)
    op_stock.append(current_operational)

df = pd.DataFrame({
    "Week": weeks,
    "Physical": phys_stock,
    "Operational": op_stock
})

# 3. Professional Matplotlib Figure with Dual Grid / Milestone Matrix
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 7), gridspec_kw={'height_ratios': [3, 1]}, sharex=True)

x = np.arange(n_weeks)
width = 0.65

# --- TOP CHART: BAR CHART FOR INVENTORY ---
bars_op = ax1.bar(x, df["Operational"], width, label='Operational Available (Adjusted)', color='#1F4E79')
bars_wait = ax1.bar(x, df["Physical"] - df["Operational"], width, bottom=df["Operational"], 
                    label='Pending Adjustment / In Transit', color='#D9E1F2', alpha=0.8)

ax1.set_ylabel('Trolley Count', fontsize=11, fontweight='bold', color='#262626')
ax1.set_title('Trolley Availability Ramp-Up & Bottleneck Control (Rate: 2 units/week)', fontsize=13, fontweight='bold', pad=15, color='#1F4E79')
ax1.set_xticks(x)
ax1.set_xticklabels(weeks, rotation=45, ha='right', fontsize=9)
ax1.legend(frameon=False, loc='upper left', fontsize=10)

# Clean minimalist style for top chart
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)
ax1.spines['left'].set_color('#BFBFBF')
ax1.spines['bottom'].set_color('#BFBFBF')
ax1.grid(axis='y', linestyle='--', alpha=0.4)

# Annotate specific operational values on top of bars
for i, v in enumerate(df["Operational"]):
    ax1.text(i, v + 0.8, str(v), ha='center', va='bottom', fontsize=8, fontweight='semibold', color='#333333')


# --- BOTTOM TRACKER: TIMELINE MILESTONES (GANTT STYLE ROWS) ---
# Row 1: Batch 1
ax2.barh(y=1, width=4, left=0, height=0.6, color='#FFF2CC', edgecolor='#D6B656', hatch='//') # Shipment CW46-49
ax2.text(2, 1, 'BATCH 1 SHIPMENT (24 units)', ha='center', va='center', fontsize=8, fontweight='bold', color='#7F6000')

ax2.barh(y=1, width=3, left=4, height=0.6, color='#FFE599', edgecolor='#D6B656') # Customs CW50-52
ax2.text(5.5, 1, 'CUSTOMS CLEARANCE', ha='center', va='center', fontsize=8, fontweight='bold', color='#7F6000')

# Row 2: Batch 2
# CW2 corresponds to index 7 in our array (CW46 is index 0)
ax2.barh(y=0, width=5, left=7, height=0.6, color='#FFF2CC', edgecolor='#D6B656', hatch='//') # Shipment CW2-6
ax2.text(9.5, 0, 'BATCH 2 SHIPMENT (30 units)', ha='center', va='center', fontsize=8, fontweight='bold', color='#7F6000')

ax2.barh(y=0, width=2, left=12, height=0.6, color='#FFE599', edgecolor='#D6B656') # Customs CW7-8
ax2.text(13, 0, 'CUSTOMS', ha='center', va='center', fontsize=8, fontweight='bold', color='#7F6000')

# Styling bottom timeline tracker
ax2.set_yticks([0, 1])
ax2.set_yticklabels(['Batch 2 Milestones', 'Batch 1 Milestones'], fontsize=9, fontweight='semibold')
ax2.set_ylim(-0.8, 1.8)
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)
ax2.spines['left'].set_color('#BFBFBF')
ax2.spines['bottom'].set_color('#BFBFBF')
ax2.grid(axis='x', linestyle=':', alpha=0.5)

plt.tight_layout()

# 4. Render in Streamlit
st.pyplot(fig)
plt.close(fig)

# Additional Professional Metrics Summary Cards
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Base Fleet", value="30 Units")
with col2:
    st.metric(label="Total Inflow Planned", value="54 Units (2 Batches)")
with col3:
    st.metric(label="Adjustment Bottleneck", value="2 Units / Week")
