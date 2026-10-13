"""KPIs and aggregations. Plain pandas, no Streamlit."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data import CLOSED, CRITICAL, MAJOR, OPEN, PENDING, SEVERITIES, iso_week_label

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
        parts.append(f"{s.top_category} accounts for {s.top_category_open} of the {s.backlog} not closed.")
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
def weekly_status(df: pd.DataFrame, today: pd.Timestamp) -> pd.DataFrame:
    """Weekly snapshot of Closed / Confirmation pending / Open.

    One checkpoint per calendar week (Sunday) and today. At each checkpoint an
    item counts as Closed if it was closed by then; otherwise it counts as
    Confirmation pending if that is its status today, else Open. So the height
    of each stack is everything found by that week.
    """
    today = today.normalize()
    cols = ["Date", "Week", CLOSED, PENDING, OPEN]
    d = df[df["Date Open"].notna() & ~(df["Status"].eq(CLOSED) & df["Closed on"].isna())]
    if d.empty:
        return pd.DataFrame(columns=cols)
    start = d["Date Open"].min().normalize()
    cps = pd.date_range(start, today, freq="W-SUN")
    if len(cps) == 0 or cps[-1] < today:
        cps = cps.append(pd.DatetimeIndex([today]))

    opened = d["Date Open"].to_numpy(dtype="datetime64[ns]")
    closed = d["Closed on"].to_numpy(dtype="datetime64[ns]")
    pending_now = d["Status"].eq(PENDING).to_numpy()
    rows = []
    for cp in cps:
        t = np.datetime64(cp, "ns")
        found = opened <= t
        done = found & ~np.isnat(closed) & (closed <= t)
        active = found & ~done
        rows.append({"Date": cp, CLOSED: int(done.sum()), PENDING: int((active & pending_now).sum()),
                     OPEN: int((active & ~pending_now).sum())})
    hist = pd.DataFrame(rows)
    hist["Week"] = hist["Date"].map(iso_week_label)
    return hist[cols]


def trend_pace(hist: pd.DataFrame) -> float:
    """Closures per week from a straight line fitted to the cumulative closed count.

    Uses every week since the first defect, so one batch of closures entering or
    leaving a short window doesn't swing the forecast.
    """
    if len(hist) < 2:
        return 0.0
    x = (hist["Date"] - hist["Date"].iloc[0]).dt.days.to_numpy(dtype=float) / 7
    slope = float(np.polyfit(x, hist[CLOSED].to_numpy(dtype=float), 1)[0])
    return max(slope, 0.0)


def forecast(hist: pd.DataFrame, rate: float, horizon: int = 6) -> pd.DataFrame | None:
    """Apply a closing pace (per week) to what's open at the last checkpoint.

    The rest is split in the current open / pending proportion; nothing new is
    assumed to be found.
    """
    if horizon <= 0 or hist.empty:
        return None
    last = hist.iloc[-1]
    remaining = int(last[OPEN] + last[PENDING])
    total = int(last[CLOSED]) + remaining
    share_open = last[OPEN] / remaining if remaining else 0.0
    rows = []
    for i in range(1, horizon + 1):
        when = last["Date"] + pd.Timedelta(weeks=i)
        c = min(last[CLOSED] + max(rate, 0.0) * i, total)
        rest = total - c
        rows.append({"Date": when, "Week": iso_week_label(when), CLOSED: c,
                     PENDING: rest * (1 - share_open), OPEN: rest * share_open})
    return pd.DataFrame(rows)[list(hist.columns)]


def by_type(df: pd.DataFrame) -> pd.DataFrame:
    t = pd.crosstab(df["Type"], df["Status"]).reindex(columns=[CLOSED, PENDING, OPEN], fill_value=0)
    t["Total"] = t.sum(axis=1)
    return t.sort_values(["Total", OPEN], ascending=False).reset_index()


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
