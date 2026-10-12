"""KPIs and aggregations. Plain pandas, no Streamlit."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data import CLOSED, OPEN, PENDING, SEVERITIES, CRITICAL, MAJOR

AGE_BUCKETS = [(0, 7, "0–7 days"), (8, 14, "8–14 days"), (15, 30, "15–30 days"),
               (31, 60, "31–60 days"), (61, 10_000, "Over 60 days")]


@dataclass
class Summary:
    total: int
    open: int
    pending: int
    closed: int
    backlog: int
    closed_share: float
    critical_open: int
    major_open: int
    median_days_to_close: float | None
    oldest_open_days: float | None
    oldest_open_label: str | None
    window_weeks: int
    found_in_window: int
    closed_in_window: int
    closing_rate: float  # per week, over the window
    eta: pd.Timestamp | None
    eta_weeks: float | None
    top_category: str | None
    top_category_open: int
    as_of: pd.Timestamp


def not_closed(df: pd.DataFrame) -> pd.Series:
    return df["Status"].ne(CLOSED)


def summary(df: pd.DataFrame, today: pd.Timestamp, window_weeks: int = 4) -> Summary:
    today = today.normalize()
    n_open = int(df["Status"].eq(OPEN).sum())
    n_pending = int(df["Status"].eq(PENDING).sum())
    n_closed = int(df["Status"].eq(CLOSED).sum())
    backlog = n_open + n_pending
    nc = df[not_closed(df)]

    start = today - pd.Timedelta(weeks=window_weeks)
    found_w = int(((df["Date Open"] > start) & (df["Date Open"] <= today)).sum())
    closed_w = int(((df["Closed on"] > start) & (df["Closed on"] <= today)).sum())
    rate = closed_w / window_weeks if window_weeks else 0.0
    eta_weeks = backlog / rate if rate > 0 and backlog > 0 else (0.0 if backlog == 0 else None)
    eta = today + pd.Timedelta(weeks=eta_weeks) if eta_weeks is not None else None

    oldest = nc.dropna(subset=["Days open"]).sort_values("Days open", ascending=False).head(1)
    oldest_label = None
    if len(oldest):
        r = oldest.iloc[0]
        oldest_label = " ".join(x for x in [r["Conveyor"], r["Station"]] if isinstance(x, str))

    cat = nc["Category"].value_counts()
    med = df["Days to close"].median()

    return Summary(
        total=len(df), open=n_open, pending=n_pending, closed=n_closed, backlog=backlog,
        closed_share=n_closed / len(df) if len(df) else 0.0,
        critical_open=int(nc["Severity"].eq(CRITICAL).sum()),
        major_open=int(nc["Severity"].eq(MAJOR).sum()),
        median_days_to_close=None if pd.isna(med) else float(med),
        oldest_open_days=None if oldest.empty else float(oldest.iloc[0]["Days open"]),
        oldest_open_label=oldest_label,
        window_weeks=window_weeks, found_in_window=found_w, closed_in_window=closed_w,
        closing_rate=rate, eta=eta, eta_weeks=eta_weeks,
        top_category=None if cat.empty else str(cat.index[0]),
        top_category_open=0 if cat.empty else int(cat.iloc[0]),
        as_of=today,
    )


def headline(s: Summary) -> tuple[str, str]:
    """A plain-language lead for the overview: (headline, supporting sentence)."""
    if s.backlog == 0:
        head = f"All {s.total} logged defects are closed."
    else:
        crit = {0: "none of them critical", 1: "1 of them critical"}.get(
            s.critical_open, f"{s.critical_open} of them critical")
        noun = "defect on the line isn't" if s.backlog == 1 else "defects on the line aren't"
        head = f"{s.backlog} {noun} closed yet, {crit}."

    parts = []
    if s.top_category and s.backlog:
        parts.append(f"{s.top_category} accounts for {s.top_category_open} of them.")
    w = s.window_weeks
    if s.found_in_window or s.closed_in_window:
        trend = ("the backlog grew" if s.found_in_window > s.closed_in_window
                 else "the backlog shrank" if s.found_in_window < s.closed_in_window
                 else "the backlog held steady")
        parts.append(
            f"In the last {w} weeks the team closed {s.closed_in_window} and found {s.found_in_window}, so {trend}.")
    else:
        parts.append(f"Nothing was found or closed in the last {w} weeks.")
    return head, " ".join(parts)


# ---------------------------------------------------------------------------
# Trend
# ---------------------------------------------------------------------------
def burnup(df: pd.DataFrame, today: pd.Timestamp, s: Summary) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Cumulative found and closed per day, plus a projection of the closed line.

    The projection extends the recent closing pace until it reaches today's
    found total, i.e. assuming nothing new is found.
    """
    today = today.normalize()
    opened = df["Date Open"].dropna()
    if opened.empty:
        return pd.DataFrame(columns=["Date", "Found", "Closed"]), None
    start = opened.min()
    days = pd.date_range(start, max(today, opened.max()), freq="D")
    found = opened.value_counts().reindex(days, fill_value=0).cumsum()
    closed_dates = df["Closed on"].dropna()
    closed = closed_dates.value_counts().reindex(days, fill_value=0).cumsum()
    hist = pd.DataFrame({"Date": days, "Found": found.values, "Closed": closed.values})

    proj = None
    rate = s.closing_rate
    now_found, now_closed = int(hist["Found"].iloc[-1]), int(hist["Closed"].iloc[-1])
    gap = now_found - now_closed
    if rate > 0 and gap > 0:
        weeks = gap / rate
        end = today + pd.Timedelta(days=int(np.ceil(weeks * 7)))
        proj = pd.DataFrame({"Date": [today, end], "Closed": [now_closed, now_found]})
    return hist, proj


def weekly_flow(df: pd.DataFrame, today: pd.Timestamp) -> pd.DataFrame:
    opened = df["Date Open"].dropna()
    if opened.empty:
        return pd.DataFrame(columns=["Week start", "Week", "Found", "Closed"])
    start = (opened.min() - pd.Timedelta(days=opened.min().weekday())).normalize()
    weeks = pd.date_range(start, today.normalize(), freq="W-MON")
    if len(weeks) == 0 or weeks[0] != start:
        weeks = weeks.insert(0, start)

    def wk(s: pd.Series) -> pd.Series:
        s = s.dropna()
        return (s - pd.to_timedelta(s.dt.weekday, unit="D")).dt.normalize()

    f = wk(df["Date Open"]).value_counts()
    c = wk(df["Closed on"]).value_counts()
    out = pd.DataFrame({"Week start": weeks})
    out["Found"] = out["Week start"].map(f).fillna(0).astype(int)
    out["Closed"] = out["Week start"].map(c).fillna(0).astype(int)
    out["Week"] = out["Week start"].map(lambda d: f"CW{d.isocalendar()[1]:02d}")
    return out


# ---------------------------------------------------------------------------
# Breakdowns
# ---------------------------------------------------------------------------
def by_category(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("Category")
    out = pd.DataFrame({
        "Logged": g.size(),
        OPEN: g["Status"].apply(lambda s: int(s.eq(OPEN).sum())),
        PENDING: g["Status"].apply(lambda s: int(s.eq(PENDING).sum())),
        CLOSED: g["Status"].apply(lambda s: int(s.eq(CLOSED).sum())),
    }).reset_index()
    out["Remaining"] = out[OPEN] + out[PENDING]
    return out.sort_values(["Remaining", "Logged"], ascending=[False, False]).reset_index(drop=True)


def by_owner(df: pd.DataFrame) -> pd.DataFrame:
    nc = df[not_closed(df)]
    if nc.empty:
        return pd.DataFrame(columns=["Owner", OPEN, PENDING, "Critical", "Major", "Oldest (days)", "Median age (days)", "Remaining"])
    g = nc.groupby("Owner")
    out = pd.DataFrame({
        OPEN: g["Status"].apply(lambda s: int(s.eq(OPEN).sum())),
        PENDING: g["Status"].apply(lambda s: int(s.eq(PENDING).sum())),
        "Critical": g["Severity"].apply(lambda s: int(s.eq(CRITICAL).sum())),
        "Major": g["Severity"].apply(lambda s: int(s.eq(MAJOR).sum())),
        "Oldest (days)": g["Days open"].max(),
        "Median age (days)": g["Days open"].median(),
    }).reset_index()
    out["Remaining"] = out[OPEN] + out[PENDING]
    return out.sort_values(["Remaining", "Critical"], ascending=False).reset_index(drop=True)


def closing_time(df: pd.DataFrame) -> pd.DataFrame:
    d = df.dropna(subset=["Days to close"])
    if d.empty:
        return pd.DataFrame(columns=["Category", "n", "p25", "Median", "p75"])
    g = d.groupby("Category")["Days to close"]
    out = pd.DataFrame({
        "n": g.size(), "p25": g.quantile(0.25), "Median": g.median(), "p75": g.quantile(0.75),
    }).reset_index()
    return out.sort_values("Median", ascending=False).reset_index(drop=True)


def aging(df: pd.DataFrame) -> pd.DataFrame:
    nc = df[not_closed(df)].dropna(subset=["Days open"])
    rows = []
    for lo, hi, label in AGE_BUCKETS:
        sub = nc[(nc["Days open"] >= lo) & (nc["Days open"] <= hi)]
        row = {"Age": label}
        for sev in SEVERITIES:
            row[sev] = int(sub["Severity"].eq(sev).sum())
        rows.append(row)
    return pd.DataFrame(rows)


def heat(df: pd.DataFrame, top: int = 20) -> pd.DataFrame:
    """Open + pending counts, asset × category (top assets by count)."""
    nc = df[not_closed(df)]
    if nc.empty:
        return pd.DataFrame()
    t = pd.crosstab(nc["Asset"], nc["Category"])
    t = t.loc[t.sum(axis=1).sort_values(ascending=False).index[:top]]
    t = t[t.sum(axis=0).sort_values(ascending=False).index]
    return t


def action_list(df: pd.DataFrame) -> pd.DataFrame:
    """Not-closed items first (most severe, then oldest), closed items last."""
    d = df.assign(_closed=df["Status"].eq(CLOSED))
    d = d.sort_values(["_closed", "Severity rank", "Days open"], ascending=[True, True, False], na_position="last")
    return d.drop(columns="_closed")
