"""The dashboard stylesheet.

All of the dashboard's CSS lives here so ``app.py`` stays focused on layout and
data. The design is a retro pixel/terminal aesthetic built on the VT323 face,
with a single set of custom properties driving colour, spacing and type so the
panels stay visually consistent with one another.
"""
from __future__ import annotations

DASHBOARD_CSS = """
@import url('https://fonts.googleapis.com/css2?family=VT323&display=swap');

/* ---------------------------------------------------------------------------
   Design tokens. Every panel derives its colour, spacing, border and type
   size from these, which is what keeps the UI internally consistent.
   --------------------------------------------------------------------------- */
:root {
    --bg: #1a1a2e;              /* app background — deep navy */
    --panel: #16213e;           /* card / panel surface */
    --panel-alt: #0f3460;       /* raised surface for emphasis */
    --panel-sunk: #12162b;      /* recessed surface */

    --text: #e4e9e4;            /* primary text */
    --muted: #8b9a90;           /* secondary text */
    --faint: #5c6b62;           /* tertiary text */

    --green: #00ff41;           /* accent: headings, active state */
    --orange: #ed7d32;          /* accent: key figures */
    --red: #ff4444;             /* accent: warnings */
    --cyan: #00e5ff;            /* accent: festivals / events */

    --border: #2a4a5e;
    --border-soft: rgba(255, 255, 255, 0.08);

    /* Spacing scale */
    --s1: 4px;
    --s2: 8px;
    --s3: 12px;
    --s4: 18px;
    --s5: 26px;
    --s6: 36px;

    /* Type scale */
    --t-xs: 0.9rem;
    --t-sm: 1.0rem;
    --t-md: 1.3rem;
    --t-lg: 1.6rem;
    --t-xl: 1.9rem;
    --t-2xl: 2.8rem;

    --radius: 4px;
}

/* ---------------------------------------------------------------------------
   Base
   --------------------------------------------------------------------------- */
html, body, [class*="css"] {
    font-family: "VT323", "Courier New", monospace !important;
    font-size: 20px;
}

/* Streamlit's theme sets font-family on its own heading/control classes, which
   outranks a plain html/body rule. Text-bearing elements are therefore listed
   explicitly so the pixel face actually applies. */
.stApp, .stApp p, .stApp div, .stApp span, .stApp li, .stApp a,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
.stApp button, .stApp label, .stApp summary, .stApp td, .stApp th {
    font-family: "VT323", "Courier New", monospace !important;
}

/* ...but Streamlit's icons *are* a font, so they must keep theirs. */
.stApp [class*="material-symbols"],
.stApp [class*="material-icons"],
.stApp [data-testid$="Icon"] {
    font-family: "Material Symbols Rounded" !important;
}

.stApp { background: var(--bg); color: var(--text); }

.block-container {
    max-width: 1440px;
    padding-top: var(--s5);
    padding-bottom: var(--s6);
}

/* Streamlit's default heavy heading margins fight the retro layout. */
h1, h2, h3, h4 { font-weight: normal !important; }

/* Respect users who ask for reduced motion. */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { transition: none !important; animation: none !important; }
}

/* ---------------------------------------------------------------------------
   Header
   --------------------------------------------------------------------------- */
.tci-header {
    padding-bottom: var(--s2);
    margin-bottom: var(--s4);
    border-bottom: 3px dashed var(--text);
}
.tci-header h1 {
    color: var(--green);
    font-size: var(--t-2xl);
    margin: 0;
    line-height: 1.1;
    text-shadow: 0 0 10px rgba(0, 255, 65, 0.3);
}
.tci-header .tagline {
    color: var(--muted);
    font-size: var(--t-sm);
    margin-top: var(--s1);
}

/* Section headings carry a terminal-style "> " prompt. */
.section {
    color: var(--text);
    font-size: var(--t-lg);
    margin: var(--s4) 0 var(--s3);
}
.section::before { content: "> "; color: var(--green); }

/* ---------------------------------------------------------------------------
   Latest-data panel
   --------------------------------------------------------------------------- */
.latest-box {
    border: 2px dashed var(--text);
    border-radius: var(--radius);
    background: rgba(22, 33, 62, 0.5);
    padding: var(--s4);
    margin-bottom: var(--s4);
}
.latest-status { color: var(--green); font-size: var(--t-sm); }
.latest-status::before { content: "\\25A0  "; }
.latest-status.is-fallback { color: var(--orange); }

.latest-big {
    font-size: var(--t-xl);
    margin: var(--s1) 0;
    color: var(--text);
    line-height: 1.15;
}
.latest-stats {
    display: flex;
    flex-wrap: wrap;
    gap: var(--s2) var(--s5);
    font-size: var(--t-xs);
    color: var(--muted);
    margin-top: var(--s3);
    padding-top: var(--s2);
    border-top: 1px solid var(--border-soft);
}
.latest-stats span { min-width: 165px; }
.latest-stats .wide { width: 100%; }

/* ---------------------------------------------------------------------------
   Crowd scale: swatch legend + gradient meter
   --------------------------------------------------------------------------- */
.legend-row { display: flex; gap: var(--s1); margin-bottom: var(--s2); }
.legend-swatch {
    width: 38px;
    height: 38px;
    border: 2px solid rgba(255, 255, 255, 0.18);
}
/* Swatches at or below the current level stay lit; the rest are dimmed, so
   the strip doubles as a level indicator. */
.legend-swatch.dim { opacity: 0.22; }
.legend-swatch.active {
    border-color: var(--text);
    box-shadow: 0 0 8px rgba(255, 255, 255, 0.25);
}
.legend-caption { font-size: var(--t-md); line-height: 1.2; }
.legend-sub { color: var(--faint); font-size: var(--t-xs); }

.meter { position: relative; margin: var(--s2) 0 var(--s4); }
.meter-bar {
    height: 16px;
    border: 1px solid var(--border-soft);
    border-radius: 2px;
}
/* Triangular marker that slides to the value's position on the scale. */
.meter-marker {
    position: absolute;
    top: 15px;
    width: 0;
    height: 0;
    border-left: 7px solid transparent;
    border-right: 7px solid transparent;
    border-bottom: 9px solid var(--text);
    transform: translateX(-7px);
}
.meter-ends {
    display: flex;
    justify-content: space-between;
    color: var(--faint);
    font-size: var(--t-xs);
    margin-top: var(--s3);
}

/* ---------------------------------------------------------------------------
   Calendar
   --------------------------------------------------------------------------- */
.cal-month {
    color: var(--green);
    font-size: var(--t-md);
    line-height: 2;
    white-space: nowrap;
    text-shadow: 0 0 8px rgba(0, 255, 65, 0.2);
}
.cal-weekdays {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 2px;
    margin-bottom: 2px;
}
.cal-wk {
    color: var(--text);
    font-size: var(--t-xs);
    text-align: center;
    background: var(--panel);
    border: 1px solid var(--border);
    padding: var(--s1) 0;
}
.cal-cell {
    height: 72px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: var(--t-md);
    font-weight: bold;
    border: 1px solid var(--border-soft);
    text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.55);
    position: relative;
}
/* Days outside the displayed month, and days with neither actual nor
   forecast data, are visibly inert. */
.cal-cell.empty { background: transparent; border-color: rgba(255,255,255,0.04); }
.cal-cell.muted { color: rgba(255, 255, 255, 0.35); }
/* A small tick marks days backed by observed data rather than a forecast. */
.cal-cell.actual::after {
    content: "";
    position: absolute;
    left: 4px;
    bottom: 4px;
    width: 5px;
    height: 5px;
    background: rgba(255, 255, 255, 0.75);
}
.cal-cell.today { outline: 1px dashed rgba(255, 255, 255, 0.55); outline-offset: -4px; }
.cal-selected {
    border: 3px solid var(--green) !important;
    box-shadow: 0 0 12px rgba(0, 255, 65, 0.35);
    z-index: 5;
}

/* The keyed week containers must not add vertical rhythm of their own —
   the tiles are meant to sit in a tight grid. */
[class*="st-key-calweek-"] {
    gap: 0 !important;
    margin-bottom: 2px !important;
}

/* Each day is a coloured tile with a transparent Streamlit button pulled up
   over it to capture the click. Scoped to the keyed calendar week containers so
   it cannot leak onto the month navigation or download buttons. */
[class*="st-key-calweek-"] [data-testid="stButton"] button {
    margin-top: -72px !important;
    height: 72px !important;
    min-height: 72px !important;
    background: transparent !important;
    border: 1px solid transparent !important;
    color: transparent !important;
    box-shadow: none !important;
    position: relative;
    z-index: 10;
}
[class*="st-key-calweek-"] [data-testid="stButton"] button:hover {
    background: rgba(255, 255, 255, 0.16) !important;
    border-color: rgba(0, 255, 65, 0.45) !important;
}
[class*="st-key-calweek-"] [data-testid="stButton"] button:focus-visible {
    border-color: var(--green) !important;
    outline: 2px solid var(--green) !important;
    outline-offset: -2px;
}

.cal-legend {
    display: flex;
    flex-wrap: wrap;
    gap: var(--s2) var(--s4);
    color: var(--faint);
    font-size: var(--t-xs);
    margin-top: var(--s3);
}

/* ---------------------------------------------------------------------------
   Selected-date detail panel
   --------------------------------------------------------------------------- */
.panel {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: var(--s4);
    margin-bottom: var(--s3);
}
.panel-title { font-size: var(--t-md); color: var(--text); margin-bottom: var(--s3); }

.detail-head { display: flex; gap: var(--s4); align-items: flex-start; }
.date-box {
    border: 1px solid var(--border);
    background: var(--panel-alt);
    padding: var(--s2) var(--s3);
    text-align: center;
    min-width: 112px;
}
.date-box .day-name { font-size: var(--t-xs); color: var(--muted); }
.date-box .day-num {
    font-size: var(--t-2xl);
    color: var(--green);
    line-height: 1;
    font-weight: bold;
}
.date-box .month-yr { font-size: var(--t-xs); color: var(--muted); }

.level-headline {
    font-size: var(--t-lg);
    font-weight: bold;
    line-height: 1.1;
    margin-top: 2px;
}

.info-label { font-size: var(--t-xs); color: var(--muted); margin-top: var(--s3); }
.info-value { font-size: var(--t-xl); color: var(--orange); line-height: 1.15; }
.info-note { font-size: var(--t-xs); color: var(--faint); margin-top: 2px; }

/* Provenance tag: is this figure observed or predicted? */
.origin-tag {
    display: inline-block;
    font-size: var(--t-xs);
    padding: 1px var(--s2);
    border: 1px solid currentColor;
    border-radius: 2px;
    letter-spacing: 0.5px;
}
.origin-tag.actual { color: var(--green); }
.origin-tag.forecast { color: var(--orange); }

/* ---------------------------------------------------------------------------
   Context chips (what is driving a given day's forecast)
   --------------------------------------------------------------------------- */
.chip-row { display: flex; flex-wrap: wrap; gap: var(--s2); margin-top: var(--s2); }
.chip {
    font-size: var(--t-xs);
    color: var(--text);
    background: var(--panel-sunk);
    border: 1px solid var(--border);
    border-radius: 2px;
    padding: 2px var(--s2);
}
.chip.hot { border-color: var(--orange); color: var(--orange); }
.chip.cool { border-color: var(--green); color: var(--green); }
.chip.event { border-color: var(--cyan); color: var(--cyan); }

/* ---------------------------------------------------------------------------
   Festivals panel
   --------------------------------------------------------------------------- */
.fest-name { color: var(--cyan); font-size: var(--t-md); line-height: 1.25; margin: var(--s1) 0; }
.fest-name.none { color: var(--faint); }
.fest-meta { color: var(--faint); font-size: var(--t-xs); }
.fest-date { color: var(--muted); font-size: var(--t-xs); margin-top: var(--s2); }

/* ---------------------------------------------------------------------------
   Quiet-days ranking
   --------------------------------------------------------------------------- */
.rank-row {
    display: flex;
    align-items: center;
    gap: var(--s3);
    padding: var(--s2) 0;
    border-bottom: 1px solid var(--border-soft);
    font-size: var(--t-xs);
}
.rank-row:last-child { border-bottom: none; }
.rank-chip {
    width: 14px;
    height: 14px;
    flex: 0 0 14px;
    border: 1px solid rgba(255,255,255,0.2);
}
.rank-day { color: var(--text); min-width: 148px; }
.rank-val { color: var(--muted); margin-left: auto; }

/* ---------------------------------------------------------------------------
   Deity backdrop motif
   --------------------------------------------------------------------------- */
.deity-wrap {
    display: flex;
    justify-content: center;
    padding: var(--s2) 0 var(--s4);
    opacity: 0.9;
}
.deity-wrap svg { max-width: 300px; }

/* ---------------------------------------------------------------------------
   Disclaimers
   --------------------------------------------------------------------------- */
.disclaimer-box {
    border: 1px solid var(--border);
    background: var(--panel);
    border-radius: var(--radius);
    padding: var(--s4);
    margin-top: var(--s3);
}
.disclaimer-box h3 {
    color: var(--red);
    font-size: var(--t-md);
    margin: 0 0 var(--s2);
    text-transform: uppercase;
}
.disclaimer-box p { font-size: var(--t-xs); color: var(--muted); line-height: 1.35; margin-bottom: var(--s2); }

.forecast-disclaimer {
    border-top: 3px dashed var(--border);
    padding-top: var(--s4);
    margin-top: var(--s5);
}
.forecast-disclaimer h3 { color: var(--red); font-size: var(--t-md); margin: 0 0 var(--s2); }
.forecast-disclaimer p { font-size: var(--t-xs); color: var(--muted); line-height: 1.45; margin-bottom: var(--s3); }

/* ---------------------------------------------------------------------------
   Streamlit control overrides
   --------------------------------------------------------------------------- */
[data-testid="stButton"] button {
    font-family: "VT323", monospace !important;
    border-radius: 2px !important;
    background: var(--panel) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
}
[data-testid="stButton"] button:hover {
    border-color: var(--green) !important;
    color: var(--green) !important;
}
[data-testid="stDownloadButton"] button {
    font-family: "VT323", monospace !important;
    background: var(--panel) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 2px !important;
}
[data-testid="stDownloadButton"] button:hover { border-color: var(--green) !important; color: var(--green) !important; }

/* Expander ("Model & data details") */
[data-testid="stExpander"] {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    background: var(--panel) !important;
}
[data-testid="stExpander"] summary { font-family: "VT323", monospace !important; color: var(--text) !important; }
[data-testid="stExpander"] p, [data-testid="stExpander"] li { font-size: var(--t-xs); color: var(--muted); }

/* Tabs */
[data-baseweb="tab-list"] { background: transparent !important; gap: var(--s2); }
[data-baseweb="tab"] {
    font-family: "VT323", monospace !important;
    font-size: var(--t-sm) !important;
    color: var(--muted) !important;
}
[data-baseweb="tab"][aria-selected="true"] { color: var(--green) !important; }

/* Hide Streamlit chrome that breaks the terminal illusion. */
#MainMenu, footer, header [data-testid="stToolbar"] { visibility: hidden; }

/* ---------------------------------------------------------------------------
   Narrow screens: shrink the tall calendar tiles so a month still fits.
   The click-overlay offset must track the tile height exactly.
   --------------------------------------------------------------------------- */
@media (max-width: 900px) {
    html, body, [class*="css"] { font-size: 18px; }
    .cal-cell { height: 54px; font-size: var(--t-sm); }
    [class*="st-key-calweek-"] [data-testid="stButton"] button {
        margin-top: -54px !important;
        height: 54px !important;
        min-height: 54px !important;
    }
    .deity-wrap svg { max-width: 200px; }
}

/* Below its stacking breakpoint Streamlit turns every row of st.columns into a
   vertical stack. For a calendar that is fatal — the seven day tiles become
   seven full-width bars — so the week rows are pinned back to a 7-across grid.
   Scoped to the keyed calendar week containers so the page's own column rows
   still stack as intended. */
@media (max-width: 640px) {
    [class*="st-key-calweek-"] [data-testid="stHorizontalBlock"] {
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 2px !important;
    }
    [class*="st-key-calweek-"] [data-testid="stHorizontalBlock"] > div,
    [class*="st-key-calweek-"] [data-testid="stHorizontalBlock"] [data-testid="stColumn"] {
        width: 14.28% !important;
        flex: 1 1 0 !important;
        min-width: 0 !important;
        /* Streamlit's own column gutters would eat most of a 53px tile. */
        padding: 0 !important;
    }
    [class*="st-key-calweek-"] [data-testid="stHorizontalBlock"] [data-testid="stVerticalBlock"] {
        gap: 0 !important;
        min-width: 0 !important;
    }
    /* Tiles get small at phone widths, so drop the tick and shrink the type
       rather than letting the digits overflow. */
    .cal-cell { height: 42px; font-size: var(--t-xs); }
    .cal-cell.actual::after { display: none; }
    [class*="st-key-calweek-"] [data-testid="stButton"] button {
        margin-top: -42px !important;
        height: 42px !important;
        min-height: 42px !important;
        padding: 0 !important;
    }
    .cal-wk { font-size: 0.7rem; }
}
"""

# Retained under its previous name so any external import keeps working.
DARK_COMMAND_CENTER_CSS = DASHBOARD_CSS
