"""Design tokens, page CSS and small HTML building blocks.

Visual idea: a plant-floor dashboard. Concrete-grey page, graphite ink, a
DIN-like signage face (Barlow), and colors taken from industrial safety
signage: severity follows the caution / warning / danger ladder
(yellow, orange, red); status uses red / blue / green. The one loud element
is the line map: a dark conveyor band where every open defect sits on its
station.
"""
from __future__ import annotations

import html

from .data import CLOSED, CRITICAL, MAJOR, MINOR, OPEN, PENDING, UNASSIGNED

# --- surfaces & ink ---------------------------------------------------------
PAGE = "#FFFFFF"  # pure white: charts and panels paste cleanly into slides
PANEL = "#E8E9E5"
INK = "#1B2024"
INK_2 = "#4D555C"
MUTED = "#80878D"
HAIR = "#D9DAD5"
AXIS = "#BFC2BC"

# --- the line map band ------------------------------------------------------
BAND = "#FFFFFF"
BAND_INK = "#4D555C"
BAND_MUTED = "#A3A8AC"
RAIL = "#E4E6E2"
ROLLER = "#C9CDC8"

# --- status (state) ---------------------------------------------------------
# Red / amber / green: the format management already reads in the weekly slides.
STATUS_COLORS = {OPEN: "#B03A2E", PENDING: "#D9A406", CLOSED: "#2E8B57"}
STATUS_TEXT = {OPEN: "#B03A2E", PENDING: "#946604", CLOSED: "#1E7E45"}  # darker steps for numbers on the page
STATUS_LABELS = {OPEN: "Open", PENDING: "Confirmation pending", CLOSED: "Closed"}

# --- severity (ordered: caution → warning → danger) -------------------------
SEVERITY_LIGHT = {CRITICAL: "#962028", MAJOR: "#CC5418", MINOR: "#D6A934", UNASSIGNED: "#A9AEB2"}

# --- other series -----------------------------------------------------------
FOUND = "#4D555C"
SINGLE = "#3E5C76"  # one-series bars (steel blue)
HEAT = ["#FBEEE7", "#F1D9CB", "#E5AE92", "#D27D5A", "#AE4F31", "#7A2A17"]

FONT = "Barlow, 'Barlow', 'Segoe UI', system-ui, sans-serif"
FONT_COND = "'Barlow Condensed', Barlow, 'Arial Narrow', system-ui, sans-serif"


def _font_faces() -> str:
    faces = [
        ("Barlow", 400, "Barlow-Regular"), ("Barlow", 500, "Barlow-Medium"),
        ("Barlow", 600, "Barlow-SemiBold"),
        ("Barlow Condensed", 500, "BarlowCondensed-Medium"),
        ("Barlow Condensed", 600, "BarlowCondensed-SemiBold"),
    ]
    return "\n".join(
        f"@font-face{{font-family:'{fam}';font-weight:{w};font-style:normal;font-display:swap;"
        f"src:url('app/static/fonts/{f}.woff2') format('woff2');}}"
        for fam, w, f in faces
    )


CSS = f"""
<style>
{_font_faces()}

:root {{
  --page:{PAGE}; --panel:{PANEL}; --ink:{INK}; --ink-2:{INK_2}; --muted:{MUTED};
  --hair:{HAIR}; --band:{BAND}; --band-ink:{BAND_INK}; --band-muted:{BAND_MUTED};
  --open:{STATUS_COLORS[OPEN]}; --pending:{STATUS_COLORS[PENDING]}; --closed:{STATUS_COLORS[CLOSED]};
}}

.block-container {{ padding-top: 3.4rem; padding-bottom: 4rem; max-width: 1480px; }}
h1, h2, h3, h4 {{ font-family: {FONT_COND} !important; letter-spacing: 0.005em; color: var(--ink); }}

/* Tabs read like the sections of a shift board */
.stTabs [data-baseweb="tab-list"] {{ gap: 1.75rem; border-bottom: 1px solid var(--hair); }}
.stTabs [data-baseweb="tab"] {{ padding: 0.35rem 0 0.6rem; height: auto; }}
.stTabs [data-baseweb="tab"] p {{ font-family: {FONT_COND}; font-size: 1.15rem; font-weight: 500; color: var(--ink-2); }}
.stTabs [aria-selected="true"] p {{ color: var(--ink); font-weight: 600; }}
.stTabs [data-baseweb="tab-highlight"] {{ background-color: var(--ink); height: 3px; }}
.stTabs [data-baseweb="tab-panel"] {{ padding-top: 1.6rem; }}

/* Masthead */
.mh {{ display:flex; justify-content:space-between; align-items:flex-end; gap:2rem; flex-wrap:wrap;
       padding-bottom: 1rem; }}
.mh-title {{ font-family:{FONT_COND}; font-weight:600; font-size:2.35rem; line-height:1; color:var(--ink); margin:0; }}
.mh-sub {{ color:var(--ink-2); font-size:1rem; margin-top:0.35rem; }}
.mh-src {{ display:grid; grid-template-columns:auto auto auto auto; column-gap:0.7rem; row-gap:0.15rem;
           font-size:0.875rem; color:var(--ink-2); text-align:left; margin:0; }}
.mh-src dt {{ color:var(--muted); }}
.mh-src dd {{ margin:0 1.2rem 0 0; color:var(--ink); font-weight:500; white-space:nowrap; }}
@media (max-width: 700px) {{ .mh-src {{ grid-template-columns:auto auto; }} }}

/* Overview lead */
.lead-head {{ font-family:{FONT_COND}; font-weight:600; font-size:clamp(2rem, 3.6vw, 3.1rem);
              line-height:1.04; color:var(--ink); max-width:24ch; margin:0 0 0.6rem; text-wrap:balance; }}
.lead-sub {{ font-size:1.15rem; line-height:1.5; color:var(--ink-2); max-width:68ch; margin:0; }}

.sw {{ display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:0.4rem; vertical-align:baseline; }}

.facts {{ display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); margin:1.8rem 0 0.4rem;
          border-top:1px solid var(--hair); }}
.facts > div {{ padding:0.9rem 1.2rem 0.2rem 0; }}
.facts > div + div {{ padding-left:1.2rem; border-left:1px solid var(--hair); }}
.facts .v {{ font-family:{FONT_COND}; font-weight:600; font-size:2rem; line-height:1.1; color:var(--ink); }}
.facts .v small {{ font-size:1rem; font-weight:500; color:var(--ink-2); margin-left:0.25rem; }}
.facts .l {{ font-size:0.92rem; color:var(--ink-2); line-height:1.35; margin-top:0.2rem; }}
@media (max-width: 900px) {{
  .facts {{ grid-template-columns:repeat(2, minmax(0,1fr)); }}
  .facts > div:nth-child(3) {{ border-left:none; padding-left:0; }}
}}

/* Overview header: title + the three status counts management reads first */
.ov-title {{ font-family:{FONT_COND}; font-weight:600; font-size:clamp(2rem, 3.4vw, 2.9rem); line-height:1;
             color:var(--ink); margin:0 0 1.1rem; }}
.kpis {{ display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:0 2rem; margin:0 0 1.6rem; }}
.kpis > div {{ border-top:4px solid var(--hair); padding-top:0.55rem; }}
.kpis .l {{ font-size:0.95rem; color:var(--ink-2); }}
.kpis .v {{ font-family:{FONT_COND}; font-weight:600; font-size:clamp(2.6rem, 4.6vw, 3.8rem); line-height:1.05; }}
.kpis .s {{ font-size:0.88rem; color:var(--muted); }}

/* Screenshot panel: counts + trend on pure white for slides */
.st-key-snapshot {{ background:#FFFFFF; border-radius:6px; padding:1.3rem 1.5rem 0.6rem; }}
.st-key-snapshot .kpis {{ margin-bottom:1.3rem; }}
.snap-title {{ font-family:{FONT_COND}; font-weight:600; font-size:1.35rem; color:var(--ink); margin:0; }}

/* Section headings */
.sec {{ margin: 0.2rem 0 0.4rem; }}
.sec h3 {{ font-family:{FONT_COND}; font-weight:600; font-size:1.45rem; line-height:1.15; margin:0; padding:0; color:var(--ink); }}
.sec p {{ color:var(--ink-2); font-size:0.95rem; margin:0.25rem 0 0; max-width:75ch; line-height:1.45; }}
.foot {{ color:var(--muted); font-size:0.85rem; margin-top:-0.4rem; line-height:1.4; }}

/* The line map band */
.st-key-linemap {{ background:#FFFFFF; }}
.lm-legend {{ display:flex; gap:1.3rem; flex-wrap:wrap; font-size:0.88rem; color:var(--band-ink); margin-top:0.7rem; }}
.lm-legend i {{ display:inline-block; width:11px; height:11px; border-radius:2px; margin-right:0.4rem; vertical-align:-1px; }}

/* Data-health list */
.dh-row {{ display:flex; align-items:baseline; gap:0.8rem; }}
.tag {{ display:inline-block; font-size:0.78rem; font-weight:600; padding:0.08rem 0.45rem; border-radius:3px; }}
.tag.fix {{ background:#F6DCD8; color:#8A241C; }}
.tag.info {{ background:#DDE3EA; color:#2C3E52; }}

/* Empty state */
.empty {{ max-width:62ch; padding:2.5rem 0 1rem; }}
.empty h2 {{ font-size:2.2rem; margin:0 0 0.6rem; }}
.empty p, .empty li {{ color:var(--ink-2); font-size:1.05rem; line-height:1.55; }}

@media (prefers-reduced-motion: reduce) {{ * {{ transition:none !important; animation:none !important; }} }}
</style>
"""


def esc(v) -> str:
    return html.escape(str(v))


def masthead(source_label: str, file_name: str, data_through: str, loaded_at: str) -> str:
    return f"""
<div class="mh">
  <div>
    <p class="mh-title">Conveyor defect tracker</p>
    <div class="mh-sub">Conveyor measurement and fix tracking</div>
  </div>
  <dl class="mh-src">
    <dt>Source</dt><dd>{esc(source_label)}</dd>
    <dt>File</dt><dd>{esc(file_name)}</dd>
    <dt>Latest entry</dt><dd>{esc(data_through)}</dd>
    <dt>Loaded</dt><dd>{esc(loaded_at)}</dd>
  </dl>
</div>"""


def section(title: str, note: str | None = None) -> str:
    n = f"<p>{esc(note)}</p>" if note else ""
    return f'<div class="sec"><h3>{esc(title)}</h3>{n}</div>'


def lead(head: str, sub: str) -> str:
    return f'<p class="lead-head">{esc(head)}</p><p class="lead-sub">{esc(sub)}</p>'


def overview_title(text: str) -> str:
    return f'<p class="ov-title">{esc(text)}</p>'


def kpis(open_: int, pending: int, closed: int) -> str:
    total = max(open_ + pending + closed, 1)
    cells = [(OPEN, "Open defects", open_), (PENDING, "Pending confirmation", pending), (CLOSED, "Closed defects", closed)]
    html_cells = "".join(
        f'<div style="border-top-color:{STATUS_COLORS[k]}"><div class="l">{label}</div>'
        f'<div class="v" style="color:{STATUS_TEXT[k]}">{n}</div><div class="s">{n / total:.0%} of {total}</div></div>'
        for k, label, n in cells)
    return f'<div class="kpis">{html_cells}</div>'


def facts(items: list[tuple[str, str, str]]) -> str:
    """items: (value, unit, label)."""
    cells = "".join(
        f'<div><div class="v">{esc(v)}{f"<small>{esc(u)}</small>" if u else ""}</div><div class="l">{esc(l)}</div></div>'
        for v, u, l in items
    )
    return f'<div class="facts">{cells}</div>'


def linemap_legend() -> str:
    items = "".join(
        f'<span><i style="background:{SEVERITY_LIGHT[s]}"></i>{s}</span>' for s in (CRITICAL, MAJOR, MINOR, UNASSIGNED)
    )
    items += f'<span><i style="background:transparent;box-shadow:inset 0 0 0 2px {INK_2}"></i>Outlined: confirmation pending</span>'
    return f'<div class="lm-legend">{items}</div>'


def tag(action: str) -> str:
    return '<span class="tag fix">Fix in Excel</span>' if action == "fix" else '<span class="tag info">Handled by the app</span>'
