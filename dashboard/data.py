"""Read and clean the tracker workbook.

Everything here is plain pandas so it can be tested without Streamlit.
The workbook is never modified: cleaning happens on a copy, and every
correction the app makes is reported as a data-health issue so it can be
fixed at the source.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------
OPEN = "Open"
PENDING = "Confirmation pending"
CLOSED = "Closed"
STATUSES = [OPEN, PENDING, CLOSED]

CRITICAL, MAJOR, MINOR, UNASSIGNED = "Critical", "Major", "Minor", "Unassigned"
SEVERITIES = [CRITICAL, MAJOR, MINOR, UNASSIGNED]
SEVERITY_RANK = {CRITICAL: 0, MAJOR: 1, MINOR: 2, UNASSIGNED: 3}

UNASSIGNED_OWNER = "Unassigned"
STATION_LEVEL = "Station-level"

# Category spellings that mean the same thing. Keys are lower-case.
CATEGORY_ALIASES = {
    "parameters": "Parametrization",
    "parameter": "Parametrization",
    "parametrization": "Parametrization",
    "parameterization": "Parametrization",
    "parametrisation": "Parametrization",
    "sensor": "Sensors",
    "indexing pins": "Indexing",
}

DEFECT_COLUMNS = [
    "Conveyor", "Station", "Type", "Category", "Status", "Severity",
    "Date Open", "Date Closed", "Responsible", "Comments",
]
REQUIRED_DEFECT_COLUMNS = ["Conveyor", "Station", "Category", "Status"]


# ---------------------------------------------------------------------------
# Containers
# ---------------------------------------------------------------------------
@dataclass
class Issue:
    """One data-health finding."""

    key: str
    title: str
    explanation: str
    action: str  # "fix" = correct it in the Excel, "info" = handled by the app
    rows: pd.DataFrame = field(default_factory=pd.DataFrame)

    @property
    def count(self) -> int:
        return len(self.rows)


@dataclass
class Workbook:
    defects: pd.DataFrame
    campaign: pd.DataFrame | None
    issues: list[Issue]
    defect_sheet: str
    campaign_sheet: str | None
    sheet_names: list[str]


class WorkbookError(ValueError):
    """The file can be opened but does not look like the tracker."""


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _clean_text(s: pd.Series) -> pd.Series:
    """Strip text, turn blanks and 'nan' strings into missing values."""

    def one(v):
        try:
            if v is None or pd.isna(v):
                return None
        except (TypeError, ValueError):
            pass
        t = re.sub(r"\s+", " ", str(v)).strip()
        return None if t == "" or t.lower() in {"nan", "none", "nat"} else t

    return s.map(one).astype(object)


def _norm_key(v) -> str:
    return re.sub(r"\s+", " ", str(v)).strip().lower()


def _drop_unnamed(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    keep = [c for c in df.columns if not c.lower().startswith("unnamed")]
    return df[keep]


def iso_week_label(ts) -> str:
    ts = pd.Timestamp(ts)
    return f"CW{ts.isocalendar()[1]:02d}"


def _blank(v) -> bool:
    """True for None, NaN, NaT and empty strings (pandas may hand back any of them)."""
    if isinstance(v, str):
        return v.strip() == ""
    try:
        return v is None or bool(pd.isna(v))
    except (TypeError, ValueError):
        return False


def normalize_status(v) -> str | None:
    if _blank(v):
        return None
    t = _norm_key(v)
    if "closed" in t or t in {"done", "fixed", "ok"}:
        return CLOSED
    if "pend" in t or "confirm" in t or "verif" in t:
        return PENDING
    if "open" in t or t in {"in progress", "wip", "ongoing"}:
        return OPEN
    return None


def normalize_severity(v) -> str:
    if _blank(v):
        return UNASSIGNED
    t = _norm_key(v)
    for s in (CRITICAL, MAJOR, MINOR):
        if t == s.lower():
            return s
    return UNASSIGNED


def normalize_category(v) -> str | None:
    if _blank(v):
        return None
    t = _norm_key(v)
    if t in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[t]
    return str(v).strip()[:1].upper() + str(v).strip()[1:]


def owner_from_responsible(v) -> str:
    """'Maintenance -> LEAD' means it was handed over to LEAD."""
    if _blank(v):
        return UNASSIGNED_OWNER
    t = str(v)
    for arrow in ("->", "→", "=>"):
        if arrow in t:
            t = t.split(arrow)[-1]
    t = t.strip()
    if t == "" or t.upper() in {"TBD", "N/A", "NA", "-", "?"}:
        return UNASSIGNED_OWNER
    return t


def _type_from_conveyor(conveyor: str | None) -> str | None:
    if _blank(conveyor):
        return None
    m = re.match(r"^([A-Za-z]+)\d", conveyor)
    return m.group(1).upper() if m else None


# ---------------------------------------------------------------------------
# Sheet discovery
# ---------------------------------------------------------------------------
def _find_defect_sheet(xls: pd.ExcelFile) -> str:
    names = xls.sheet_names
    ordered = (["Data"] if "Data" in names else []) + [n for n in names if n != "Data"]
    for name in ordered:
        head = pd.read_excel(xls, sheet_name=name, nrows=0)
        cols = {str(c).strip() for c in head.columns}
        if all(c in cols for c in REQUIRED_DEFECT_COLUMNS):
            return name
    raise WorkbookError(
        "No sheet has the tracker columns "
        f"({', '.join(REQUIRED_DEFECT_COLUMNS)}). Sheets found: {', '.join(names)}."
    )


def _find_campaign_sheet(xls: pd.ExcelFile, skip: str) -> str | None:
    for name in xls.sheet_names:
        if name == skip:
            continue
        head = pd.read_excel(xls, sheet_name=name, nrows=0)
        cols = {str(c).strip().lower() for c in head.columns}
        if "problem description" in cols and "fix status" in cols:
            return name
    return None


# ---------------------------------------------------------------------------
# Defects (the "Data" sheet)
# ---------------------------------------------------------------------------
def clean_defects(raw: pd.DataFrame, today: pd.Timestamp) -> tuple[pd.DataFrame, list[Issue]]:
    raw = _drop_unnamed(raw)
    for c in DEFECT_COLUMNS:
        if c not in raw.columns:
            raw[c] = None

    # Excel row number (header is row 1) so people can find the line to fix.
    raw = raw.reset_index(drop=True)
    raw["Excel row"] = raw.index + 2

    # Fully empty lines are ignored.
    empty = raw[DEFECT_COLUMNS].apply(_clean_text).isna().all(axis=1)
    raw = raw.loc[~empty].copy()

    df = pd.DataFrame(index=raw.index)
    df["Excel row"] = raw["Excel row"].astype(int)
    df["Conveyor (raw)"] = _clean_text(raw["Conveyor"])
    df["Conveyor"] = df["Conveyor (raw)"].map(lambda v: v.upper() if isinstance(v, str) and re.match(r"^[A-Za-z]{1,3}\d+$", v) else v)
    df["Station"] = _clean_text(raw["Station"])
    df["Type (raw)"] = _clean_text(raw["Type"])
    df["Category (raw)"] = _clean_text(raw["Category"])
    df["Category"] = df["Category (raw)"].map(normalize_category).fillna("Uncategorized")
    df["Status (raw)"] = _clean_text(raw["Status"])
    norm_status = df["Status (raw)"].map(normalize_status)
    df["Status"] = norm_status.fillna(OPEN)
    df["Severity (raw)"] = _clean_text(raw["Severity"])
    df["Severity"] = df["Severity (raw)"].map(normalize_severity)
    df["Responsible"] = _clean_text(raw["Responsible"])
    df["Owner"] = df["Responsible"].map(owner_from_responsible)
    df["Comments"] = _clean_text(raw["Comments"])
    df["Date Open"] = pd.to_datetime(raw["Date Open"], errors="coerce").dt.normalize()
    df["Date Closed"] = pd.to_datetime(raw["Date Closed"], errors="coerce").dt.normalize()

    inferred_type = df["Conveyor"].map(_type_from_conveyor)
    df["Type"] = df["Type (raw)"].fillna(inferred_type)
    df.loc[df["Type"].isna() & df["Conveyor"].isna(), "Type"] = "Station"
    df["Type"] = df["Type"].fillna("Unknown")
    df["Asset"] = df["Conveyor"].fillna(STATION_LEVEL)

    is_closed = df["Status"].eq(CLOSED)
    df["Closed on"] = df["Date Closed"].where(is_closed)
    df["Days to close"] = (df["Closed on"] - df["Date Open"]).dt.days
    df.loc[df["Days to close"] < 0, "Days to close"] = np.nan
    df["Days open"] = np.where(~is_closed, (today.normalize() - df["Date Open"]).dt.days, np.nan)
    df["Days open"] = pd.to_numeric(df["Days open"], errors="coerce")
    df["Severity rank"] = df["Severity"].map(SEVERITY_RANK).astype(int)
    df["Week opened"] = df["Date Open"].map(lambda d: iso_week_label(d) if pd.notna(d) else None)

    issues = _defect_issues(df)
    df = df.reset_index(drop=True)
    df["id"] = df.index
    return df, issues


def _view(df: pd.DataFrame, extra: list[str] | None = None) -> pd.DataFrame:
    cols = ["Excel row", "Conveyor", "Station", "Category", "Status", "Severity",
            "Date Open", "Date Closed", "Responsible", "Comments"]
    for c in extra or []:
        if c not in cols:
            cols.insert(1, c)
    return df[cols].reset_index(drop=True)


def _defect_issues(df: pd.DataFrame) -> list[Issue]:
    out: list[Issue] = []
    closed = df["Status"].eq(CLOSED)

    def add(key, title, explanation, action, mask, extra=None):
        rows = df.loc[mask]
        if len(rows):
            out.append(Issue(key, title, explanation, action, _view(rows, extra)))

    add("severity", "Severity is blank",
        "These defects count as Unassigned in every severity chart. Set Minor, Major or Critical.",
        "fix", df["Severity (raw)"].isna())
    add("closed_no_date", "Closed without a close date",
        "They count as closed, but they can't appear in the found-vs-closed trend or in days-to-close.",
        "fix", closed & df["Date Closed"].isna())
    add("date_not_closed", "Close date on an item that isn't closed",
        "The status wins: these stay in the backlog. Clear the date or close the item.",
        "fix", ~closed & df["Date Closed"].notna())
    add("no_open_date", "Open date is blank",
        "Without it the app can't age the item or place it on the trend.",
        "fix", df["Date Open"].isna())
    add("close_before_open", "Closed before it was opened",
        "Days to close is ignored for these rows.",
        "fix", df["Date Open"].notna() & df["Date Closed"].notna() & (df["Date Closed"] < df["Date Open"]))
    add("status_unknown", "Status is blank or not recognized",
        "Only Open, Closed and Confirmation pending are understood. The app treats these rows as Open.",
        "fix", df["Status (raw)"].map(normalize_status).isna())
    add("owner_missing", "No owner",
        "Responsible is blank or TBD, so nobody is accountable for these.",
        "fix", df["Owner"].eq(UNASSIGNED_OWNER) & ~closed)
    add("category_alias", "Category spelled differently",
        "Merged automatically, e.g. Parameters is counted as Parametrization.",
        "info", df["Category (raw)"].notna() & (df["Category (raw)"] != df["Category"]), ["Category (raw)"])
    add("conveyor_case", "Conveyor name in lower case",
        "Merged automatically with the upper-case name, e.g. Tl001 is counted as TL001.",
        "info", df["Conveyor (raw)"].notna() & (df["Conveyor (raw)"] != df["Conveyor"]), ["Conveyor (raw)"])
    add("type_inferred", "Element type is blank",
        "Filled in from the conveyor name, e.g. FC001 becomes FC.",
        "info", df["Type (raw)"].isna(), ["Type"])
    add("handover", "Handed over to another owner",
        "Responsible shows a handover like 'Maintenance -> LEAD'. The app counts it for the receiving owner.",
        "info", df["Responsible"].fillna("").str.contains("->|→|=>", regex=True), ["Owner"])
    return out


# ---------------------------------------------------------------------------
# Measurement campaign (the original "Faults to fix" sheet)
# ---------------------------------------------------------------------------
def _find_col(cols, *needles) -> str | None:
    for c in cols:
        lc = c.lower()
        if all(n in lc for n in needles):
            return c
    return None


def clean_campaign(raw: pd.DataFrame, defects: pd.DataFrame) -> tuple[pd.DataFrame, list[Issue]]:
    """Link each campaign fault to its tracker row by description.

    The campaign sheet is a snapshot from the measurement round; the tracker
    (Data) carries the current status, so linked faults take their status
    from there.
    """
    raw = _drop_unnamed(raw)
    cols = list(raw.columns)
    # The sheet carries side tables to the right (Pareto counts); keep the
    # fault list itself, which ends where the description column ends.
    desc_col = _find_col(cols, "problem", "description")
    raw = raw.reset_index(drop=True)
    raw["Excel row"] = raw.index + 2
    raw = raw[_clean_text(raw[desc_col]).notna()].copy()

    def col(*needles):
        c = _find_col(cols, *needles)
        return _clean_text(raw[c]) if c else pd.Series([None] * len(raw), index=raw.index, dtype=object)

    out = pd.DataFrame(index=raw.index)
    out["Excel row"] = raw["Excel row"].astype(int)
    out["Description"] = _clean_text(raw[desc_col])
    out["Conveyor"] = col("conveyor").map(lambda v: v.upper() if isinstance(v, str) and re.match(r"^[A-Za-z]{1,3}\d+$", v) else v)
    st_col = next((c for c in cols if c.strip().lower() == "station"), None)
    out["Station"] = _clean_text(raw[st_col]) if st_col else None
    out["PLC"] = col("plc").fillna("No PLC")
    out["Cluster"] = col("cluster").fillna("Unknown")
    fault_col = next((c for c in cols if c.strip().lower() == "fault"), None)
    out["Fault"] = (_clean_text(raw[fault_col]) if fault_col else pd.Series(None, index=raw.index)).map(
        lambda v: "Uncategorized" if _blank(v) else normalize_category(v))
    out["Campaign status"] = col("fix", "status").fillna("Open")
    m_col = _find_col(cols, "measur")
    out["Measurement (m/s²)"] = pd.to_numeric(raw[m_col], errors="coerce") if m_col else np.nan

    key = defects["Comments"].map(lambda v: None if _blank(v) else _norm_key(v))
    lookup = (defects.assign(_k=key).dropna(subset=["_k"])
              .drop_duplicates("_k").set_index("_k"))
    k = out["Description"].map(_norm_key)
    found = k.isin(lookup.index)
    out["Linked"] = found
    out["Tracker row"] = k.map(lookup["Excel row"]).astype("Int64")
    out["Status"] = k.map(lookup["Status"])
    out["Severity"] = k.map(lookup["Severity"])
    out["Owner"] = k.map(lookup["Owner"])
    out["Tracker id"] = k.map(lookup["id"]).astype("Int64")
    out["Remeasure requested"] = out["Campaign status"].str.lower().str.contains("remeasure")
    out["Status"] = out["Status"].fillna(out["Campaign status"].map(normalize_status)).fillna(OPEN)
    out = out.reset_index(drop=True)

    issues = []
    missing = out.loc[~out["Linked"], ["Excel row", "Description", "Conveyor", "Station", "Campaign status"]]
    if len(missing):
        issues.append(Issue(
            "campaign_unlinked", "Campaign fault not found in the tracker",
            "These faults from the measurement campaign have no row in Data with the same description, "
            "so their status comes from the campaign sheet and may be out of date. Excel rows refer to the campaign sheet.",
            "fix", missing.reset_index(drop=True)))
    return out, issues


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def read_workbook(content: bytes, today: pd.Timestamp | None = None) -> Workbook:
    today = (today or pd.Timestamp.today()).normalize()
    try:
        xls = pd.ExcelFile(io.BytesIO(content))
    except Exception as exc:  # noqa: BLE001 - surface any reader error as a clear message
        raise WorkbookError(f"The file couldn't be opened as an Excel workbook ({exc}).") from exc

    defect_sheet = _find_defect_sheet(xls)
    defects, issues = clean_defects(pd.read_excel(xls, sheet_name=defect_sheet), today)
    if defects.empty:
        raise WorkbookError(f"The sheet '{defect_sheet}' has no defect rows.")

    campaign_sheet = _find_campaign_sheet(xls, skip=defect_sheet)
    campaign = None
    if campaign_sheet:
        campaign, c_issues = clean_campaign(pd.read_excel(xls, sheet_name=campaign_sheet), defects)
        issues += c_issues

    return Workbook(defects, campaign, issues, defect_sheet, campaign_sheet, list(xls.sheet_names))
