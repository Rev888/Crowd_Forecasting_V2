"""Tirumala Crowd Intelligence - temporary Streamlit dashboard.

Calendar-first forecasting UI around the existing production CatBoost model.
"""
from __future__ import annotations

import calendar as pycalendar
import re
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib import data_loader as dl
from lib import predictor

st.set_page_config(
    page_title="Tirumala Crowd Intelligence",
    page_icon="🛕",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Styling: compact terminal / intelligence-console aesthetic.
# ---------------------------------------------------------------------------





def fmt(v, suffix="", decimals=0):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    try:
        return f"{v:,.{decimals}f}{suffix}"
    except Exception:
        return str(v)


def parse_wait_range(raw) -> tuple[float, float] | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", str(raw).replace("–", "-"))]
    if not nums:
        return None
    if len(nums) == 1:
        return nums[0], nums[0]
    return min(nums[0], nums[1]), max(nums[0], nums[1])


def format_wait(pair: tuple[float, float] | None) -> str:
    if not pair:
        return "—"
    lo, hi = pair
    if round(lo, 1) == round(hi, 1):
        return f"{lo:g}h"
    return f"{lo:g}–{hi:g}h"




def band_range(value: float, size: int = 5000) -> tuple[int, int]:
    lo = int(value // size) * size
    return lo, lo + size


def range_text(lo: int, hi: int) -> str:
    return f"{lo // 1000}–{hi // 1000}K"


def month_shift(y: int, m: int, delta: int) -> tuple[int, int]:
    idx = y * 12 + (m - 1) + delta
    return idx // 12, idx % 12 + 1



st.markdown('''
<style>
@import url('https://fonts.googleapis.com/css2?family=VT323&display=swap');
:root {
  --bg:#222222; --panel:#2b2b2b; --text:#e4e9e4; --green:#51c65b;
  --orange:#ed7d32; --red:#ed4e4e; --yellow:#f6c044; --lightgreen: #84cc52;
}
html, body, [class*="css"] { font-family: "VT323", monospace !important; font-size: 20px; }
.stApp { background: var(--bg); color: var(--text); }
.block-container { max-width: 1400px; padding-top: 2rem; padding-bottom: 2rem; }
.tci-header { padding-bottom: 5px; margin-bottom: 10px; border-bottom: 3px dashed var(--text); }
.tci-header h1 { color:var(--green); font-size:2.8rem; margin:0; font-weight:normal; }
.section { color:var(--text); font-size:1.6rem; margin:15px 0 10px; }
.section::before { content: "> "; }

/* Latest Data Box */
.latest-box { border: 2px dashed var(--text); padding: 15px; margin-bottom: 20px; border-radius:4px; position:relative;}
.latest-title { color: var(--green); font-size: 1.1rem; }
.latest-title::before { content: "■ "; }
.latest-main { font-size: 1.8rem; margin: 5px 0;}
.latest-grid { display: flex; flex-wrap: wrap; gap: 15px; font-size: 1rem; }
.latest-grid div { min-width: 150px; }

/* Calendar */
.cal-head { display:flex; align-items:center; justify-content:space-between; margin-bottom:5px; }
.cal-month { color:var(--green); font-size:1.6rem; }
.cal-weekdays { display:grid; grid-template-columns:repeat(7,1fr); gap:1px; margin-bottom:1px; }
.cal-week { color:var(--text); font-size:1.1rem; text-align:center; background: #333; border: 1px solid #444; }
.cal-cell { height:75px; display:flex; align-items:center; justify-content:center; color:white; font-size:1.5rem; position:relative; }
.cal-cell.empty { background:var(--bg); border:1px solid #333; }
.cal-selected { border: 3px solid var(--orange) !important; transform: scale(1.05); z-index:5; }

[data-testid="stVerticalBlock"]:has(.cal-cell) [data-testid="stButton"] button {
  margin-top:-75px !important; height:75px !important; min-height:75px !important;
  background:transparent !important; border:1px solid transparent !important;
  color:transparent !important; box-shadow:none !important; position:relative; z-index:10;
}
[data-testid="stVerticalBlock"]:has(.cal-cell) [data-testid="stButton"] button:hover {
  background:rgba(255,255,255,.2) !important;
}

/* Right Column */
.legend-box { display:flex; gap:4px; margin-bottom:10px; }
.legend-item { width:40px; height:40px; border:2px solid #ccc; }

.detail-box { background: #2a2a2a; padding: 20px; margin-bottom: 20px; border-radius:4px;}
.detail-title { font-size: 1.5rem; margin-bottom: 10px; }
.detail-date-box { border: 1px solid #555; padding: 10px; margin-bottom: 15px; text-align: center; max-width: 120px; }
.detail-date-day { font-size: 1.1rem; color: #ccc; }
.detail-date-num { font-size: 2.5rem; color: var(--orange); line-height: 1; }
.detail-date-month { font-size: 1rem; color: #ccc; }
.detail-label { font-size: 1rem; margin-top: 15px; }
.detail-value { font-size: 1.8rem; color: var(--orange); }

.festivals-box { border-top: 1px solid #555; padding-top: 10px; margin-top: 20px; }
.festival-text { color: #00e5ff; font-size: 1.3rem; line-height: 1.2; margin: 5px 0; }

.disclaimer { border-top: 2px dashed #666; padding-top: 20px; margin-top: 30px; }
.disclaimer h3 { color: var(--red); font-size: 1.6rem; margin:0 0 10px; text-transform:uppercase;}
.disclaimer p { font-size: 1rem; color: #ccc; line-height: 1.3; margin-bottom: 10px; }
</style>
''', unsafe_allow_html=True)
# Displays the main header of the dashboard using custom HTML to match the pixel-art font and dashed bottom border styling.
st.markdown('<div class="tci-header"><h1>Tirumala Crowd Predictor</h1></div>', unsafe_allow_html=True)

def crowd_meta(value: float) -> tuple[str, str, str]:
    if value < 70_000:
        return "Low crowd", "#e4e9e4", "#51c65b"
    if value < 75_000:
        return "Medium-low crowd", "#e4e9e4", "#84cc52"
    if value < 85_000:
        return "Medium crowd", "#e4e9e4", "#f6c044"
    if value < 90_000:
        return "High crowd", "#e4e9e4", "#ed7d32"
    if value < 95_000:
        return "Very high crowd", "#e4e9e4", "#7f1d1d"
    return "Extreme crowd", "#e4e9e4", "#4a1210"

@st.cache_data(ttl=12 * 60 * 60, show_spinner=False)
def cached_snapshot():
    return dl.get_latest_snapshot()

snapshot = cached_snapshot()

# We need to fetch historical valid data for actuals lookup used by day_payload
hist_df = dl.load_merged_history().copy()
if "date" in hist_df.columns:
    hist_df["date"] = pd.to_datetime(hist_df["date"], errors="coerce").dt.normalize()
if "pilgrims" in hist_df.columns:
    hist_df["pilgrims"] = pd.to_numeric(hist_df["pilgrims"], errors="coerce")
hist_df = hist_df.dropna(subset=["date"]).sort_values("date")
valid_hist = hist_df[hist_df["pilgrims"].notna() & (hist_df["pilgrims"] > 0) & (hist_df["pilgrims"] <= 100000)]
actuals = valid_hist.drop_duplicates("date", keep="last").set_index("date")["pilgrims"].astype(float).sort_index() if not valid_hist.empty else pd.Series(dtype=float)

events_df = dl.load_events()
if events_df is not None and not events_df.empty:
    events_df = events_df.copy()
    events_df["start_date"] = pd.to_datetime(events_df["start_date"], errors="coerce")
    events_df["end_date"] = pd.to_datetime(events_df["end_date"], errors="coerce")
    # This release is intentionally limited to 2026, where the event calendar
    # used by the forecasting pipeline is complete/verified for this prototype.
    events_df = events_df[
        events_df["start_date"].notna()
        & events_df["end_date"].notna()
        & (events_df["end_date"] >= pd.Timestamp("2026-01-01"))
        & (events_df["start_date"] <= pd.Timestamp("2026-12-31"))
    ].copy()

actual_lookup = {pd.Timestamp(k).normalize(): float(v) for k, v in actuals.items()}
latest_actual_date = pd.Timestamp(actuals.index.max()).date() if not actuals.empty else None

@st.cache_data(show_spinner=False)
def forecast_one_day(iso_date: str) -> dict:
    d = date.fromisoformat(iso_date)
    return predictor.predict_pilgrims(d, events_df)


def events_for_date(d: date) -> list[dict]:
    if events_df is None or events_df.empty:
        return []
    ts = pd.Timestamp(d).normalize()
    try:
        mask = (pd.to_datetime(events_df["start_date"]) <= ts) & (pd.to_datetime(events_df["end_date"]) >= ts)
    except Exception:
        return []
    rows = events_df.loc[mask]
    out = []
    for _, r in rows.iterrows():
        name = r.get("calendar_label") or r.get("event_name") or r.get("event") or "TTD Event"
        text = str(name)
        major = any(k in text.lower() for k in ["brahmotsav", "garuda seva", "garuda vahana", "vaikunta ekadasi", "vaikuntha ekadasi", "pavitrotsav", "rathasaptami", "rathasapthami"])
        if "major_event" in r and bool(r.get("major_event")):
            major = True
        out.append({"name": text, "type": r.get("event_type"), "importance": r.get("importance"), "major": major})
    return out


def historical_wait_for_date(d: date) -> tuple[float, float] | None:
    if hist_df.empty:
        return None
    rows = hist_df[hist_df["date"] == pd.Timestamp(d).normalize()]
    if rows.empty:
        return None
    row = rows.iloc[-1]
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
    ts = pd.Timestamp(d).normalize()
    actual = actual_lookup.get(ts)
    evs = events_for_date(d)
    if actual is not None:
        lo, hi = band_range(actual)
        wait = historical_wait_for_date(d)
        level, color, bg = crowd_meta(actual)
        return {
            "is_actual": True, "value": actual, "lo": lo, "hi": hi, "wait": wait,
            "level": level, "color": color, "bg": bg, "events": evs,
        }
    result = predictor.predict_pilgrims(d, events_df)
    value = float(result["point_estimate"])
    lo, hi = int(result["range_low"]), int(result["range_high"])
    level, color, bg = crowd_meta(value)
    wait = result.get("wait_range_hours")
    return {
        "is_actual": False, "value": value, "lo": lo, "hi": hi, "wait": wait,
        "level": level, "color": color, "bg": bg, "events": evs,
    }

# ---------------------------------------------------------------------------
# Main calendar
# Split the UI into two main columns (Left for data & calendar, Right for details & legend) to match the dashboard design.
main_col1, main_col2 = st.columns([1.2, 1], gap="large")

with main_col1:
    # Section header for the latest actual scraped data from TTD. Dynamically uses the date from the snapshot.
    st.markdown(f'<div class="section">Latest data - {snapshot.get("date", "n/a")}</div>', unsafe_allow_html=True)
    
    # Latest data box: Renders the most recent TTD operational statistics dynamically.
    latest_html = f'''
    <div class="latest-box">
        <div class="latest-title">last refreshed on {snapshot.get("date", "n/a")}</div>
        <div class="latest-main">{fmt(snapshot.get("pilgrims"))} pilgrims</div>
        <div class="latest-main">{snapshot.get('waiting_time') or "—"} Hours</div>
        <div class="latest-grid">
            <div>Tonsures: {fmt(snapshot.get("tonsures"))}</div>
            <div>Hundi kanukalu: {fmt(snapshot.get("hundi"), " Cr", 2)}</div>
            <div>Laddu sale: {fmt(snapshot.get("laddu"), " Lakh", 2)}</div>
            <div>Annaprasadams: {fmt(snapshot.get("annaprasadam"), " Lakh", 2)}</div>
            <div style="width:100%;">Waiting Compartments: {snapshot.get("waiting_compartments") or "—"}</div>
        </div>
    </div>
    '''
    st.markdown(latest_html, unsafe_allow_html=True)
    
    # Renders the section title for the future crowd predictor calendar.
    st.markdown('<div class="section" style="margin-top:30px;">Future crowd predictor:</div>', unsafe_allow_html=True)
    
    # Calendar implementation: Renders a month view where each day is color-coded by the predicted crowd level.
    current_month = date.today().replace(day=1)
    if "cal_month" not in st.session_state:
        st.session_state.cal_month = current_month
    else:
        current_month = st.session_state.cal_month
        
    cal_head1, cal_head2, cal_head3 = st.columns([1.5, 0.5, 0.5])
    with cal_head1:
        st.markdown(f'<div class="cal-month">{current_month.strftime("%B %Y")}</div>', unsafe_allow_html=True)
    with cal_head2:
        if st.button("<", use_container_width=True):
            y, m = month_shift(current_month.year, current_month.month, -1)
            st.session_state.cal_month = date(y, m, 1)
            st.rerun()
    with cal_head3:
        if st.button(">", use_container_width=True):
            y, m = month_shift(current_month.year, current_month.month, 1)
            st.session_state.cal_month = date(y, m, 1)
            st.rerun()
            
    weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    st.markdown(
        '<div class="cal-weekdays">'
        + "".join(f'<div class="cal-week">{name}</div>' for name in weekday_names)
        + '</div>',
        unsafe_allow_html=True,
    )
    
    weeks = pycalendar.monthcalendar(current_month.year, current_month.month)
    if "selected_date" not in st.session_state:
        st.session_state.selected_date = date.today()

    visible_end = date(current_month.year, current_month.month, pycalendar.monthrange(current_month.year, current_month.month)[1])
    future_map = {}
    if latest_actual_date is not None and visible_end > latest_actual_date:
        try:
            fdf = predictor.forecast_until(visible_end.isoformat(), events_df)
            future_map = {pd.Timestamp(r["date"]).normalize(): r.to_dict() for _, r in fdf.iterrows()}
        except Exception:
            pass

    for week in weeks:
        cols = st.columns(7, gap="small")
        for idx, day_num in enumerate(week):
            with cols[idx]:
                if day_num == 0:
                    st.markdown('<div class="cal-cell empty"></div>', unsafe_allow_html=True)
                    continue
                d = date(current_month.year, current_month.month, day_num)
                ts = pd.Timestamp(d).normalize()
                is_actual = ts in actual_lookup
                if is_actual:
                    value = actual_lookup[ts]
                    level, fg, bg = crowd_meta(value)
                else:
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
                
                selected = d == st.session_state.selected_date
                selected_class = " cal-selected" if selected else ""
                
                card_html = (
                    f'<div class="cal-cell {selected_class}" '
                    f'style="background:{bg};">'
                    f'{day_num}</div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)
                if st.button(str(day_num), key=f"cal_{d.isoformat()}", use_container_width=True):
                    st.session_state.selected_date = d
                    st.rerun()

    payload = day_payload(st.session_state.selected_date)
    events_today = payload["events"]
    
    st.markdown('<div class="festivals-box"><div style="color:white;">□ Utsavams/Festivals this day:</div>', unsafe_allow_html=True)
    if events_today:
        for e in events_today:
            st.markdown(f'<div class="festival-text">{e["name"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="festival-text" style="color:#aaa;">No scheduled events</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="color:#aaa;margin-top:5px;">{st.session_state.selected_date.strftime("%d-%m-%Y")}</div></div>', unsafe_allow_html=True)

with main_col2:
    # Legend
    legend_html = '''
    <div style="display:flex; flex-direction:column; align-items:flex-start; margin-bottom: 20px;">
        <div class="legend-box">
            <div class="legend-item" style="background:#51c65b;"></div>
            <div class="legend-item" style="background:#84cc52;"></div>
            <div class="legend-item" style="background:#f6c044;"></div>
            <div class="legend-item" style="background:#ed7d32;"></div>
            <div class="legend-item" style="background:#7f1d1d;"></div>
            <div class="legend-item" style="background:#4a1210;"></div>
        </div>
        <div style="color:var(--text);font-size:1.1rem;">Crowd levels intensity</div>
    </div>
    '''
    st.markdown(legend_html, unsafe_allow_html=True)
    
    # Selected date info
    sel_date = st.session_state.selected_date
    day_str = sel_date.strftime("%A")
    num_str = sel_date.strftime("%d")
    month_str = sel_date.strftime("%B %Y")
    
    level_label, _, bg_color = crowd_meta(payload["value"])
    wait_text = format_wait(payload["wait"])
    
    detail_html = f'''
    <div class="detail-box">
        <div class="detail-title">Selected Date</div>
        <div style="display:flex; gap: 20px; align-items: center;">
            <div class="detail-date-box">
                <div class="detail-date-day">{day_str}</div>
                <div class="detail-date-num">{num_str}</div>
                <div class="detail-date-month">{month_str}</div>
            </div>
            <div style="flex:1;">
                <div style="font-size:1rem;color:#ccc;">Predicted crowd level:</div>
                <div style="font-size:1.8rem;color:{bg_color};font-weight:bold;">{level_label}</div>
            </div>
        </div>
        
        <div class="detail-label">Expected pilgrims</div>
        <div class="detail-value">{range_text(payload["lo"], payload["hi"]) if payload.get("hi") else "—"}</div>
        
        <div class="detail-label">Expected waiting time in ticketless<br>free darshan</div>
        <div class="detail-value">{wait_text}</div>
    </div>
    '''
    st.markdown(detail_html, unsafe_allow_html=True)
    
    # Disclaimer
    disclaimer_html = '''
    <div class="disclaimer">
        <h3>⚠ DISCLAIMER</h3>
        <p>This is an independent and unofficial project created for informational and planning purposes. It is not affiliated with, associated with, or endorsed by Tirumala Tirupati Devasthanams (TTD) and does not represent official TTD information or advisories.</p>
    </div>
    '''
    st.markdown(disclaimer_html, unsafe_allow_html=True)
    
    disclaimer_bottom_html = '''
    <div class="disclaimer">
        <h3>Forecast Disclaimer:</h3>
        <p>Crowd levels are predicted using Machine Learning (ML) models based on available historical and contextual data. Predictions are estimates and cannot guarantee actual crowd conditions. Real-world conditions may vary due to unforeseen events, operational changes, weather, festivals, and other factors.</p>
        <p>Please use these predictions only as a planning reference. The developers are not responsible for any loss, injury, delay, inconvenience, or other consequences resulting from reliance on the information provided.</p>
    </div>
    '''
    st.markdown(disclaimer_bottom_html, unsafe_allow_html=True)
