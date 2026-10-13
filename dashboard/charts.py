"""Plotly figures. One look for every chart: thin marks, hairline grid,
sentence-case labels, legends on top, tooltips that add detail."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .data import CLOSED, CRITICAL, MAJOR, MINOR, OPEN, PENDING, SEVERITIES, UNASSIGNED
from .theme import (AXIS, FONT, FOUND, HAIR, HEAT, INK, INK_2, MUTED, PAGE, SEVERITY_LIGHT,
                    SINGLE, STATUS_COLORS, STATUS_LABELS)

CONFIG = {"displayModeBar": False, "displaylogo": False, "responsive": True}


def _axis(**kw) -> dict:
    base = dict(gridcolor=HAIR, gridwidth=1, linecolor=AXIS, zeroline=False, ticks="",
                tickfont=dict(color=MUTED, size=12), title_font=dict(color=INK_2, size=12),
                automargin=True, showspikes=False)
    base.update(kw)
    return base


def style(fig: go.Figure, height: int, legend: bool = True, top: int | None = None) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=4, r=24, t=top if top is not None else (40 if legend else 10), b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=13, color=INK_2),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=HAIR, font=dict(family=FONT, size=13, color=INK), align="left"),
        showlegend=legend,
        legend=dict(orientation="h", x=0, xanchor="left", y=1.0, yanchor="bottom", title_text="",
                    font=dict(size=13, color=INK_2), itemclick="toggleothers", traceorder="normal"),
        bargap=0.38, barcornerradius=3,
        xaxis=_axis(), yaxis=_axis(),
    )
    return fig


def _gap_line() -> dict:
    """A thin page-colored outline: a visible 2px gap between stacked fills."""
    return dict(color=PAGE, width=1.5)


def _cw_axis(fig: go.Figure, start, end) -> None:
    start = pd.Timestamp(start)
    monday = start - pd.Timedelta(days=start.weekday())
    span_weeks = max((pd.Timestamp(end) - monday).days / 7, 1)
    step = 1 if span_weeks <= 10 else 2 if span_weeks <= 24 else 4
    fig.update_xaxes(type="date", tickformat="CW%V", tick0=monday, dtick=step * 7 * 86_400_000,
                     showgrid=False, hoverformat="%a %d %b %Y")


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------
def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alpha})"


def status_trend(hist: pd.DataFrame, fc: pd.DataFrame | None) -> go.Figure:
    """Stacked areas per calendar week (Closed, Confirmation pending, Open) with a lighter forecast."""
    order = (CLOSED, PENDING, OPEN)
    fig = go.Figure()
    for status in order:
        fig.add_trace(go.Scatter(
            x=hist["Week"], y=hist[status], name=STATUS_LABELS[status], legendgroup=status,
            mode="lines", stackgroup="actual", line=dict(color=STATUS_COLORS[status], width=1.5),
            fillcolor=_rgba(STATUS_COLORS[status], 0.78),
            hovertemplate=STATUS_LABELS[status] + ": %{y:.0f}<extra></extra>"))
    if fc is not None and len(fc):
        joined = pd.concat([hist.iloc[[-1]], fc], ignore_index=True)
        for status in order:
            fig.add_trace(go.Scatter(
                x=joined["Week"], y=joined[status], name=STATUS_LABELS[status], legendgroup=status,
                showlegend=False, mode="lines", stackgroup="forecast",
                line=dict(color=STATUS_COLORS[status], width=1.5, dash="dash"),
                fillcolor=_rgba(STATUS_COLORS[status], 0.24),
                hovertemplate=STATUS_LABELS[status] + " (forecast): %{y:.0f}<extra></extra>"))
        start = hist["Week"].iloc[-1]
        weeks = joined["Week"].tolist()
        fig.add_shape(type="line", xref="x", yref="paper", x0=start, x1=start, y0=0, y1=1,
                      line=dict(color=MUTED, width=1, dash="dot"))
        fig.add_annotation(x=weeks[len(weeks) // 2], y=1.06, xref="x", yref="paper", text="FORECAST",
                           showarrow=False, font=dict(family=FONT, size=14, color=INK),
                           bgcolor="rgba(255,255,255,0.9)", bordercolor=MUTED, borderwidth=1, borderpad=5)
    style(fig, 450, top=40)
    fig.update_layout(hovermode="x unified",
                      legend=dict(orientation="h", x=0, xanchor="left", y=-0.16, yanchor="top"))
    fig.update_xaxes(type="category", showgrid=False, title_text="Week", tickfont=dict(color=INK_2, size=12))
    fig.update_yaxes(rangemode="tozero", title_text="Defects")
    return fig


def element_types(t: pd.DataFrame) -> go.Figure:
    """Status by element type: stacked columns, closed at the bottom."""
    fig = go.Figure()
    for status in (CLOSED, PENDING, OPEN):
        fig.add_trace(go.Bar(x=t["Type"], y=t[status], name=STATUS_LABELS[status],
                             marker=dict(color=STATUS_COLORS[status], line=_gap_line()),
                             hovertemplate="%{x}<br>" + STATUS_LABELS[status] + ": %{y}<extra></extra>"))
    fig.add_trace(go.Scatter(x=t["Type"], y=t["Total"], mode="text", text=t["Total"].astype(str),
                             textposition="top center", textfont=dict(color=INK, size=13),
                             showlegend=False, hoverinfo="skip", cliponaxis=False))
    style(fig, 380)
    fig.update_layout(barmode="stack", bargap=0.3)
    fig.update_xaxes(type="category", showgrid=False, tickfont=dict(color=INK, size=13))
    fig.update_yaxes(rangemode="tozero", range=[0, max(t["Total"].max(), 1) * 1.15], title_text="Defects")
    return fig


def _hbar_status(df: pd.DataFrame, label_col: str, end_text: list[str], height_per: int = 34) -> go.Figure:
    df = df.iloc[::-1]  # biggest on top
    fig = go.Figure()
    for status in (OPEN, PENDING):
        fig.add_trace(go.Bar(
            y=df[label_col], x=df[status], name=STATUS_LABELS[status], orientation="h",
            marker=dict(color=STATUS_COLORS[status], line=_gap_line()),
            hovertemplate="%{y}<br>" + STATUS_LABELS[status] + ": %{x}<extra></extra>"))
    totals = (df[OPEN] + df[PENDING]).tolist()
    fig.add_trace(go.Scatter(
        y=df[label_col], x=totals, mode="text", text=["\u2002" + t for t in reversed(end_text)],
        textposition="middle right",
        textfont=dict(size=12, color=INK_2), showlegend=False, hoverinfo="skip", cliponaxis=False))
    style(fig, 56 + height_per * len(df))
    fig.update_layout(barmode="stack", bargap=0.32)
    fig.update_xaxes(showgrid=True, rangemode="tozero", range=[0, max(totals + [1]) * 1.28], title_text=None)
    fig.update_yaxes(showgrid=False, tickfont=dict(color=INK, size=13))
    return fig


def categories(cat: pd.DataFrame) -> go.Figure:
    d = cat[cat["Remaining"] > 0].reset_index(drop=True)
    end = [f"{r.Remaining} of {r.Logged}" for r in d.itertuples()]
    return _hbar_status(d, "Category", end)


def owners(own: pd.DataFrame) -> go.Figure:
    end = [f"{int(r.Remaining)}" + (f", {int(r.Critical)} critical" if r.Critical else "") for r in own.itertuples()]
    return _hbar_status(own, "Owner", end)


def closing_time(ct: pd.DataFrame) -> go.Figure:
    d = ct.iloc[::-1]
    fig = go.Figure()
    for r in d.itertuples():
        fig.add_trace(go.Scatter(x=[r.p25, r.p75], y=[r.Category, r.Category], mode="lines",
                                 line=dict(color="#C9CCC7", width=7), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(
        x=d["Median"], y=d["Category"], mode="markers", showlegend=False,
        marker=dict(color=SINGLE, size=12, line=dict(color=PAGE, width=2)),
        customdata=np.stack([d["n"], d["p25"], d["p75"]], axis=-1),
        hovertemplate="%{y}<br>Median: %{x:.0f} days<br>Middle half: %{customdata[1]:.0f}–%{customdata[2]:.0f} days"
                      "<br>Closed items: %{customdata[0]}<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=np.maximum(d["p75"], d["Median"]), y=d["Category"], mode="text", showlegend=False, hoverinfo="skip",
        text=[f"\u2002{m:.0f} d" for m in d["Median"]], textposition="middle right",
        textfont=dict(size=12, color=INK_2), cliponaxis=False))
    style(fig, 56 + 34 * len(d), legend=False, top=10)
    fig.update_xaxes(rangemode="tozero", title_text="Days from open to close",
                     range=[0, max(d["p75"].max(), d["Median"].max()) * 1.2 + 2])
    fig.update_yaxes(showgrid=False, tickfont=dict(color=INK, size=13))
    return fig


# ---------------------------------------------------------------------------
# Follow-up
# ---------------------------------------------------------------------------
def aging(ag: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for sev in SEVERITIES:
        fig.add_trace(go.Bar(x=ag["Age"], y=ag[sev], name=sev,
                             marker=dict(color=SEVERITY_LIGHT[sev], line=_gap_line()),
                             hovertemplate="%{x}<br>" + sev + ": %{y}<extra></extra>"))
    totals = ag[SEVERITIES].sum(axis=1)
    fig.add_trace(go.Scatter(x=ag["Age"], y=totals, mode="text", text=[str(t) if t else "" for t in totals],
                             textposition="top center", textfont=dict(color=INK, size=13),
                             showlegend=False, hoverinfo="skip", cliponaxis=False))
    style(fig, 330)
    fig.update_layout(barmode="stack")
    fig.update_yaxes(rangemode="tozero", range=[0, max(totals.max(), 1) * 1.18], title_text="Open items")
    fig.update_xaxes(showgrid=False, tickfont=dict(color=INK, size=13))
    return fig


def weekly_flow(wf: pd.DataFrame) -> go.Figure:
    mid = wf["Week start"] + pd.Timedelta(days=3.5)
    fig = go.Figure()
    for col, color in (("Found", FOUND), ("Closed", STATUS_COLORS[CLOSED])):
        fig.add_trace(go.Bar(x=mid, y=wf[col], name=col, customdata=wf["Week"],
                             marker=dict(color=color, line=_gap_line()),
                             hovertemplate="%{customdata}<br>" + col + ": %{y}<extra></extra>"))
    style(fig, 330)
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.08)
    fig.update_yaxes(rangemode="tozero", title_text="Defects per week")
    _cw_axis(fig, wf["Week start"].min(), wf["Week start"].max() + pd.Timedelta(days=7))
    fig.update_xaxes(range=[wf["Week start"].min(), wf["Week start"].max() + pd.Timedelta(days=7)])
    return fig


def heatmap(t: pd.DataFrame) -> go.Figure:
    z = t.values.astype(float)
    z_plot = np.where(z == 0, np.nan, z)
    text = np.where(z == 0, "", z.astype(int).astype(str))
    zmax = max(np.nanmax(z) if z.size else 1, 1)
    scale = [[i / (len(HEAT) - 1), c] for i, c in enumerate(HEAT)]
    fig = go.Figure(go.Heatmap(
        z=z_plot, x=list(t.columns), y=list(t.index), text=text, texttemplate="%{text}",
        textfont=dict(family=FONT, size=12), colorscale=scale, zmin=0, zmax=zmax, showscale=False,
        xgap=2, ygap=2, hoverongaps=False,
        hovertemplate="%{y}<br>%{x}: %{z:.0f} not closed<extra></extra>"))
    style(fig, 70 + 26 * len(t.index), legend=False, top=10)
    fig.update_xaxes(side="top", showgrid=False, tickfont=dict(color=INK, size=12), linecolor="rgba(0,0,0,0)")
    fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(color=INK, size=12), linecolor="rgba(0,0,0,0)")
    fig.update_layout(plot_bgcolor=PAGE)
    return fig


# ---------------------------------------------------------------------------
# Measurement campaign
# ---------------------------------------------------------------------------
def campaign_status(c: pd.DataFrame, by: str) -> go.Figure:
    t = pd.crosstab(c[by], c["Status"]).reindex(columns=[OPEN, PENDING, CLOSED], fill_value=0)
    t = t.loc[t.sum(axis=1).sort_values(ascending=True).index]
    remeasure = c[c["Remeasure requested"]].groupby(by).size().reindex(t.index, fill_value=0)
    fig = go.Figure()
    for status in (OPEN, PENDING, CLOSED):
        fig.add_trace(go.Bar(y=t.index, x=t[status], name=STATUS_LABELS[status], orientation="h",
                             marker=dict(color=STATUS_COLORS[status], line=_gap_line()),
                             hovertemplate="%{y}<br>" + STATUS_LABELS[status] + ": %{x}<extra></extra>"))
    totals = t.sum(axis=1)
    end = ["\u2002" + f"{n}" + (f", {r} to remeasure" if r else "") for n, r in zip(totals, remeasure)]
    fig.add_trace(go.Scatter(y=t.index, x=totals, mode="text", text=end, textposition="middle right",
                             textfont=dict(size=12, color=INK_2), showlegend=False, hoverinfo="skip",
                             cliponaxis=False))
    style(fig, 60 + 36 * len(t))
    fig.update_layout(barmode="stack", bargap=0.32)
    fig.update_xaxes(range=[0, max(totals.max(), 1) * 1.35])
    fig.update_yaxes(showgrid=False, tickfont=dict(color=INK, size=13), type="category")
    return fig


def measurements(c: pd.DataFrame, limit_ms2: float) -> go.Figure:
    d = c.dropna(subset=["Measurement (m/s²)"]).copy()
    d["abs"] = d["Measurement (m/s²)"].abs()
    d["label"] = d["Conveyor"].fillna("") + " " + d["Station"].fillna("")
    over = d["abs"] > limit_ms2
    fig = go.Figure()
    fig.add_hline(y=limit_ms2, line=dict(color=STATUS_COLORS[OPEN], width=1.5))
    fig.add_annotation(x=1, xref="paper", y=limit_ms2, text=f"Limit {limit_ms2:.2f} m/s²", showarrow=False,
                       xanchor="right", yanchor="bottom", font=dict(size=12, color=STATUS_COLORS[OPEN]))
    fig.add_trace(go.Scatter(
        x=d["label"], y=d["abs"], mode="markers", showlegend=False,
        marker=dict(size=12, color=np.where(over, STATUS_COLORS[OPEN], STATUS_COLORS[CLOSED]),
                    line=dict(color=PAGE, width=2)),
        customdata=np.stack([d["Description"], d["Measurement (m/s²)"]], axis=-1),
        hovertemplate="%{x}<br>%{customdata[1]:.2f} m/s² (|a| = %{y:.2f})<br>%{customdata[0]}<extra></extra>"))
    style(fig, 300, legend=False, top=10)
    ymax = max(d["abs"].max() if len(d) else 0, limit_ms2) * 1.3
    fig.update_yaxes(range=[0, ymax], title_text="Peak acceleration |a| (m/s²)")
    fig.update_xaxes(showgrid=False, type="category", tickfont=dict(color=INK, size=12))
    return fig
