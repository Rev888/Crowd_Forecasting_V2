"""The dashboard stylesheet.

All CSS lives here so ``app.py`` stays focused on layout and data.

The palette, type scale and spacing below are taken from the reference design:
a near-black ground, dark-grey panels with thin grey borders, dashed light-grey
rules, bright green for headings and **amber/orange as the key accent** for every
figure the reader is meant to take away. Sizes are in px rather than rem so they
land exactly where the design puts them regardless of the host font size.
"""
from __future__ import annotations

DASHBOARD_CSS = """
@import url('https://fonts.googleapis.com/css2?family=VT323&display=swap');

/* ---------------------------------------------------------------------------
   Design tokens — the single source of truth for the whole dashboard.
   --------------------------------------------------------------------------- */
:root {
    /* Surfaces */
    --bg: #0f0f10;              /* page ground, near-black */
    --panel: #1a1b1d;           /* Selected Date / festivals / disclaimer */
    --panel-alt: #232426;       /* date box inside the detail panel */
    --panel-sunk: #141517;      /* recessed surface (chips) */

    /* Lines */
    --border: #34363a;          /* 1px panel borders */
    --dash: #cfcfcf;            /* dashed rules: title underline, latest box */
    --hair: rgba(255, 255, 255, 0.07);

    /* Text */
    --text: #eaeaea;            /* primary */
    --muted: #9a9c9e;           /* labels, secondary */
    --faint: #6e7073;           /* tertiary */

    /* Accents */
    --green: #3ddc4a;           /* title, "> " prompt, month name */
    --orange: #f0a63c;          /* THE accent: figures, date number, level */
    --red: #ef4136;             /* disclaimer headings */
    --cyan: #4fd8ea;            /* festival names */

    /* Spacing scale (px) */
    --s1: 4px;
    --s2: 8px;
    --s3: 12px;
    --s4: 16px;
    --s5: 20px;
    --s6: 28px;
    --s7: 40px;

    /* Type scale (px), matched to the reference */
    --t-title: 42px;            /* dashboard title */
    --t-section: 23px;          /* "> Latest data - ..." */
    --t-figure: 30px;           /* 73,699 pilgrims / 70-80k / 19-20 Hours */
    --t-daynum: 46px;           /* the big "16th" */
    --t-level: 28px;            /* "Medium crowd" headline */
    --t-lead: 20px;             /* festival names, panel titles */
    --t-body: 16px;             /* legend caption */
    --t-digit: 22px;            /* calendar day numbers */
    --t-label: 15px;            /* grey labels, disclaimer body */
    --t-small: 14px;            /* dense stats, weekday header */
}

/* ---------------------------------------------------------------------------
   Base
   --------------------------------------------------------------------------- */
html, body, [class*="css"] {
    font-family: "VT323", "Courier New", monospace !important;
}

/* Streamlit's theme sets font-family on its own heading/control classes, which
   outranks a plain html/body rule. Text-bearing elements are listed explicitly
   so the pixel face actually applies. */
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
    max-width: 1480px;
    padding-top: var(--s6);
    padding-bottom: var(--s7);
}

h1, h2, h3, h4 { font-weight: normal !important; }

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { transition: none !important; animation: none !important; }
}

/* ---------------------------------------------------------------------------
   Header — green title over a dashed light-grey rule
   --------------------------------------------------------------------------- */
.tci-header {
    padding-bottom: var(--s3);
    margin-bottom: var(--s5);
    border-bottom: 3px dashed var(--dash);
}
.tci-header h1 {
    color: var(--green);
    font-size: var(--t-title);
    margin: 0;
    line-height: 1.05;
    letter-spacing: 0.5px;
}

/* Section headings carry a terminal-style "> " prompt. */
.section {
    color: var(--text);
    font-size: var(--t-section);
    margin: var(--s5) 0 var(--s3);
    line-height: 1.2;
}
.section::before { content: "> "; color: var(--green); }

/* ---------------------------------------------------------------------------
   Latest-data panel — dashed border, transparent ground
   --------------------------------------------------------------------------- */
.latest-box {
    border: 2px dashed var(--dash);
    background: transparent;
    padding: var(--s4) var(--s5);
    margin-bottom: var(--s4);
}
.latest-status {
    color: var(--green);
    font-size: var(--t-label);
    line-height: 1.3;
}
.latest-status::before { content: "\\25A0  "; }
.latest-status.is-fallback { color: var(--orange); }

.latest-big {
    font-size: var(--t-figure);
    margin: var(--s2) 0 0;
    color: var(--text);
    line-height: 1.15;
}
/* Two-column grid of dense operational stats, as in the reference. */
.latest-stats {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--s2) var(--s5);
    font-size: var(--t-small);
    color: var(--muted);
    margin-top: var(--s4);
}
.latest-stats .wide { grid-column: 1 / -1; }

/* ---------------------------------------------------------------------------
   Crowd scale: swatch strip + gradient meter
   --------------------------------------------------------------------------- */
.legend-row { display: flex; gap: var(--s1); margin-bottom: var(--s3); }
.legend-swatch {
    width: 42px;
    height: 42px;
    border: none;
}
/* Swatches up to the current level stay lit; the rest are dimmed, so the strip
   doubles as a level indicator. */
.legend-swatch.dim { opacity: 0.30; }
.legend-caption {
    font-size: var(--t-lead);
    line-height: 1.2;
    color: var(--text);
}
.legend-sub { color: var(--faint); font-size: var(--t-small); margin-top: 2px; }

.meter { position: relative; margin: 0 0 var(--s4); }
.meter-bar { height: 14px; }
/* Triangular marker that slides to the value's position on the scale. */
.meter-marker {
    position: absolute;
    top: 13px;
    width: 0;
    height: 0;
    border-left: 7px solid transparent;
    border-right: 7px solid transparent;
    border-bottom: 9px solid var(--text);
    transform: translateX(-7px);
}

/* ---------------------------------------------------------------------------
   Calendar
   --------------------------------------------------------------------------- */
.cal-month {
    color: var(--green);
    font-size: var(--t-section);
    line-height: 1.9;
    white-space: nowrap;
}
.cal-weekdays {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 3px;
    margin-bottom: 3px;
}
.cal-wk {
    color: var(--muted);
    font-size: var(--t-small);
    text-align: center;
    background: var(--panel);
    border: 1px solid var(--border);
    padding: var(--s1) 0;
}
.cal-cell {
    height: 62px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: var(--t-digit);
    border: 1px solid transparent;
    position: relative;
    /* The reference sets every tile's digits in light type over a soft dark
       shadow, which is what keeps them readable across the whole band ramp. */
    color: #f5f5f0;
    text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.6);
}
/* Days outside the displayed month, and days with neither observation nor
   forecast, are visibly inert. */
.cal-cell.empty { background: transparent; border-color: var(--hair); }
.cal-cell.muted { color: var(--faint); }
.cal-cell.today { outline: 1px dashed rgba(255, 255, 255, 0.5); outline-offset: -4px; }
/* The reference marks the selected day with a light box, not a green glow. */
.cal-selected {
    border: 3px solid var(--text) !important;
    z-index: 5;
}

/* Each day is a coloured tile with a transparent Streamlit button pulled up
   over it to capture the click. Scoped to the keyed calendar week containers so
   it cannot leak onto the month navigation or download buttons. */
[class*="st-key-calweek-"] {
    gap: 0 !important;
    margin-bottom: 3px !important;
}
[class*="st-key-calweek-"] [data-testid="stButton"] button {
    margin-top: -62px !important;
    height: 62px !important;
    min-height: 62px !important;
    background: transparent !important;
    border: 1px solid transparent !important;
    color: transparent !important;
    box-shadow: none !important;
    position: relative;
    z-index: 10;
}
[class*="st-key-calweek-"] [data-testid="stButton"] button:hover {
    background: rgba(255, 255, 255, 0.14) !important;
    border-color: rgba(255, 255, 255, 0.5) !important;
}
[class*="st-key-calweek-"] [data-testid="stButton"] button:focus-visible {
    outline: 2px solid var(--text) !important;
    outline-offset: -2px;
}

/* ---------------------------------------------------------------------------
   Panels (Selected Date, festivals, disclaimer)
   --------------------------------------------------------------------------- */
.panel {
    background: var(--panel);
    border: 1px solid var(--border);
    padding: var(--s5);
    margin-bottom: var(--s4);
}
.panel-title {
    font-size: var(--t-lead);
    color: var(--text);
    margin-bottom: var(--s4);
}

/* Date box beside the meter and level. Wraps rather than compressing, so the
   labels stay on one line instead of breaking mid-phrase in a narrow column. */
.detail-head {
    display: flex;
    gap: var(--s5);
    align-items: flex-start;
    flex-wrap: wrap;
}
.detail-head > .detail-readout { flex: 1 1 190px; min-width: 0; }
.date-box {
    background: var(--panel-alt);
    border: 1px solid var(--border);
    padding: var(--s3) var(--s4);
    text-align: center;
    min-width: 118px;
}
.date-box .day-name { font-size: var(--t-label); color: var(--muted); line-height: 1.2; }
/* The reference sets the day number in the amber accent, not green. */
.date-box .day-num {
    font-size: var(--t-daynum);
    color: var(--orange);
    line-height: 1.05;
}
.date-box .month-yr { font-size: var(--t-small); color: var(--muted); line-height: 1.2; }

.info-label {
    font-size: var(--t-label);
    color: var(--muted);
    margin-top: var(--s4);
    line-height: 1.25;
}
.info-value {
    font-size: var(--t-figure);
    color: var(--orange);
    line-height: 1.15;
}
.info-note { font-size: var(--t-small); color: var(--faint); margin-top: 2px; }
.level-headline {
    font-size: var(--t-level);
    line-height: 1.1;
    margin-top: 2px;
}

/* Provenance tag: is this figure observed or predicted? */
.origin-tag {
    display: inline-block;
    font-size: var(--t-small);
    padding: 0 var(--s2);
    border: 1px solid currentColor;
    letter-spacing: 0.5px;
    vertical-align: 2px;
}
.origin-tag.actual { color: var(--green); }
.origin-tag.forecast { color: var(--orange); }

/* ---------------------------------------------------------------------------
   Context chips (what is driving a given day)
   --------------------------------------------------------------------------- */
.chip-row { display: flex; flex-wrap: wrap; gap: var(--s2); }
.chip {
    font-size: var(--t-small);
    color: var(--text);
    background: var(--panel-sunk);
    border: 1px solid var(--border);
    padding: 1px var(--s2);
}
.chip.hot { border-color: var(--orange); color: var(--orange); }
.chip.cool { border-color: var(--green); color: var(--green); }
.chip.event { border-color: var(--cyan); color: var(--cyan); }

/* ---------------------------------------------------------------------------
   Festivals panel
   --------------------------------------------------------------------------- */
.fest-name {
    color: var(--cyan);
    font-size: var(--t-lead);
    line-height: 1.3;
    margin: var(--s1) 0;
}
.fest-name.none { color: var(--faint); }
.fest-meta { color: var(--faint); font-size: var(--t-small); }
.fest-date { color: var(--muted); font-size: var(--t-label); margin-top: var(--s3); }

/* ---------------------------------------------------------------------------
   Quiet-days ranking
   --------------------------------------------------------------------------- */
.rank-row {
    display: flex;
    align-items: center;
    gap: var(--s3);
    padding: var(--s2) 0;
    border-bottom: 1px solid var(--hair);
    font-size: var(--t-label);
}
.rank-row:last-child { border-bottom: none; }
.rank-chip { width: 14px; height: 14px; flex: 0 0 14px; }
.rank-day { color: var(--text); min-width: 150px; }
.rank-val { color: var(--muted); margin-left: auto; }

/* ---------------------------------------------------------------------------
   Deity backdrop motif
   --------------------------------------------------------------------------- */
.deity-wrap {
    display: flex;
    justify-content: center;
    padding: 0 0 var(--s6);
}
.deity-wrap svg, .deity-wrap img { max-width: 300px; }

/* ---------------------------------------------------------------------------
   Disclaimers
   --------------------------------------------------------------------------- */
.disclaimer-box {
    border: 1px solid var(--border);
    background: var(--panel);
    padding: var(--s5);
}
.disclaimer-box h3 {
    color: var(--red);
    font-size: var(--t-section);
    margin: 0 0 var(--s3);
    text-transform: uppercase;
}
.disclaimer-box p {
    font-size: var(--t-label);
    color: var(--text);
    line-height: 1.45;
    margin: 0;
}

.forecast-disclaimer {
    border-top: 3px dashed var(--border);
    padding-top: var(--s5);
    margin-top: var(--s6);
}
.forecast-disclaimer h3 {
    color: var(--red);
    font-size: var(--t-section);
    margin: 0 0 var(--s3);
}
.forecast-disclaimer p {
    font-size: var(--t-label);
    color: var(--text);
    line-height: 1.5;
    margin-bottom: var(--s3);
}

/* ---------------------------------------------------------------------------
   Streamlit control overrides
   --------------------------------------------------------------------------- */
[data-testid="stButton"] button,
[data-testid="stDownloadButton"] button {
    font-family: "VT323", monospace !important;
    font-size: var(--t-label) !important;
    border-radius: 0 !important;
    background: var(--panel) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
}
[data-testid="stButton"] button:hover,
[data-testid="stDownloadButton"] button:hover {
    border-color: var(--text) !important;
    color: var(--text) !important;
}

[data-testid="stExpander"] {
    border: 1px solid var(--border) !important;
    border-radius: 0 !important;
    background: var(--panel) !important;
}
[data-testid="stExpander"] summary { color: var(--text) !important; }

[data-baseweb="tab-list"] { background: transparent !important; gap: var(--s4); }
[data-baseweb="tab"] {
    font-size: var(--t-label) !important;
    color: var(--muted) !important;
}
[data-baseweb="tab"][aria-selected="true"] { color: var(--green) !important; }
[data-baseweb="tab-highlight"] { background: var(--green) !important; }

/* Hide Streamlit chrome that breaks the terminal illusion. */
#MainMenu, footer, header [data-testid="stToolbar"] { visibility: hidden; }

/* ---------------------------------------------------------------------------
   Mid widths: stack the page's two main rows rather than letting Streamlit
   keep them side by side, which squeezes the detail panel to a few words per
   line. Keyed to the specific rows so the calendar week grid is untouched.
   --------------------------------------------------------------------------- */
@media (max-width: 1250px) {
    [class*="st-key-mainrow"] > [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
    [class*="st-key-mainrow"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        flex: 1 1 100% !important;
        width: 100% !important;
    }
    /* Side by side the artwork sits above the disclaimer; once stacked it is
       decorative only, so give the disclaimer the width instead. */
    .deity-wrap svg, .deity-wrap img { max-width: 220px; }
}

@media (max-width: 1100px) {
    [class*="st-key-calrow"] > [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
    [class*="st-key-calrow"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        flex: 1 1 100% !important;
        width: 100% !important;
    }
}

/* ---------------------------------------------------------------------------
   Narrow screens
   --------------------------------------------------------------------------- */
@media (max-width: 900px) {
    :root {
        --t-title: 32px;
        --t-section: 20px;
        --t-figure: 25px;
        --t-daynum: 38px;
        --t-level: 23px;
        --t-digit: 19px;
    }
    .cal-cell { height: 50px; }
    [class*="st-key-calweek-"] [data-testid="stButton"] button {
        margin-top: -50px !important;
        height: 50px !important;
        min-height: 50px !important;
    }
    .deity-wrap svg, .deity-wrap img { max-width: 210px; }
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
        gap: 3px !important;
    }
    [class*="st-key-calweek-"] [data-testid="stHorizontalBlock"] > div,
    [class*="st-key-calweek-"] [data-testid="stHorizontalBlock"] [data-testid="stColumn"] {
        width: 14.28% !important;
        flex: 1 1 0 !important;
        min-width: 0 !important;
        /* Streamlit's own column gutters would eat most of a 42px tile. */
        padding: 0 !important;
    }
    [class*="st-key-calweek-"] [data-testid="stHorizontalBlock"] [data-testid="stVerticalBlock"] {
        gap: 0 !important;
        min-width: 0 !important;
    }
    .cal-cell { height: 42px; font-size: 17px; }
    [class*="st-key-calweek-"] [data-testid="stButton"] button {
        margin-top: -42px !important;
        height: 42px !important;
        min-height: 42px !important;
        padding: 0 !important;
    }
    .latest-stats { grid-template-columns: 1fr; }
    .cal-wk { font-size: 11px; }
}
"""

# Retained under its previous name so any external import keeps working.
DARK_COMMAND_CENTER_CSS = DASHBOARD_CSS
