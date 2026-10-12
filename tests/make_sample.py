"""Build a synthetic tracker workbook for tests and screenshots.

Everything here is invented: it only mimics the structure of the real
workbook (sheet names, columns, the kinds of gaps people leave), so the
public repository never holds plant data.

    python tests/make_sample.py out.xlsx
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

SEED = 7
ANCHOR = pd.Timestamp("2026-07-06")

CONVEYORS = ([f"TR{n:03d}" for n in range(1, 12)] + [f"TL{n:03d}" for n in range(1, 13)]
             + ["TV001", "TV003", "TU001", "FC001"])
STATIONS = ["ST020", "ST130", "ST300", "ST390", "ST395", "ST410", "ST430", "ST460", "ST500", "ST540",
            "ST550", "ST710", "ST780", "ST810", "ST850", "ST870", "ST880", "ST890", "ST900", "ST920",
            "ST940", "ST950", "ST960", "ST970", "ST981", "ST050 F", "ST100 F", "FT001", "FT002"]
HOT = {"ST880": 5, "ST890": 4, "ST970": 3, "ST960": 2, "ST550": 2}
CATEGORIES = ["Sensors"] * 8 + ["Parametrization"] * 4 + ["Transition"] * 3 + ["Indexing"] * 2 + \
             ["Mechanical stop"] * 2 + ["Other"]
TEMPLATES = {
    "Sensors": "Sensor gap check and adjust on {c}",
    "Parametrization": "Ramp parameters reviewed for {c}",
    "Transition": "Collision at the start of the transition into {c}, {s}",
    "Indexing": "Movement when indexing the pins of {c} {s}",
    "Mechanical stop": "Collision with the mechanical stop at the end of {c} rotation",
    "Other": "Part shifts while stationary at {s}",
}
OWNERS = ["Maintenance"] * 5 + ["Supplier"] * 2 + ["LEAD"] * 2 + ["Maintenance/Contractor -> LEAD", "TBD", None]


def build(n: int = 160, seed: int = SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    weights = np.array([HOT.get(s, 1) for s in STATIONS], dtype=float)
    rows = []
    batches = [ANCHOR + pd.Timedelta(days=d) for d in (4, 11, 18, 49, 70, 88)]
    for i in range(n):
        station = rng.choice(STATIONS, p=weights / weights.sum())
        cat = rng.choice(CATEGORIES)
        station_level = cat == "Parametrization" and rng.random() < 0.6
        conveyor = None if station_level else rng.choice(CONVEYORS)
        ctype = "Station" if station_level else conveyor[:2]
        opened = batches[min(int(rng.exponential(1.6)), len(batches) - 1)] if rng.random() < 0.8 else \
            ANCHOR + pd.Timedelta(days=int(rng.integers(0, 92)))
        r = rng.random()
        status = "Closed" if r < 0.62 else ("Confirmation pending" if r < 0.68 else "Open")
        closed = opened + pd.Timedelta(days=int(rng.integers(2, 30))) if status == "Closed" else None
        if closed is not None and closed > ANCHOR + pd.Timedelta(days=95):
            closed = ANCHOR + pd.Timedelta(days=95)
        sev = rng.choice(["Minor", "Minor", "Major", "Critical", None, None], p=[.32, .12, .26, .04, .16, .10])
        rows.append({
            "Conveyor": conveyor, "Station": station, "Type": ctype, "Category": cat,
            "Status": status, "Severity": sev, "Date Open": opened, "Date Closed": closed,
            "Responsible": rng.choice(np.array(OWNERS, dtype=object)),
            "Comments": TEMPLATES[cat].format(c=conveyor or station, s=station) if rng.random() < 0.7 else None,
            "Cluster": "F" if station.endswith(" F") or station.startswith("FT") else rng.choice(["H", "H", "F"]),
        })
    data = pd.DataFrame(rows)
    # the usual human touches
    data.loc[3, "Category"] = "Parameters"
    data.loc[5, "Conveyor"] = "tl002"
    data.loc[6, "Type"] = None
    data.loc[8, ["Status", "Date Closed"]] = ["Closed", None]
    data.loc[9, "Date Open"] = None

    # campaign sheet: a snapshot of some transition / stop faults, plus one that isn't tracked
    camp_src = data[data["Category"].isin(["Transition", "Mechanical stop", "Indexing", "Other"])
                    & data["Comments"].notna()].drop_duplicates("Comments").head(24)
    camp = pd.DataFrame({
        "#": range(1, len(camp_src) + 1),
        "Problem description": camp_src["Comments"].values,
        "Conveyor": camp_src["Conveyor"].values,
        "Station": camp_src["Station"].values,
        "PLC": rng.choice(["PLC 1", "PLC 3", "PLC 5", "PLC 6"], len(camp_src)),
        "Cluster": rng.choice(["H", "H", "F"], len(camp_src)),
        "Measurment [m/s^2]": [round(float(v), 3) if rng.random() < 0.35 else None
                               for v in rng.normal(-1.4, 0.5, len(camp_src))],
        "Fix Status": rng.choice(["Open", "Closed", "Remeasure req"], len(camp_src), p=[.5, .35, .15]),
        "Type conveyor": [c[:2] if isinstance(c, str) else None for c in camp_src["Conveyor"]],
        "Fault": camp_src["Category"].replace({"Indexing": "Indexing Pins"}).values,
        "Responsible": None, "Start Date": camp_src["Date Open"].values, "Fixed date ": None, "Closed Date": None,
    })
    extra = camp.iloc[[0]].copy()
    extra["#"] = len(camp) + 1
    extra["Problem description"] = "Part moves while the carrier waits on the rack"
    camp = pd.concat([camp, extra], ignore_index=True)
    return data, camp


def write(path: str) -> None:
    data, camp = build()
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        data.to_excel(xw, sheet_name="Data", index=False)
        camp.to_excel(xw, sheet_name="Faults to fix_og", index=False)


if __name__ == "__main__":
    write(sys.argv[1] if len(sys.argv) > 1 else "sample.xlsx")
    print("written")
