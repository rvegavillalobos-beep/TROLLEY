"""Conveyor defect tracker.

Run:  streamlit run app.py
Data: SharePoint (via secrets), a synced local path, or an uploaded workbook.
See README.md for setup.
"""
from __future__ import annotations

import io
import os
from datetime import datetime

import pandas as pd
import streamlit as st

from dashboard import charts, linemap, metrics, theme
from dashboard.data import CLOSED, OPEN, PENDING, SEVERITIES, STATUSES, Workbook, WorkbookError, read_workbook
from dashboard.source import Loaded, SourceError, fetch_sharepoint, local_path, read_local

G = 9.80665  # m/s² per g

st.set_page_config(page_title="Conveyor defect tracker", page_icon=":material/conveyor_belt:", layout="wide")
st.html(theme.CSS)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def _secrets() -> dict:
    try:
        return {k: (dict(v) if hasattr(v, "keys") else v) for k, v in st.secrets.items()}
    except Exception:  # noqa: BLE001 - no secrets file is a normal state
        return {}


@st.cache_data(ttl=300, show_spinner="Reading the workbook from SharePoint…")
def _load_sharepoint(cfg_items: tuple) -> Loaded:
    return fetch_sharepoint(dict(cfg_items))


@st.cache_data(show_spinner=False)
def _load_local(path: str, _mtime: float) -> Loaded:
    # _mtime isn't used in the body; it's part of the cache key so a re-synced file reloads.
    return read_local(path)


@st.cache_data(show_spinner="Reading the workbook…")
def _parse(content: bytes, today: str) -> Workbook:
    return read_workbook(content, pd.Timestamp(today))


def load(upload) -> tuple[Loaded | None, list[str]]:
    notes: list[str] = []
    if upload is not None:
        return Loaded(upload.getvalue(), "upload", "Uploaded file", upload.name), notes
    secrets = _secrets()
    sp = secrets.get("sharepoint")
    if isinstance(sp, dict) and sp.get("file_url"):
        try:
            return _load_sharepoint(tuple(sorted((k, str(v)) for k, v in sp.items()))), notes
        except Exception as exc:  # noqa: BLE001 - show any connection problem and fall back
            notes.append(f"SharePoint: {exc}")
    path = local_path(secrets)
    if path:
        try:
            p = os.path.expandvars(os.path.expanduser(path))
            mtime = os.path.getmtime(p) if os.path.exists(p) else 0.0
            return _load_local(path, mtime), notes
        except SourceError as exc:
            notes.append(f"Local file: {exc}")
    return None, notes


with st.sidebar:
    st.markdown("### Data")
    upload = st.file_uploader("Use a different workbook", type=["xlsx", "xlsm"],
                              help="For this session only. Without an upload the app reads SharePoint "
                                   "or the synced file set up in the secrets.")
    if st.button("Reload data", icon=":material/refresh:", width="stretch"):
        st.cache_data.clear()
        st.rerun()
    cluster_slot = st.container()
    st.markdown("### Forecast")
    horizon = st.slider("Forecast horizon (weeks)", 0, 12, 6)
    basis = st.radio("Closing pace", ["Trend over all weeks", "Recent weeks only"],
                     help="Trend: a straight line through every week's closed total, so one batch of closures "
                          "doesn't swing it. Recent: only what was closed in the recent window.")
    st.markdown("### Settings")
    window = st.slider("Recent window (weeks)", 2, 8, 4,
                       help="Used for 'found vs closed lately' in the summary sentence, and for the forecast "
                            "when the closing pace is set to recent weeks.")
    limit_g = st.number_input("Acceleration limit (g)", min_value=0.01, max_value=2.0, value=0.16, step=0.01,
                              format="%.2f", help="Used in the measurement campaign tab.")

loaded, notes = load(upload)
with st.sidebar:
    for n in notes:
        st.warning(n, icon=":material/cloud_off:")

if loaded is None:
    st.html(theme.masthead("Not connected", "None", "–", "–"))
    st.html("""
<div class="empty">
  <h2>Connect the tracker workbook</h2>
  <p>The dashboard reads the <b>Data</b> sheet of <i>Conveyors measurement &amp; fix tracking</i>. Pick one:</p>
  <ul>
    <li><b>SharePoint</b>: add the app registration and file link to the secrets. The app then reads the live file.</li>
    <li><b>Synced folder</b>: sync the SharePoint library with OneDrive and set its path in the secrets.</li>
    <li><b>Upload</b>: drop the workbook below for a one-off look.</li>
  </ul>
</div>""")
    first = st.file_uploader("Upload the workbook", type=["xlsx", "xlsm"], key="first_upload")
    if first is not None:
        loaded = Loaded(first.getvalue(), "upload", "Uploaded file", first.name)
    else:
        st.stop()

today = pd.Timestamp.today().normalize()
try:
    wb = _parse(loaded.content, today.isoformat())
except WorkbookError as exc:
    st.error(f"{exc} Pick the tracker workbook, or check that its first row holds the column names.",
             icon=":material/error:")
    st.stop()

df = wb.defects
campaign = wb.campaign
cluster = None
clusters = sorted(df["Cluster"].dropna().unique()) if "Cluster" in df else []
if clusters:
    with cluster_slot:
        st.markdown("### Cluster")
        pick = st.selectbox("Cluster", ["All clusters"] + clusters, label_visibility="collapsed",
                            help="From the Cluster column of the Data sheet.")
    if pick != "All clusters":
        cluster = pick
        df = df[df["Cluster"].eq(cluster)].reset_index(drop=True)
        if campaign is not None:
            campaign = campaign[campaign["Cluster"].astype(str).str.upper().eq(str(cluster).upper())]
if df.empty:
    st.info("No defects for this selection.", icon=":material/filter_alt_off:")
    st.stop()
latest = pd.concat([df["Date Open"], df["Date Closed"]]).max()
saved = loaded.modified.astimezone().strftime("%d %b %Y, %H:%M") if loaded.modified else datetime.now().strftime("%d %b %Y, %H:%M")
st.html(theme.masthead(
    loaded.label, loaded.file_name,
    latest.strftime("%d %b %Y") if pd.notna(latest) else "–",
    saved))

fix_checks = [i for i in wb.issues if i.action == "fix"]
tab_names = ["Overview", "Follow-up", "Measurement campaign",
             f"Data health ({len(fix_checks)})" if fix_checks else "Data health", "All records"]
t_over, t_follow, t_camp, t_health, t_records = st.tabs(tab_names)

DISPLAY_COLS = ["Excel row", "Severity", "Status", "Days open", "Conveyor", "Station", "Category",
                "Owner", "Date Open", "Date Closed", "Comments"]
COLUMN_CONFIG = {
    "Excel row": st.column_config.NumberColumn("Excel row", format="%d", width="small",
                                               help="Row number in the Data sheet"),
    "Days open": st.column_config.NumberColumn("Days open", format="%d", width="small"),
    "Date Open": st.column_config.DateColumn("Opened", format="D MMM YYYY"),
    "Date Closed": st.column_config.DateColumn("Closed", format="D MMM YYYY"),
    "Comments": st.column_config.TextColumn("Comments", width="large"),
}


def blank_text(frame: pd.DataFrame) -> pd.DataFrame:
    """Show missing text as an empty cell instead of 'None'."""
    out = frame.copy()
    for c in out.columns:
        if out[c].dtype == object or pd.api.types.is_string_dtype(out[c]):
            out[c] = out[c].where(out[c].notna(), "")
    return out


def table(frame: pd.DataFrame, height: int | None = None, cols: list[str] | None = None):
    cols = [c for c in (cols or DISPLAY_COLS) if c in frame.columns]
    kw = {"height": height} if height else {}
    st.dataframe(blank_text(frame[cols]), hide_index=True, width="stretch", column_config=COLUMN_CONFIG, **kw)


def plot(fig, key: str):
    st.plotly_chart(fig, key=key, config=charts.config(key), theme=None, width="stretch")


def downloads(frame: pd.DataFrame, stem: str, key: str):
    c1, c2, _ = st.columns([1, 1, 3])
    c1.download_button("Download CSV", frame.to_csv(index=False).encode("utf-8-sig"), f"{stem}.csv",
                       "text/csv", icon=":material/download:", key=f"{key}_csv", width="stretch")
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as xw:
        frame.to_excel(xw, index=False, sheet_name="Defects")
    c2.download_button("Download Excel", buf.getvalue(), f"{stem}.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       icon=":material/download:", key=f"{key}_xlsx", width="stretch")


def fmt_num(v: float) -> str:
    return f"{v:.0f}" if abs(v - round(v)) < 0.05 else f"{v:.1f}"


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------
with t_over:
    s = metrics.summary(df, today, window)
    hist = metrics.weekly_status(df, today)
    trend = metrics.trend_pace(hist)
    pace = trend if basis.startswith("Trend") else s.closing_rate
    fc = metrics.forecast(hist, pace, horizon)

    st.html(theme.overview_title("Defect status" + (f", cluster {cluster}" if cluster else "")))
    # Counts + trend on one pure-white panel, so a single screenshot drops straight into a slide
    with st.container(key="snapshot"):
        st.html(theme.kpis(s.open, s.pending, s.closed)
                + '<p class="snap-title">Defect Status Trend &amp; Burndown per Calendar Week</p>')
        if len(hist):
            plot(charts.status_trend(hist, fc if horizon else None), "trend")
    excluded = int((df["Status"].eq(CLOSED) & df["Date Closed"].isna()).sum() + df["Date Open"].isna().sum())
    if excluded:
        st.html(f'<p class="foot" style="margin-top:0.5rem">{excluded} rows are left out of the trend because a '
                "date is missing. See Data health.</p>")

    crit_label = ("Critical defect still open" if s.critical_open == 1 else "Critical defects still open") + (
        f", plus {s.major_open} major" if s.major_open else "")
    st.html(theme.facts([
        (str(s.critical_open), "", crit_label),
        (fmt_num(s.median_days_to_close) if s.median_days_to_close is not None else "–", "days",
         "Median time from open to close"),
        (fmt_num(s.oldest_open_days) if s.oldest_open_days is not None else "–", "days",
         f"Oldest open item ({s.oldest_open_label})" if s.oldest_open_label else "Oldest open item"),
        (fmt_num(trend), "per week",
         f"Average closing pace since {hist['Week'].iloc[0] if len(hist) else 'the start'}; "
         f"{s.closed_in_window} closed in the last {s.window_weeks} weeks"),
    ]))

    st.write("")
    with st.container(key="linemap"):
        st.html(theme.section(
            "Where the open defects sit on the line",
            "Each square is one defect that isn't closed yet, stacked on its station in line order. "
            "Hover for details, or drag a box across squares to list them below. Hovering a station's "
            "rail shows everything logged there.") + theme.linemap_legend())
        lm = linemap.build(df)
        event = st.plotly_chart(lm.figure, key="linemap_chart", on_select="rerun",
                                selection_mode=("points", "box", "lasso"), config=charts.config("line_map"),
                                theme=None, width="stretch")
    picked = linemap.selected_ids(event, lm, df)
    if picked:
        sel = df[df["id"].isin(picked)].sort_values(["Severity rank", "Days open"], ascending=[True, False])
        st.html(theme.section(f"{len(sel)} selected", "Double-click the map to clear the selection."))
        table(sel, cols=[c for c in DISPLAY_COLS if c != "Date Closed"])
    else:
        st.html('<p class="foot" style="margin-top:0.6rem">Nothing selected yet.</p>')

    st.write("")
    c1, c2 = st.columns([1.2, 1], gap="large")
    with c1:
        st.html(theme.section("Status by element type", "Everything logged, by type of element."))
        plot(charts.element_types(metrics.by_type(df)), "types")
    with c2:
        cat = metrics.by_category(df)
        done = cat[cat["Remaining"] == 0]["Category"].tolist()
        st.html(theme.section("What's left, by category",
                              f"Open and pending validation per category. Percentages are of the {s.backlog} issues "
                              "still open or pending validation, so together they add up to 100%."
                              + (f" Fully closed: {', '.join(done)}." if done else "")))
        if (cat["Remaining"] > 0).any():
            plot(charts.categories(cat, s.backlog), "cat")

    c3, c4 = st.columns([1.2, 1], gap="large")
    with c3:
        own = metrics.by_owner(df)
        st.html(theme.section("Who owns what's left",
                              "Handovers such as 'Maintenance -> LEAD' count for the receiving owner."))
        if len(own):
            plot(charts.owners(own), "owners")
    with c4:
        ct = metrics.closing_time(df)
        st.html(theme.section("How long closing takes",
                              "Dot = median days from open to close. Bar = the middle half of closed items."))
        if len(ct):
            plot(charts.closing_time(ct), "closing")


# ---------------------------------------------------------------------------
# Follow-up
# ---------------------------------------------------------------------------
with t_follow:
    st.html(theme.section("Follow-up",
                          "For the weekly review. Filters apply to everything on this tab; leave one empty to include all."))
    f1, f2, f3, f4, f5 = st.columns(5)
    sel_owner = f1.multiselect("Owner", sorted(df["Owner"].unique()), placeholder="All owners")
    sel_cat = f2.multiselect("Category", sorted(df["Category"].unique()), placeholder="All categories")
    sel_type = f3.multiselect("Element type", sorted(df["Type"].unique()), placeholder="All types")
    sel_sev = f4.multiselect("Severity", SEVERITIES, placeholder="All severities")
    sel_status = f5.multiselect("Status", STATUSES, default=[OPEN, PENDING], placeholder="All statuses")

    base = df
    for col, sel in (("Owner", sel_owner), ("Category", sel_cat), ("Type", sel_type), ("Severity", sel_sev)):
        if sel:
            base = base[base[col].isin(sel)]
    view = base[base["Status"].isin(sel_status)] if sel_status else base

    st.html(theme.section("Owner board", f"{len(view[view['Status'].ne(CLOSED)])} items not closed in this selection."))
    board = metrics.by_owner(view)
    if len(board):
        st.dataframe(
            board[["Owner", OPEN, PENDING, "Critical", "Major", "Oldest (days)", "Median age (days)"]],
            hide_index=True, width="stretch",
            column_config={
                OPEN: st.column_config.ProgressColumn("Open", format="%d", min_value=0,
                                                      max_value=int(max(board[OPEN].max(), 1))),
                PENDING: st.column_config.NumberColumn("Confirmation pending", format="%d"),
                "Critical": st.column_config.NumberColumn("Critical", format="%d"),
                "Major": st.column_config.NumberColumn("Major", format="%d"),
                "Oldest (days)": st.column_config.NumberColumn("Oldest (days)", format="%d"),
                "Median age (days)": st.column_config.NumberColumn("Median age (days)", format="%d"),
            })
    else:
        st.info("Nothing open in this selection.", icon=":material/check_circle:")

    a1, a2 = st.columns(2, gap="large")
    with a1:
        st.html(theme.section("How old the open items are", "Items not closed, by days since they were opened."))
        ag = metrics.aging(view)
        if ag[SEVERITIES].values.sum():
            plot(charts.aging(ag), "aging")
    with a2:
        st.html(theme.section("Found and closed per week", "Calendar weeks; ignores the status filter."))
        wf = metrics.weekly_flow(base, today)
        if len(wf):
            plot(charts.weekly_flow(wf), "flow")

    ht = metrics.heat(view)
    if len(ht):
        st.html(theme.section("Hot spots", "Items not closed, by conveyor and category. Top 20 conveyors."))
        plot(charts.heatmap(ht), "heat")

    st.html(theme.section("Action list", "Most severe first, then oldest."))
    actions = metrics.action_list(view)
    act_cols = [c for c in DISPLAY_COLS if c != "Date Closed" or (sel_status and CLOSED in sel_status)]
    table(actions, height=min(42 + 35 * len(actions), 560), cols=act_cols)
    downloads(actions[[c for c in DISPLAY_COLS if c in actions.columns] + ["Responsible", "Type"]],
              "action_list", "act")


# ---------------------------------------------------------------------------
# Measurement campaign
# ---------------------------------------------------------------------------
with t_camp:
    c = campaign
    if wb.campaign is not None and (c is None or c.empty):
        st.info(f"No campaign faults for cluster {cluster}.", icon=":material/filter_alt_off:")
    elif c is None or c.empty:
        st.info("This workbook has no campaign sheet (a sheet with 'Problem description' and 'Fix status' columns).",
                icon=":material/info:")
    else:
        limit_ms2 = limit_g * G
        linked = int(c["Linked"].sum())
        n_closed = int(c["Status"].eq(CLOSED).sum())
        n_left = int(c["Status"].ne(CLOSED).sum())
        n_rem = int(c["Remeasure requested"].sum())
        n_meas = int(c["Measurement (m/s²)"].notna().sum())
        st.html(theme.lead(
            f"{n_closed} of {len(c)} campaign faults are closed.",
            f"The measurement campaign ('{wb.campaign_sheet}') logged {len(c)} faults. {linked} of them match a row "
            f"in '{wb.defect_sheet}' by description, so their status here is the current one from the tracker.")
            + theme.facts([
                (str(n_left), "", "Open or confirmation pending"),
                (str(n_rem), "", "Marked for remeasurement"),
                (f"{n_meas} of {len(c)}", "", "Have a measured value"),
                (f"{limit_ms2:.2f}", "m/s²", f"Limit ({limit_g:.2f} g)"),
            ]))
        st.write("")
        k1, k2 = st.columns(2, gap="large")
        with k1:
            st.html(theme.section("By PLC"))
            plot(charts.campaign_status(c, "PLC"), "plc")
        with k2:
            st.html(theme.section("By fault type"))
            plot(charts.campaign_status(c, "Fault"), "fault")
        k3, k4 = st.columns(2, gap="large")
        with k3:
            st.html(theme.section("By cluster"))
            plot(charts.campaign_status(c, "Cluster"), "cluster")
        with k4:
            over = int((c["Measurement (m/s²)"].abs() > limit_ms2).sum())
            st.html(theme.section("Measured peak acceleration",
                                  f"{n_meas} of {len(c)} faults have a value; {over} above the limit. "
                                  "Add values to the measurement column to fill this in."))
            if n_meas:
                plot(charts.measurements(c, limit_ms2), "meas")
        rem = c[c["Remeasure requested"]]
        if len(rem):
            st.html(theme.section("Marked for remeasurement", "Excel rows refer to the campaign sheet."))
            st.dataframe(blank_text(rem[["Excel row", "Conveyor", "Station", "PLC", "Cluster", "Fault", "Status",
                              "Measurement (m/s²)", "Description"]]),
                         hide_index=True, width="stretch",
                         column_config={"Excel row": st.column_config.NumberColumn(format="%d", width="small"),
                                        "Description": st.column_config.TextColumn(width="large"),
                                        "Measurement (m/s²)": st.column_config.NumberColumn(format="%.2f")})


# ---------------------------------------------------------------------------
# Data health
# ---------------------------------------------------------------------------
with t_health:
    fix_rows = sum(i.count for i in fix_checks)
    info_checks = [i for i in wb.issues if i.action == "info"]
    if fix_checks:
        st.html(theme.lead(
            f"{len(fix_checks)} checks need a correction in the Excel.",
            f"{fix_rows} rows in total. The dashboard still works, but these rows are counted with a fallback or left "
            "out of some charts. Excel row numbers point to the line to fix."))
    else:
        st.html(theme.lead("The workbook is clean.", "No rows need a correction."))
    st.write("")
    for issue in fix_checks + info_checks:
        with st.expander(f"{issue.title} ({issue.count})", icon=(":material/edit:" if issue.action == "fix"
                                                                   else ":material/auto_fix_high:")):
            st.html(f'<div class="dh-row">{theme.tag(issue.action)}<span>{theme.esc(issue.explanation)}</span></div>')
            st.dataframe(blank_text(issue.rows), hide_index=True, width="stretch",
                         column_config={**COLUMN_CONFIG,
                                        "Excel row": st.column_config.NumberColumn("Excel row", format="%d",
                                                                                   width="small")})


# ---------------------------------------------------------------------------
# All records
# ---------------------------------------------------------------------------
with t_records:
    st.html(theme.section("All records", f"{len(df)} rows from '{wb.defect_sheet}', cleaned as described in Data health."))
    q = st.text_input("Search", placeholder="Conveyor, station, owner or words in the comments",
                      label_visibility="collapsed")
    rec = df
    if q:
        hay = (df["Conveyor"].fillna("") + " " + df["Station"].fillna("") + " " + df["Owner"].fillna("") + " "
               + df["Category"].fillna("") + " " + df["Comments"].fillna(""))
        rec = df[hay.str.contains(q, case=False, regex=False)]
    st.caption(f"{len(rec)} of {len(df)} rows")
    cols = DISPLAY_COLS + ["Type", "Responsible"]
    table(rec, height=600, cols=cols)
    downloads(rec[[c for c in cols if c in rec.columns]], "defects", "rec")
