"""Tirumala Crowd Predictor — Streamlit Dashboard.

A retro pixel-art styled dashboard for forecasting and monitoring
pilgrim crowd levels at Tirumala, using a CatBoost ML model.
All data is loaded dynamically — nothing is hardcoded.
"""
from __future__ import annotations

# Standard library imports for calendar calculations, regex parsing, and date handling
import calendar as pycalendar
import re
from datetime import date
from pathlib import Path

# Third-party imports for data handling, charting, and the Streamlit framework
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Local library imports: data_loader handles CSV/scrape data, predictor wraps the CatBoost model
from lib import data_loader as dl
from lib import predictor

# ---------------------------------------------------------------------------
# Page configuration — sets the browser tab title, icon, and enables wide layout
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Tirumala Crowd Predictor",
    page_icon="🛕",
    layout="wide",
)

# ---------------------------------------------------------------------------
# CSS Styling — Injects custom styles to create the retro pixel-art dashboard
# Uses the VT323 Google Font for the retro terminal look.
# All colors are defined as CSS variables for easy theming.
# ---------------------------------------------------------------------------
st.markdown('''
<style>
/* Import the retro pixel font from Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=VT323&display=swap');

/* CSS variables for the dark retro color scheme */
:root {
    --bg: #1a1a2e;          /* Main background — deep navy */
    --panel: #16213e;        /* Panel/card backgrounds */
    --panel-alt: #0f3460;    /* Alternate panel for contrast */
    --text: #e4e9e4;         /* Primary text color — soft white */
    --green: #00ff41;        /* Retro green for headers and accents */
    --orange: #ed7d32;       /* Orange for selected items and values */
    --red: #ff4444;          /* Red for warnings and disclaimers */
    --yellow: #f6c044;       /* Yellow for medium crowd levels */
    --cyan: #00e5ff;         /* Cyan for festival/event names */
    --muted: #7a8a7e;        /* Muted grey for secondary text */
    --border: #2a4a5e;       /* Subtle border color */
}

/* Apply the VT323 pixel font globally to all elements */
html, body, [class*="css"] {
    font-family: "VT323", monospace !important;
    font-size: 20px;
}

/* Dark background for the entire Streamlit app */
.stApp {
    background: var(--bg);
    color: var(--text);
}

/* Constrain content width and add padding */
.block-container {
    max-width: 1400px;
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}

/* ===== HEADER ===== */
/* The main title bar with a dashed bottom border mimicking a terminal prompt */
.tci-header {
    padding-bottom: 8px;
    margin-bottom: 15px;
    border-bottom: 3px dashed var(--text);
}
.tci-header h1 {
    color: var(--green);
    font-size: 2.8rem;
    margin: 0;
    font-weight: normal;
    text-shadow: 0 0 10px rgba(0, 255, 65, 0.3);
}

/* ===== SECTION HEADERS ===== */
/* Each section title gets a ">" prefix mimicking a terminal prompt */
.section {
    color: var(--text);
    font-size: 1.6rem;
    margin: 15px 0 10px;
}
.section::before {
    content: "> ";
    color: var(--green);
}

/* ===== LATEST DATA BOX ===== */
/* Dashed border container showing the most recent TTD scrape data */
.latest-box {
    border: 2px dashed var(--text);
    padding: 15px 18px;
    margin-bottom: 20px;
    border-radius: 4px;
    background: rgba(22, 33, 62, 0.5);
}
/* Green dot + label for the refresh timestamp */
.latest-status {
    color: var(--green);
    font-size: 1rem;
}
.latest-status::before {
    content: "■ ";
}
/* Large pilgrim count and wait time numbers */
.latest-big {
    font-size: 1.7rem;
    margin: 4px 0;
    color: var(--text);
}
/* Grid of smaller operational stats (tonsures, hundi, etc.) */
.latest-stats {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 20px;
    font-size: 0.95rem;
    color: var(--muted);
    margin-top: 8px;
}
.latest-stats span {
    min-width: 160px;
}

/* ===== CROWD LEVEL LEGEND ===== */
/* Row of colored squares showing the crowd intensity scale */
.legend-row {
    display: flex;
    gap: 4px;
    margin-bottom: 6px;
}
.legend-swatch {
    width: 38px;
    height: 38px;
    border: 2px solid rgba(255,255,255,0.3);
}

/* ===== CALENDAR ===== */
/* Month name displayed in green */
.cal-month {
    color: var(--green);
    font-size: 1.6rem;
    text-shadow: 0 0 8px rgba(0, 255, 65, 0.2);
}
/* Weekday header row using CSS grid for 7 equal columns */
.cal-weekdays {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 2px;
    margin-bottom: 2px;
}
/* Each weekday label cell */
.cal-wk {
    color: var(--text);
    font-size: 1.05rem;
    text-align: center;
    background: var(--panel);
    border: 1px solid var(--border);
    padding: 3px 0;
}
/* Individual calendar day cell — color-coded by crowd prediction */
.cal-cell {
    height: 72px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 1.4rem;
    font-weight: bold;
    position: relative;
    border: 1px solid rgba(255,255,255,0.08);
    text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
}
/* Empty cells for days outside the current month */
.cal-cell.empty {
    background: transparent;
    border: 1px solid rgba(255,255,255,0.04);
}
/* Highlighted border when a day is selected */
.cal-selected {
    border: 3px solid var(--green) !important;
    box-shadow: 0 0 12px rgba(0, 255, 65, 0.3);
    z-index: 5;
}

/* Invisible Streamlit buttons overlaid on calendar cells for click handling */
[data-testid="stVerticalBlock"]:has(.cal-cell) [data-testid="stButton"] button {
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
/* Hover effect on calendar day buttons */
[data-testid="stVerticalBlock"]:has(.cal-cell) [data-testid="stButton"] button:hover {
    background: rgba(255, 255, 255, 0.15) !important;
    border-color: rgba(0, 255, 65, 0.4) !important;
}

/* ===== SELECTED DATE DETAIL BOX ===== */
.detail-card {
    background: var(--panel);
    border: 1px solid var(--border);
    padding: 18px;
    border-radius: 4px;
    margin-bottom: 15px;
}
/* The date number box (day/month display) */
.date-box {
    border: 1px solid var(--border);
    padding: 8px 12px;
    text-align: center;
    max-width: 110px;
    background: var(--panel-alt);
}
.date-box .day-name {
    font-size: 1rem;
    color: var(--muted);
}
.date-box .day-num {
    font-size: 2.8rem;
    color: var(--green);
    line-height: 1;
    font-weight: bold;
}
.date-box .month-yr {
    font-size: 0.95rem;
    color: var(--muted);
}
/* Labels and values for pilgrims/wait time */
.info-label {
    font-size: 1rem;
    color: var(--muted);
    margin-top: 12px;
}
.info-value {
    font-size: 1.8rem;
    color: var(--orange);
    line-height: 1.1;
}

/* ===== FESTIVAL / EVENTS BOX ===== */
.fest-box {
    border-top: 1px solid var(--border);
    padding-top: 12px;
    margin-top: 18px;
}
/* Festival names in cyan */
.fest-name {
    color: var(--cyan);
    font-size: 1.3rem;
    line-height: 1.2;
    margin: 4px 0;
}

/* ===== DISCLAIMER BOXES ===== */
.disclaimer-box {
    border: 1px solid var(--border);
    background: var(--panel);
    padding: 15px 18px;
    border-radius: 4px;
    margin-top: 15px;
}
.disclaimer-box h3 {
    color: var(--red);
    font-size: 1.5rem;
    margin: 0 0 8px;
    text-transform: uppercase;
}
.disclaimer-box p {
    font-size: 1rem;
    color: var(--muted);
    line-height: 1.3;
    margin-bottom: 8px;
}

/* ===== FORECAST DISCLAIMER (full-width bottom section) ===== */
.forecast-disclaimer {
    border-top: 3px dashed var(--border);
    padding-top: 18px;
    margin-top: 30px;
}
.forecast-disclaimer h3 {
    color: var(--red);
    font-size: 1.5rem;
    margin: 0 0 8px;
}
.forecast-disclaimer p {
    font-size: 1rem;
    color: var(--muted);
    line-height: 1.4;
    margin-bottom: 10px;
}

/* ===== STREAMLIT BUTTON OVERRIDES ===== */
/* Style the navigation buttons (< and > for calendar) */
[data-testid="stButton"] button {
    font-family: "VT323", monospace !important;
    border-radius: 3px !important;
}
</style>
''', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Render the main header — "Tirumala Crowd Predictor" in retro green
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="tci-header"><h1>Tirumala Crowd Predictor</h1></div>',
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Helper functions — used throughout the dashboard for formatting and logic
# ---------------------------------------------------------------------------

def fmt(v, suffix="", decimals=0):
    """Format a numeric value with commas and optional suffix.
    Returns '—' (em dash) for None/NaN values so the UI never shows blanks."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    try:
        return f"{v:,.{decimals}f}{suffix}"
    except Exception:
        return str(v)


def parse_wait_range(raw) -> tuple[float, float] | None:
    """Extract a numeric wait-time range from raw TTD text like '19-20' or '15'.
    Returns a (lo, hi) tuple of hours, or None if unparseable."""
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", str(raw).replace("–", "-"))]
    if not nums:
        return None
    if len(nums) == 1:
        return nums[0], nums[0]
    return min(nums[0], nums[1]), max(nums[0], nums[1])


def format_wait(pair: tuple[float, float] | None) -> str:
    """Convert a (lo, hi) wait-time tuple into a human-readable string like '19-20 Hours'.
    Returns '—' if no data is available."""
    if not pair:
        return "—"
    lo, hi = pair
    if round(lo, 1) == round(hi, 1):
        return f"{lo:g} Hours"
    return f"{lo:g}-{hi:g} Hours"


def crowd_meta(value: float) -> tuple[str, str, str]:
    """Map a pilgrim count to (label, text_color, background_color).
    These colors directly correspond to the legend squares in the UI.
    The thresholds match the ML model's crowd-banding logic."""
    if value < 70_000:
        return "Low crowd", "#ffffff", "#2d8a2e"        # Deep green — least crowded
    if value < 75_000:
        return "Medium-low crowd", "#ffffff", "#6aaf2e"  # Light green
    if value < 80_000:
        return "Medium crowd", "#ffffff", "#d4a017"      # Yellow-gold
    if value < 85_000:
        return "High crowd", "#ffffff", "#e8872b"        # Orange
    if value < 90_000:
        return "Very high crowd", "#ffffff", "#d44a2b"   # Red-orange
    return "Extreme crowd", "#ffffff", "#8b1a1a"         # Dark red — most crowded


def band_range(value: float, size: int = 5000) -> tuple[int, int]:
    """Round a pilgrim count down to the nearest 5K band. e.g. 73,699 → (70000, 75000).
    Used to display ranges like '70-75K' in the UI."""
    lo = int(value // size) * size
    return lo, lo + size


def range_text(lo: int, hi: int) -> str:
    """Format a pilgrim band as a compact K-range string like '70-80k'."""
    return f"{lo // 1000}-{hi // 1000}k"


def month_shift(y: int, m: int, delta: int) -> tuple[int, int]:
    """Shift a (year, month) pair forward or backward by delta months.
    Used by the calendar navigation buttons."""
    idx = y * 12 + (m - 1) + delta
    return idx // 12, idx % 12 + 1


# ---------------------------------------------------------------------------
# Data Loading — fetch snapshot, history, events, and actuals.
# All data is loaded from CSVs and live scrapes — nothing is hardcoded.
# ---------------------------------------------------------------------------

# Cache the latest TTD operational snapshot for 12 hours to avoid hammering the scraper
@st.cache_data(ttl=12 * 60 * 60, show_spinner=False)
def cached_snapshot():
    """Fetch the latest TTD operational data (pilgrims, tonsures, hundi, etc.)
    via live scrape, falling back to stored CSV data on failure."""
    return dl.get_latest_snapshot()

# Retrieve the latest snapshot — this dict powers the "Latest data" box
snapshot = cached_snapshot()

# Load the full historical crowd dataset from merged.csv for trend analysis
hist_df = dl.load_merged_history().copy()
if "date" in hist_df.columns:
    # Normalize all dates to midnight timestamps to avoid comparison issues
    hist_df["date"] = pd.to_datetime(hist_df["date"], errors="coerce").dt.normalize()
if "pilgrims" in hist_df.columns:
    # Coerce pilgrim values to numeric, dropping any corrupted entries
    hist_df["pilgrims"] = pd.to_numeric(hist_df["pilgrims"], errors="coerce")
# Remove rows with missing dates and sort chronologically
hist_df = hist_df.dropna(subset=["date"]).sort_values("date")
# Filter to valid pilgrim counts (> 0 and <= 100K to exclude data errors)
valid_hist = hist_df[hist_df["pilgrims"].notna() & (hist_df["pilgrims"] > 0) & (hist_df["pilgrims"] <= 100000)]
# Build a deduplicated Series of actual pilgrim counts indexed by date
actuals = (
    valid_hist.drop_duplicates("date", keep="last")
    .set_index("date")["pilgrims"]
    .astype(float)
    .sort_index()
    if not valid_hist.empty
    else pd.Series(dtype=float)
)

# Load the official TTD events calendar for 2026-2027 (festivals, utsavams)
events_df = dl.load_events()
if events_df is not None and not events_df.empty:
    events_df = events_df.copy()
    events_df["start_date"] = pd.to_datetime(events_df["start_date"], errors="coerce")
    events_df["end_date"] = pd.to_datetime(events_df["end_date"], errors="coerce")
    # Filter events to the 2026 calendar year (verified data range for this prototype)
    events_df = events_df[
        events_df["start_date"].notna()
        & events_df["end_date"].notna()
        & (events_df["end_date"] >= pd.Timestamp("2026-01-01"))
        & (events_df["start_date"] <= pd.Timestamp("2026-12-31"))
    ].copy()

# Build a fast lookup dict: {Timestamp → pilgrim_count} for actual historical data
actual_lookup = {pd.Timestamp(k).normalize(): float(v) for k, v in actuals.items()}
# Find the most recent date with actual data — forecasts start after this
latest_actual_date = pd.Timestamp(actuals.index.max()).date() if not actuals.empty else None


# ---------------------------------------------------------------------------
# Forecast and event helper functions
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def forecast_one_day(iso_date: str) -> dict:
    """Run the CatBoost model to predict crowd for a single future date.
    Results are cached by Streamlit to avoid redundant model calls."""
    d = date.fromisoformat(iso_date)
    return predictor.predict_pilgrims(d, events_df)


def events_for_date(d: date) -> list[dict]:
    """Look up all TTD events active on a given date from the events calendar.
    Returns a list of dicts with name, type, importance, and whether it's a major event."""
    if events_df is None or events_df.empty:
        return []
    ts = pd.Timestamp(d).normalize()
    try:
        # Check if the date falls within any event's start-end range
        mask = (pd.to_datetime(events_df["start_date"]) <= ts) & (pd.to_datetime(events_df["end_date"]) >= ts)
    except Exception:
        return []
    rows = events_df.loc[mask]
    out = []
    for _, r in rows.iterrows():
        # Try multiple column names for the event label (different CSVs use different names)
        name = r.get("calendar_label") or r.get("event_name") or r.get("event") or "TTD Event"
        text = str(name)
        # Detect major events by keyword matching on the event name
        major = any(k in text.lower() for k in [
            "brahmotsav", "garuda seva", "garuda vahana",
            "vaikunta ekadasi", "vaikuntha ekadasi",
            "pavitrotsav", "rathasaptami", "rathasapthami"
        ])
        # Also check the explicit major_event flag if present in the data
        if "major_event" in r and bool(r.get("major_event")):
            major = True
        out.append({"name": text, "type": r.get("event_type"), "importance": r.get("importance"), "major": major})
    return out


def historical_wait_for_date(d: date) -> tuple[float, float] | None:
    """Look up the historical Sarva Darshan wait time for a specific date.
    Returns (lo, hi) hours or None if no data exists for that date."""
    if hist_df.empty:
        return None
    rows = hist_df[hist_df["date"] == pd.Timestamp(d).normalize()]
    if rows.empty:
        return None
    row = rows.iloc[-1]
    # Try multiple possible column names for wait time data
    for col in ("waiting_time_raw", "waiting_time", "waiting_time_min"):
        if col in row.index:
            raw = row[col]
            if col.endswith("_min"):
                lo = raw
                hi = row.get("waiting_time_max")
                try:
                    if pd.notna(lo) and pd.notna(hi):
                        return float(lo), float(hi)
                except Exception:
                    pass
            else:
                parsed = parse_wait_range(raw)
                if parsed:
                    return parsed
    return None


def day_payload(d: date) -> dict:
    """Build a complete data payload for a given date, combining actual data
    (if available) or model forecast with event information.
    This is the main function that powers the 'Selected Date' detail panel."""
    ts = pd.Timestamp(d).normalize()
    actual = actual_lookup.get(ts)
    evs = events_for_date(d)
    if actual is not None:
        # Use real historical data when available
        lo, hi = band_range(actual)
        wait = historical_wait_for_date(d)
        level, color, bg = crowd_meta(actual)
        return {
            "is_actual": True, "value": actual, "lo": lo, "hi": hi, "wait": wait,
            "level": level, "color": color, "bg": bg, "events": evs,
        }
    # Otherwise, run the ML model to generate a forecast
    result = predictor.predict_pilgrims(d, events_df)
    value = float(result["point_estimate"])
    lo, hi = int(result["range_low"]), int(result["range_high"])
    level, color, bg = crowd_meta(value)
    wait = result.get("wait_range_hours")
    return {
        "is_actual": False, "value": value, "lo": lo, "hi": hi, "wait": wait,
        "level": level, "color": color, "bg": bg, "events": evs,
    }


# ===========================================================================
#  MAIN DASHBOARD LAYOUT
#  Two-column layout matching the reference UI:
#    Left column  → Latest data box + Calendar + Festivals
#    Right column → Legend + Selected date details + Disclaimers
# ===========================================================================

# Dynamically display the section header with the actual data date from the snapshot
st.markdown(
    f'<div class="section">Latest data - {snapshot.get("date", "n/a")}</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# ROW 1: Latest Data Box (left) + Crowd Level Legend (right)
# This row shows the most recent TTD stats alongside the color legend
# ---------------------------------------------------------------------------
top_left, top_right = st.columns([1.3, 1], gap="medium")

with top_left:
    # Render the latest operational data inside a dashed-border terminal box
    # All values come dynamically from the snapshot dict — nothing is hardcoded
    latest_html = f'''
    <div class="latest-box">
        <div class="latest-status">last refreshed on {snapshot.get("date", "n/a")}</div>
        <div class="latest-big">{fmt(snapshot.get("pilgrims"))} pilgrims</div>
        <div class="latest-big">{snapshot.get("waiting_time") or "—"} Hours</div>
        <div class="latest-stats">
            <span>Tonsures: {fmt(snapshot.get("tonsures"))}</span>
            <span>Hundi kanukalu: {fmt(snapshot.get("hundi"), " CR", 2)}</span>
            <span>Laddu sale…{fmt(snapshot.get("laddu"), " Lac", 2)}</span>
            <span>Annaprasadams…{fmt(snapshot.get("annaprasadam"), " Lac", 2)}</span>
            <span style="width:100%;">Waiting Compartments: {snapshot.get("waiting_compartments") or "—"}</span>
        </div>
    </div>
    '''
    st.markdown(latest_html, unsafe_allow_html=True)

with top_right:
    # Render the crowd level legend — 6 colored squares representing the intensity scale
    # Colors match the crowd_meta() function thresholds exactly
    legend_html = '''
    <div style="margin-top: 10px;">
        <div class="legend-row">
            <div class="legend-swatch" style="background:#2d8a2e;"></div>
            <div class="legend-swatch" style="background:#6aaf2e;"></div>
            <div class="legend-swatch" style="background:#d4a017;"></div>
            <div class="legend-swatch" style="background:#e8872b;"></div>
            <div class="legend-swatch" style="background:#d44a2b;"></div>
            <div class="legend-swatch" style="background:#8b1a1a;"></div>
        </div>
        <div style="color:var(--muted);font-size:1.05rem;">Medium crowd</div>
    </div>
    '''
    st.markdown(legend_html, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# ROW 2: Future Crowd Predictor section header
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="section" style="margin-top:25px;">Future crowd predictor:</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# ROW 3: Calendar (left) + Selected Date Details (right)
# This is the main interactive area of the dashboard
# ---------------------------------------------------------------------------
cal_col, detail_col = st.columns([1.2, 1], gap="medium")

with cal_col:
    # --- Calendar Month Navigation ---
    # Initialize the current displayed month (defaults to today's month)
    current_month = date.today().replace(day=1)
    if "cal_month" not in st.session_state:
        st.session_state.cal_month = current_month
    else:
        current_month = st.session_state.cal_month

    # Calendar header: Month name + navigation arrows + Today button
    ch1, ch2, ch3, ch4 = st.columns([2, 0.4, 0.6, 0.4])
    with ch1:
        # Display the current month and year in green retro text
        st.markdown(
            f'<div class="cal-month">{current_month.strftime("%B %Y")}</div>',
            unsafe_allow_html=True,
        )
    with ch2:
        # Left arrow button — navigate to the previous month
        if st.button("◄", key="prev_month", use_container_width=True):
            y, m = month_shift(current_month.year, current_month.month, -1)
            st.session_state.cal_month = date(y, m, 1)
            st.rerun()
    with ch3:
        # Today button — jump back to the current month
        if st.button("Today", key="today_btn", use_container_width=True):
            st.session_state.cal_month = date.today().replace(day=1)
            st.session_state.selected_date = date.today()
            st.rerun()
    with ch4:
        # Right arrow button — navigate to the next month
        if st.button("►", key="next_month", use_container_width=True):
            y, m = month_shift(current_month.year, current_month.month, 1)
            st.session_state.cal_month = date(y, m, 1)
            st.rerun()

    # --- Weekday Headers ---
    # Render Mon-Sun labels as a CSS grid row above the calendar cells
    weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    st.markdown(
        '<div class="cal-weekdays">'
        + "".join(f'<div class="cal-wk">{name}</div>' for name in weekday_names)
        + '</div>',
        unsafe_allow_html=True,
    )

    # --- Initialize selected date ---
    # Default to today if no date has been selected yet
    if "selected_date" not in st.session_state:
        st.session_state.selected_date = date.today()

    # --- Pre-compute forecasts for all visible future days ---
    # This batch call is much faster than forecasting each day individually
    visible_end = date(
        current_month.year, current_month.month,
        pycalendar.monthrange(current_month.year, current_month.month)[1]
    )
    future_map = {}
    if latest_actual_date is not None and visible_end > latest_actual_date:
        try:
            fdf = predictor.forecast_until(visible_end.isoformat(), events_df)
            future_map = {
                pd.Timestamp(r["date"]).normalize(): r.to_dict()
                for _, r in fdf.iterrows()
            }
        except Exception:
            pass  # Gracefully handle forecast failures — cells will show individually

    # --- Render Calendar Grid ---
    # Each week is a row of 7 Streamlit columns
    # Each day cell is color-coded by its crowd prediction level
    weeks = pycalendar.monthcalendar(current_month.year, current_month.month)
    for week in weeks:
        cols = st.columns(7, gap="small")
        for idx, day_num in enumerate(week):
            with cols[idx]:
                if day_num == 0:
                    # Empty cell for days outside the current month
                    st.markdown('<div class="cal-cell empty"></div>', unsafe_allow_html=True)
                    continue

                # Construct the date object for this calendar cell
                d = date(current_month.year, current_month.month, day_num)
                ts = pd.Timestamp(d).normalize()
                is_actual = ts in actual_lookup

                # Determine the crowd level color for this day
                if is_actual:
                    # Use real historical data for past dates
                    value = actual_lookup[ts]
                    level, fg, bg = crowd_meta(value)
                else:
                    # Use ML forecast for future dates
                    r = future_map.get(ts)
                    if r is None:
                        try:
                            r = forecast_one_day(d.isoformat())
                            value = float(r["point_estimate"])
                        except Exception:
                            value = 0
                        level, fg, bg = crowd_meta(value) if value else ("—", "#555", "#333")
                    else:
                        value = float(r["prediction"])
                        level, fg, bg = crowd_meta(value)

                # Check if this day is the currently selected date
                selected = d == st.session_state.selected_date
                sel_cls = " cal-selected" if selected else ""

                # Render the color-coded calendar cell with the day number
                st.markdown(
                    f'<div class="cal-cell{sel_cls}" style="background:{bg};">'
                    f'{day_num}</div>',
                    unsafe_allow_html=True,
                )
                # Invisible button overlay for click detection on this day
                if st.button(str(day_num), key=f"cal_{d.isoformat()}", use_container_width=True):
                    st.session_state.selected_date = d
                    st.rerun()

    # --- Festival/Events Box ---
    # Shows any TTD utsavams/festivals happening on the selected date
    payload = day_payload(st.session_state.selected_date)
    events_today = payload["events"]

    st.markdown('<div class="fest-box">', unsafe_allow_html=True)
    st.markdown(
        '<div style="color:var(--text);">□ Utsavams/Festivals this day:</div>',
        unsafe_allow_html=True,
    )
    if events_today:
        # Display each festival name in cyan
        for e in events_today:
            st.markdown(f'<div class="fest-name">{e["name"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="fest-name" style="color:var(--muted);">No scheduled events</div>',
            unsafe_allow_html=True,
        )
    # Show the formatted date below the festival list
    st.markdown(
        f'<div style="color:var(--muted);margin-top:5px;">'
        f'{st.session_state.selected_date.strftime("%d-%m-%Y")}</div></div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# RIGHT COLUMN: Selected Date Details + Disclaimers
# ---------------------------------------------------------------------------
with detail_col:
    # Retrieve all data for the currently selected date
    sel = st.session_state.selected_date
    level_label, _, bg_color = crowd_meta(payload["value"])
    wait_text = format_wait(payload["wait"])

    # Render the selected date detail card with all prediction info
    detail_html = f'''
    <div class="detail-card">
        <div style="font-size:1.4rem;margin-bottom:12px;color:var(--text);">Selected Date</div>
        <div style="display:flex; gap:18px; align-items:flex-start;">
            <div class="date-box">
                <div class="day-name">{sel.strftime("%A")}</div>
                <div class="day-num">{sel.strftime("%-d")}th</div>
                <div class="month-yr">{sel.strftime("%B %Y")}</div>
            </div>
            <div style="flex:1;">
                <div style="margin-bottom: 4px;">
                    <div class="legend-row" style="margin-bottom:4px;">
                        <div class="legend-swatch" style="background:#2d8a2e;width:28px;height:18px;"></div>
                        <div class="legend-swatch" style="background:#6aaf2e;width:28px;height:18px;"></div>
                        <div class="legend-swatch" style="background:#d4a017;width:28px;height:18px;border:3px solid var(--green);"></div>
                        <div class="legend-swatch" style="background:#e8872b;width:28px;height:18px;"></div>
                        <div class="legend-swatch" style="background:#d44a2b;width:28px;height:18px;"></div>
                        <div class="legend-swatch" style="background:#8b1a1a;width:28px;height:18px;"></div>
                    </div>
                </div>
                <div style="font-size:0.95rem;color:var(--muted);">Predicted crowd level:</div>
                <div style="font-size:1.8rem;color:{bg_color};font-weight:bold;">{level_label}</div>
            </div>
        </div>

        <div class="info-label">Expected pilgrims</div>
        <div class="info-value">{range_text(payload["lo"], payload["hi"]) if payload.get("hi") else "—"}</div>

        <div class="info-label">Expected waiting time in ticketless<br>free darshan</div>
        <div class="info-value">{wait_text}</div>
    </div>
    '''
    st.markdown(detail_html, unsafe_allow_html=True)

    # --- Disclaimer Box ---
    # Clearly states this is an unofficial, independent project
    disclaimer_html = '''
    <div class="disclaimer-box">
        <h3>⚠ DISCLAIMER</h3>
        <p>This is an independent and unofficial project created for informational and
        planning purposes. It is not affiliated with, associated with, or endorsed by
        Tirumala Tirupati Devasthanams (TTD) and does not represent official TTD
        information or advisories.</p>
    </div>
    '''
    st.markdown(disclaimer_html, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# FULL-WIDTH BOTTOM SECTION: Forecast Disclaimer
# This appears below both columns, spanning the full width of the page
# ---------------------------------------------------------------------------
st.markdown('''
<div class="forecast-disclaimer">
    <h3>Forecast Disclaimer:</h3>
    <p>Crowd levels are predicted using Machine Learning (ML) models based on available
    historical and contextual data. Predictions are estimates and cannot guarantee actual
    crowd conditions. Real-world conditions may vary due to unforeseen events, operational
    changes, weather, festivals, and other factors.</p>
    <p>Please use these predictions only as a planning reference. The developers are not
    responsible for any loss, injury, delay, inconvenience, or other consequences resulting
    from reliance on the information provided.</p>
</div>
''', unsafe_allow_html=True)
