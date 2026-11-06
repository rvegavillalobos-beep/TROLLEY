import io

import pandas as pd
import pytest

from dashboard import metrics
from dashboard.data import (CLOSED, OPEN, PENDING, UNASSIGNED, WorkbookError, normalize_category,
                            normalize_severity, normalize_status, owner_from_responsible, read_workbook)
from dashboard.source import parse_sharepoint_url
from tests.make_sample import build

TODAY = pd.Timestamp("2026-10-12")


def _xlsx(data: pd.DataFrame, camp: pd.DataFrame | None = None) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        data.to_excel(xw, sheet_name="Data", index=False)
        if camp is not None:
            camp.to_excel(xw, sheet_name="Faults to fix_og", index=False)
    return buf.getvalue()


@pytest.fixture(scope="module")
def wb():
    data, camp = build()
    return read_workbook(_xlsx(data, camp), TODAY)


def test_normalizers():
    assert normalize_status(" closed ") == CLOSED
    assert normalize_status("Confirmation pending") == PENDING
    assert normalize_status("OPEN") == OPEN
    assert normalize_status(None) is None
    assert normalize_severity("major") == "Major"
    assert normalize_severity(float("nan")) == UNASSIGNED
    assert normalize_category("Parameters") == "Parametrization"
    assert normalize_category("Indexing Pins") == "Indexing"
    assert owner_from_responsible("Maintenance/Contractor -> LEAD") == "LEAD"
    assert owner_from_responsible("TBD") == "Unassigned"
    assert owner_from_responsible(None) == "Unassigned"


def test_cleaning(wb):
    d = wb.defects
    assert wb.defect_sheet == "Data" and wb.campaign_sheet == "Faults to fix_og"
    assert "Parameters" not in set(d["Category"])
    assert "tl002" not in set(d["Conveyor"].dropna())
    assert set(d["Status"]) <= {OPEN, PENDING, CLOSED}
    assert d["Excel row"].min() == 2
    # closed items never carry an age, open items never carry days-to-close
    assert d.loc[d["Status"].eq(CLOSED), "Days open"].isna().all()
    assert d.loc[d["Status"].ne(CLOSED), "Days to close"].isna().all()


def test_issues(wb):
    keys = {i.key: i for i in wb.issues}
    assert keys["category_alias"].count >= 1
    assert keys["conveyor_case"].count == 1
    assert keys["closed_no_date"].count >= 1
    assert keys["no_open_date"].count >= 1
    assert keys["campaign_unlinked"].count == 1
    assert all("Excel row" in i.rows.columns for i in wb.issues)


def test_campaign_links(wb):
    c = wb.campaign
    assert c["Linked"].sum() == len(c) - 1
    linked = c[c["Linked"]]
    status = wb.defects.set_index("Excel row")["Status"]
    assert (linked["Status"].values == status.loc[linked["Tracker row"].astype(int)].values).all()


def test_summary_and_trend(wb):
    d = wb.defects
    s = metrics.summary(d, TODAY, 4)
    assert s.open + s.pending + s.closed == len(d)
    assert s.backlog == s.open + s.pending
    hist = metrics.weekly_status(d, TODAY)
    pace = metrics.trend_pace(hist)
    assert pace > 0
    fc = metrics.forecast(hist, pace, 6)
    charted = d[d["Date Open"].notna() & ~(d["Status"].eq(CLOSED) & d["Closed on"].isna())]
    last = hist.iloc[-1]
    assert last[CLOSED] == charted["Closed on"].notna().sum()
    assert last[CLOSED] + last[OPEN] + last[PENDING] == len(charted)
    assert last[PENDING] == charted["Status"].eq(PENDING).sum()
    stack = hist[[CLOSED, PENDING, OPEN]].sum(axis=1)
    assert stack.is_monotonic_increasing          # each week's stack = everything found by then
    assert hist[CLOSED].is_monotonic_increasing
    assert hist["Week"].is_unique
    assert len(fc) == 6 and fc[CLOSED].is_monotonic_increasing
    assert (fc[[CLOSED, PENDING, OPEN]].sum(axis=1).round(6) == stack.iloc[-1]).all()
    head, sub = metrics.headline(s)
    assert str(s.backlog) in head


def test_trend_without_pace():
    data, _ = build()
    wbx = read_workbook(_xlsx(data), TODAY)
    hist = metrics.weekly_status(wbx.defects, TODAY)
    fc = metrics.forecast(hist, 0.0, 3)
    assert (fc[CLOSED] == hist[CLOSED].iloc[-1]).all()   # flat when nothing is being closed


def test_trend_pace_ignores_window_edges():
    """A batch of closures leaving a short window must not flatten the trend pace."""
    data, _ = build()
    d = read_workbook(_xlsx(data), TODAY).defects
    a = metrics.trend_pace(metrics.weekly_status(d, TODAY))
    b = metrics.trend_pace(metrics.weekly_status(d, TODAY + pd.Timedelta(days=1)))
    assert a > 0 and abs(a - b) / a < 0.1


def _crafted(with_fix: bool) -> bytes:
    rows = pd.DataFrame({
        "Conveyor": ["TR001", "TR002", "TR003"], "Station": ["ST100", "ST200", "ST300"],
        "Type": ["TR"] * 3, "Category": ["Sensors"] * 3,
        "Status": ["Closed", "Confirmation pending", "Open"], "Severity": ["Minor"] * 3,
        "Date Open": pd.to_datetime(["2026-09-01"] * 3),
        "Date Closed": pd.to_datetime(["2026-10-01", None, None]),
        "Responsible": ["Maintenance"] * 3, "Comments": ["a", "b", "c"],
    })
    if with_fix:
        rows["Fix finished"] = pd.to_datetime(["2026-09-20", "2026-09-25", None])
    return _xlsx(rows)


def test_fix_finished_drives_pending():
    d = read_workbook(_crafted(True), TODAY).defects
    h = metrics.weekly_status(d, TODAY).set_index("Date")
    at = lambda day: tuple(int(h.loc[pd.Timestamp(day), k]) for k in (CLOSED, PENDING, OPEN))
    assert at("2026-09-13") == (0, 0, 3)   # nothing fixed yet
    assert at("2026-09-20") == (0, 1, 2)   # first fix finished
    assert at("2026-09-27") == (0, 2, 1)   # second fix finished
    assert at("2026-10-04") == (1, 1, 1)   # first one closed
    assert at("2026-10-12") == (1, 1, 1)   # today matches the statuses
    v = d.set_index("Conveyor")["Days in validation"]
    assert v["TR001"] == 11 and v["TR002"] == 17 and pd.isna(v["TR003"])
    assert not any(i.key == "fix_column_missing" for i in read_workbook(_crafted(True), TODAY).issues)


def test_without_fix_column_pending_since_open():
    wbx = read_workbook(_crafted(False), TODAY)
    h = metrics.weekly_status(wbx.defects, TODAY).set_index("Date")
    assert int(h.loc[pd.Timestamp("2026-09-13"), PENDING]) == 1
    assert any(i.key == "fix_column_missing" for i in wbx.issues)


def test_fix_issues_flagged(wb):
    keys = {i.key for i in wb.issues}
    assert "fix_on_open" in keys and "pending_no_fix" in keys


def test_by_type(wb):
    t = metrics.by_type(wb.defects)
    assert t["Total"].sum() == len(wb.defects)
    assert list(t["Total"]) == sorted(t["Total"], reverse=True)


def test_cluster_column(wb):
    assert set(wb.defects["Cluster"].dropna()) <= {"H", "F"}


def test_breakdowns(wb):
    d = wb.defects
    nc = int(d["Status"].ne(CLOSED).sum())
    assert metrics.by_owner(d)["Remaining"].sum() == nc
    assert metrics.by_category(d)["Logged"].sum() == len(d)
    assert metrics.heat(d, top=1000).values.sum() == nc
    flow = metrics.weekly_flow(d, TODAY)
    assert flow["Found"].sum() == d["Date Open"].notna().sum()
    acts = metrics.action_list(d)
    assert acts["Status"].iloc[0] != CLOSED


def test_not_a_tracker():
    with pytest.raises(WorkbookError):
        read_workbook(_xlsx(pd.DataFrame({"a": [1]})), TODAY)


def test_sharepoint_link_parsing():
    t = parse_sharepoint_url(
        "https://contoso.sharepoint.com/:x:/r/teams/Quality/_layouts/15/Doc.aspx?"
        "sourcedoc=%7B1A2B3C4D-0000-4000-8000-123456789ABC%7D&file=Tracker_%26_log.xlsx&action=default")
    assert t.hostname == "contoso.sharepoint.com"
    assert t.site_path == "/teams/Quality"
    assert t.item_guid == "1a2b3c4d-0000-4000-8000-123456789abc"
    assert t.file_name == "Tracker_&_log.xlsx"
    d = parse_sharepoint_url("https://contoso.sharepoint.com/sites/Ops/Shared%20Documents/QA/Tracker.xlsx")
    assert d.site_path == "/sites/Ops" and d.drive_path == "QA/Tracker.xlsx" and d.file_name == "Tracker.xlsx"
