# Conveyor defect tracker

A Streamlit dashboard for the *Conveyors measurement & fix tracking* workbook.
It reads the **Data** sheet (one row per defect) and, when present, the original
measurement-campaign sheet (*Faults to fix*), and turns them into:

| Tab | For | What it shows |
|---|---|---|
| **Overview** | Management | A one-line status, closed/awaiting/open progress, the **line map** (every open defect on its station, in line order), found vs closed with a projection, what's left by category and owner, how long closing takes |
| **Follow-up** | The weekly review | Filters, owner board, aging, found/closed per week, hot spots (conveyor × category), the action list with downloads |
| **Measurement campaign** | Cluster-movement work | Campaign faults linked to their current tracker status, by PLC, fault type and cluster, measured peak acceleration against the limit (0.16 g by default), remeasure list |
| **Data health** | Whoever maintains the Excel | Every gap or inconsistency with the Excel row number to fix, plus what the app corrects on its own |
| **All records** | Everyone | Search and download |

The Excel file is never changed. Cleaning rules (e.g. *Parameters* counts as
*Parametrization*, blank severity counts as *Unassigned*, `Maintenance -> LEAD`
counts for LEAD) are listed in the Data health tab.

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Where the data comes from

The app tries these in order:

1. **A file uploaded in the sidebar**: for that session only.
2. **SharePoint**: reads the live workbook through Microsoft Graph when the
   `[sharepoint]` secrets are set. Cached for 5 minutes; *Reload data* forces a fresh read.
3. **A synced folder**: a local path (e.g. the SharePoint library synced with
   OneDrive), from `[local] path` in the secrets or the `TROLLEY_XLSX_PATH`
   environment variable. It reloads automatically when the file changes.

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in one
option. On Streamlit Community Cloud, paste the same content into
*App settings → Secrets*. **Never commit secrets or the workbook**: this repository
is public, and `.gitignore` already blocks `secrets.toml` and Excel files.

### What to ask IT for (SharePoint option)

> Please create an Entra ID (Azure AD) app registration for a read-only dashboard
> that downloads one Excel file from the SharePoint site `<site URL>`.
> Application permission: **Sites.Selected** for Microsoft Graph, granted *read*
> on that site only (or Sites.Read.All if Sites.Selected isn't used).
> I need the **tenant ID**, **client ID** and a **client secret**.

Then put those three values and the file's link (the address you see when the file
is open in Excel online) in the secrets. If the hosting platform can't reach
the company tenant, run the app on a company laptop and use the synced-folder
option instead.

## Development

```bash
pip install pytest
python -m pytest -q                   # unit tests + headless app test
python tests/make_sample.py demo.xlsx # synthetic workbook (no plant data)
TROLLEY_XLSX_PATH=demo.xlsx streamlit run app.py
```

GitHub Actions runs the tests on every push. On branches other than `main` it
also renders every tab with the synthetic workbook and pushes the screenshots to
a `ci-screenshots` branch (safe to delete at any time).

Layout:

```
app.py                 page layout and tabs
dashboard/data.py      reading + cleaning the workbook, data-health checks
dashboard/metrics.py   KPIs, trend, breakdowns (plain pandas)
dashboard/charts.py    Plotly figures
dashboard/linemap.py   the line map
dashboard/theme.py     colors, type, CSS and small HTML blocks
dashboard/source.py    SharePoint / local file loading
static/fonts/          Barlow and Barlow Condensed (SIL Open Font License)
```
