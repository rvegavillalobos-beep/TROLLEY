"""The line map: every station in process order on a conveyor band, with one
square per defect that isn't closed yet, stacked on its station."""
from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .data import CLOSED, OPEN, PENDING, SEVERITIES
from .theme import BAND, BAND_INK, BAND_MUTED, FONT, FONT_COND, INK, HAIR, RAIL, ROLLER, SEVERITY_LIGHT, STATUS_LABELS

NO_STATION = "No station"
GROUP_GAP = 1.8
UNIT_PX = 19  # vertical pixels per stacked square


def _station_key(label: str) -> tuple[int, int, str]:
    if label == NO_STATION:
        return (10, 0, label)
    m = re.match(r"^ST\s*(\d+)\s*$", label, re.I)
    if m:
        return (0, int(m.group(1)), label)
    m = re.match(r"^ST\s*(\d+)\s*([A-Z]+)$", label, re.I)
    if m:
        return (1, int(m.group(1)), label)
    m = re.match(r"^([A-Z]+)\s*(\d+)", label, re.I)
    if m:
        return (2 + (0 if m.group(1).upper() == "FT" else 1), int(m.group(2)), label)
    return (9, 0, label)


@dataclass
class LineMap:
    figure: go.Figure
    point_ids: list[list[int]]       # curve number -> defect ids, per point
    track_curve: int                 # curve number of the rail trace (hover only)
    track_stations: list[str]        # station per rail bar


def _wrap(text, width=56) -> str:
    if not isinstance(text, str) or not text:
        return ""
    return "<br>".join(textwrap.wrap(text, width)[:4])


def build(df: pd.DataFrame) -> LineMap:
    d = df.copy()
    d["Station"] = d["Station"].fillna(NO_STATION)
    stations = sorted(d["Station"].unique(), key=_station_key)

    # x positions with a gap between groups of stations
    pos, groups, x, prev = {}, [], 0.0, None
    for s in stations:
        g = _station_key(s)[0]
        if prev is not None and g != prev:
            x += GROUP_GAP
        if prev is None or g != prev:
            groups.append([s])
        else:
            groups[-1].append(s)
        pos[s] = x
        x += 1
        prev = g

    nc = d[d["Status"].ne(CLOSED)].copy()
    nc = nc.sort_values(["Station", "Severity rank", "Status", "Days open"],
                        ascending=[True, True, False, False], na_position="last")
    nc["y"] = nc.groupby("Station").cumcount() + 1
    nc["x"] = nc["Station"].map(pos)
    max_n = int(nc["y"].max()) if len(nc) else 1

    fig = go.Figure()
    point_ids: list[list[int]] = []

    # Rail: one bar per station, touching inside a group, with roller lines.
    counts = d.groupby("Station").agg(
        total=("id", "size"), closed=("Status", lambda s: int(s.eq(CLOSED).sum())),
        conveyors=("Conveyor", lambda s: ", ".join(sorted({c for c in s if isinstance(c, str)})[:8])))
    rail_x = [pos[s] for s in stations]
    rail_cd = np.stack([
        stations,
        [int(counts.loc[s, "total"]) for s in stations],
        [int(counts.loc[s, "closed"]) for s in stations],
        [int(counts.loc[s, "total"] - counts.loc[s, "closed"]) for s in stations],
        [counts.loc[s, "conveyors"] or "none recorded" for s in stations],
    ], axis=-1)
    fig.add_trace(go.Bar(
        x=rail_x, y=[0.82] * len(stations), base=[-0.62] * len(stations), width=1.0,
        marker=dict(color=RAIL, line=dict(width=0),
                    pattern=dict(shape="|", fgcolor=ROLLER, bgcolor=RAIL, size=7, solidity=0.3)),
        customdata=rail_cd, showlegend=False, name="Stations",
        hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]} logged, %{customdata[2]} closed, "
                      "%{customdata[3]} not closed<br>Conveyors: %{customdata[4]}<extra></extra>"))
    point_ids.append([])
    track_curve = 0

    # Defect squares, one trace per severity and status (filled = open, outlined = awaiting confirmation)
    for sev in SEVERITIES:
        for status, symbol in ((OPEN, "square"), (PENDING, "square-open")):
            sub = nc[(nc["Severity"] == sev) & (nc["Status"] == status)]
            if sub.empty:
                continue
            days = sub["Days open"].map(lambda v: f"{v:.0f} days" if pd.notna(v) else "age unknown")
            cd = np.stack([
                sub["Station"], sub["Conveyor"].fillna("station-level"), sub["Category"], sub["Severity"],
                [STATUS_LABELS[status]] * len(sub), days, sub["Owner"], sub["Comments"].map(_wrap),
            ], axis=-1)
            fig.add_trace(go.Scatter(
                x=sub["x"], y=sub["y"], mode="markers", name=f"{sev} ({STATUS_LABELS[status].lower()})",
                showlegend=False,
                marker=dict(symbol=symbol, size=12 if status == OPEN else 10.5, color=SEVERITY_LIGHT[sev],
                            line=dict(color=BAND if status == OPEN else SEVERITY_LIGHT[sev],
                                      width=1 if status == OPEN else 2.2)),
                selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=0.28)),
                customdata=cd,
                hovertemplate="<b>%{customdata[0]}</b>  %{customdata[1]}<br>%{customdata[2]}, %{customdata[3]}"
                              "<br>%{customdata[4]}, %{customdata[5]}<br>Owner: %{customdata[6]}"
                              "<br><br>%{customdata[7]}<extra></extra>"))
            point_ids.append(sub["id"].astype(int).tolist())

    # Stack totals, only where they stand out
    tops = nc.groupby("Station").agg(n=("y", "max"), x=("x", "first"))
    tops = tops[tops["n"] >= 3]
    if len(tops):
        fig.add_trace(go.Scatter(x=tops["x"], y=tops["n"] + 0.95, mode="text", text=tops["n"].astype(str),
                                 textfont=dict(family=FONT_COND, size=13, color=BAND_INK),
                                 hoverinfo="skip", showlegend=False))
        point_ids.append([])

    # Group captions: the station range each group covers
    for g in groups:
        kind = _station_key(g[0])[0]
        if kind >= 9:
            label = "No station" if kind == 10 else "Other areas"
        else:
            label = g[0] if len(g) == 1 else f"{g[0]} to {g[-1]}"
        if len(g) < len(label) / 3:  # too narrow for its caption; the tick labels say enough
            continue
        fig.add_annotation(x=pos[g[0]] - 0.5, y=max_n + 1.9, text=label, showarrow=False,
                           xanchor="left", yanchor="top", font=dict(family=FONT, size=12, color=BAND_MUTED))

    has_open = set(nc["Station"])
    ticktext = [s if s in has_open else f'<span style="color:{BAND_MUTED}">{s}</span>' for s in stations]
    height = int(110 + (max_n + 3.2) * UNIT_PX)
    fig.update_layout(
        height=height, margin=dict(l=6, r=6, t=8, b=8),
        paper_bgcolor=BAND, plot_bgcolor=BAND, font=dict(family=FONT, color=BAND_INK),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=HAIR, font=dict(family=FONT, size=13, color=INK), align="left"),
        dragmode="select", bargap=0, showlegend=False,
        xaxis=dict(range=[-0.9, x - 0.1], tickvals=rail_x, ticktext=ticktext, tickangle=-90,
                   tickfont=dict(family=FONT_COND, size=12, color=BAND_INK), showgrid=False, zeroline=False,
                   showline=False, ticks="", fixedrange=True, automargin=True),
        yaxis=dict(range=[-0.8, max_n + 2.0], visible=False, fixedrange=True),
    )
    return LineMap(fig, point_ids, track_curve, stations)


def selected_ids(event, lm: LineMap, df: pd.DataFrame) -> list[int]:
    """Translate a Streamlit plotly selection event into defect ids."""
    try:
        points = event.selection.points  # type: ignore[attr-defined]
    except AttributeError:
        try:
            points = event["selection"]["points"]
        except (KeyError, TypeError):
            return []
    ids: list[int] = []
    for p in points or []:
        curve = p.get("curve_number")
        idx = p.get("point_index", p.get("point_number"))
        if curve is None or idx is None:
            continue
        if curve == lm.track_curve:
            continue  # the rail is for hover only; a box that grazes it shouldn't pull in whole stations
        if 0 <= curve < len(lm.point_ids) and int(idx) < len(lm.point_ids[curve]):
            ids.append(lm.point_ids[curve][int(idx)])
    seen, out = set(), []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out
