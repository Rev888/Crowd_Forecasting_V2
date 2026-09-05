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
st.markdown(
    """
<style>
:root {
  --bg:#080b09; --panel:#0e130f; --panel2:#111811; --line:#1d2a20;
  --text:#d8e5da; --muted:#6d7c71; --green:#57ff6b; --red:#ff4d4d;
  --gold:#d8b35a; --yellow:#e7c95c; --orange:#ff8b3d;
}
html, body, [class*="css"] { font-family: "JetBrains Mono", "IBM Plex Mono", Consolas, monospace; }
.stApp { background: var(--bg); color: var(--text); }
.block-container { max-width: 1440px; padding-top: 1.2rem; padding-bottom: 2rem; }
.tci-header { border:1px solid var(--line); border-left:3px solid var(--green); background:var(--panel);
  padding:16px 20px; margin-bottom:18px; }
.tci-header h1 { color:var(--green); font-size:1.55rem; letter-spacing:3px; margin:0; font-weight:700; }
.tci-header p { color:var(--muted); font-size:.72rem; letter-spacing:1px; margin:5px 0 0; }
.section { color:var(--green); font-size:.72rem; letter-spacing:2px; text-transform:uppercase;
  border-bottom:1px solid var(--line); padding:7px 0; margin:22px 0 12px; }
.card { border:1px solid var(--line); background:var(--panel); padding:12px 14px; }
.card .label { color:var(--muted); font-size:.62rem; letter-spacing:1.3px; text-transform:uppercase; }
.card .value { color:var(--text); font-size:1.16rem; font-weight:700; margin-top:4px; }
.card .sub { color:var(--muted); font-size:.67rem; margin-top:4px; }
.status { font-size:.66rem; letter-spacing:1px; text-transform:uppercase; }

/* Calendar */
.cal-shell { border:1px solid var(--line); background:#090d0a; padding:10px; }
.cal-head { display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid var(--line);
  padding:4px 6px 10px; margin-bottom:8px; }
.cal-month { color:var(--green); font-size:.95rem; font-weight:700; letter-spacing:2px; text-transform:uppercase; }
.cal-legend { color:var(--muted); font-size:.58rem; letter-spacing:.3px; }
.cal-week { color:#58655c; font-size:.55rem; letter-spacing:1px; text-transform:uppercase; text-align:center; padding:2px 0 5px; }
.cal-weekdays { display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:8px; margin-bottom:8px; }
.cal-weekdays .cal-week { padding:2px 0 5px; }
.cal-cell-wrap { padding:2px; }
.cal-cell { min-height:76px; border:1px solid rgba(255,255,255,.08); padding:6px 7px; position:relative; }
.cal-cell.actual { opacity:.48; filter:saturate(.35); }
.cal-cell.future { opacity:1; }
.cal-cell.empty { background:transparent; border-color:transparent; }
.cal-day { font-size:.67rem; font-weight:700; color:#e3ece5; }
.cal-range { font-size:.62rem; font-weight:700; margin-top:7px; color:#f0f4f0; }
.cal-wait { font-size:.57rem; margin-top:4px; color:#b6c0b8; }
.cal-event { position:absolute; top:5px; right:6px; width:7px; height:7px; border-radius:50%; background:var(--gold); box-shadow:0 0 0 1px rgba(216,179,90,.28); }
.cal-selected { outline:1px solid var(--green); box-shadow:inset 0 0 0 1px rgba(87,255,107,.18); }
.cal-extreme { border-color:rgba(216,179,90,.75); box-shadow: inset 0 0 0 1px rgba(216,179,90,.12); }

/* Use links inside cells for actual click behavior */
[data-testid="stVerticalBlock"]:has(.cal-cell) [data-testid="stButton"] button {
  margin-top:-76px !important; height:76px !important; min-height:76px !important;
  background:transparent !important; border:1px solid transparent !important;
  color:transparent !important; box-shadow:none !important;
  position:relative; z-index:10;
}
[data-testid="stVerticalBlock"]:has(.cal-cell) [data-testid="stButton"] button:hover {
  border-color:var(--green) !important; background:rgba(87,255,107,.04) !important;
}

.detail-grid { display:grid; grid-template-columns: 1.1fr .9fr; gap:10px; }
.detail-main { border:1px solid var(--line); background:var(--panel); padding:16px; }
.detail-kicker { color:var(--muted); font-size:.62rem; letter-spacing:1.4px; text-transform:uppercase; }
.detail-title { color:#edf4ee; font-size:1.15rem; font-weight:700; margin-top:3px; }
.detail-range { color:var(--green); font-size:2.1rem; line-height:1.05; font-weight:800; margin:12px 0 5px; }
.detail-wait { color:#d8e5da; font-size:1rem; font-weight:700; }
.detail-badge { display:inline-block; padding:4px 8px; border:1px solid currentColor; font-size:.61rem; letter-spacing:1px; margin-top:7px; }
.factor { color:#b6c0b8; font-size:.7rem; margin-top:4px; }
.advanced { border:1px solid var(--line); background:#090d0a; padding:8px 10px; }

[data-testid="stButton"] button { font-family:inherit !important; border-radius:3px !important; }
[data-testid="stButton"] button[kind="primary"] { background:#122016 !important; border:1px solid #2a4a30 !important; color:var(--green) !important; }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="tci-header"><h1>TIRUMALA CROWD INTELLIGENCE</h1>'
    '<p>DARSHAN FORECASTING &amp; OPERATIONAL MONITORING — TTD TIRUMALA</p></div>',
    unsafe_allow_html=True,
)


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


def crowd_meta(value: float) -> tuple[str, str, str]:
    # Crowd colour is based ONLY on expected/observed pilgrim count.
    # Events are shown independently with a small gold dot.
    if value < 70_000:
        return "LOW", "#39d353", "rgba(10,55,20,.52)"       # GREEN
    if value < 75_000:
        return "MODERATE", "#e6d447", "rgba(62,58,10,.58)"  # YELLOW
    if value < 85_000:
        return "HIGH", "#ff8b3d", "rgba(72,38,10,.60)"      # ORANGE
    if value < 90_000:
        return "VERY HIGH", "#ff3b3b", "rgba(78,8,8,.66)"   # RED
    return "EXTREME", "#b80f18", "rgba(48,4,7,.78)"         # DARK RED


def band_range(value: float, size: int = 5000) -> tuple[int, int]:
    lo = int(value // size) * size
    return lo, lo + size


def range_text(lo: int, hi: int) -> str:
    return f"{lo // 1000}–{hi // 1000}K"


def month_shift(y: int, m: int, delta: int) -> tuple[int, int]:
    idx = y * 12 + (m - 1) + delta
    return idx // 12, idx % 12 + 1


# ---------------------------------------------------------------------------
# Latest TTD operational data
# ---------------------------------------------------------------------------
st.markdown('<div class="section">Latest TTD Operational Data</div>', unsafe_allow_html=True)
@st.cache_data(ttl=12 * 60 * 60, show_spinner=False)
def cached_snapshot():
    return dl.get_latest_snapshot()

refresh_col, _ = st.columns([1, 5])
with refresh_col:
    if st.button("REFRESH TTD DATA", use_container_width=True):
        cached_snapshot.clear()
        try:
            dl.get_latest_snapshot.clear()
        except Exception:
            pass
        st.rerun()

snapshot = cached_snapshot()
if snapshot.get("source") == "unavailable":
    st.error("No TTD operational data is available (live scrape failed and no stored data was found).")
else:
    is_live = snapshot.get("source") == "live"
    status = "LIVE SCRAPE" if is_live else "STORED FALLBACK — LIVE SCRAPE UNAVAILABLE"
    status_color = "#57ff6b" if is_live else "#ef8a3d"
    a, b = st.columns([3, 1])
    with a:
        st.caption(f"Data date: **{snapshot.get('date', 'n/a')}**")
    with b:
        st.markdown(f'<div class="status" style="color:{status_color}">● {status}</div>', unsafe_allow_html=True)

    cards = [
        ("PILGRIMS (DARSHAN)", fmt(snapshot.get("pilgrims"))),
        ("SARVA DARSHAN WAIT", f"{snapshot.get('waiting_time')} H" if snapshot.get("waiting_time") else "—"),
        ("WAITING COMPARTMENTS", snapshot.get("waiting_compartments") or "—"),
        ("TONSURES", fmt(snapshot.get("tonsures"))),
        ("HUNDI KANUKALU", fmt(snapshot.get("hundi"), " Cr", 2)),
        ("LADDU SALES", fmt(snapshot.get("laddu"), " Lakh", 2)),
        ("ANNAPRASADAM", fmt(snapshot.get("annaprasadam"), " Lakh", 2)),
        ("MEDICAL CASES", fmt(snapshot.get("medical"))),
    ]
    cols = st.columns(4)
    for i, (label, value) in enumerate(cards):
        with cols[i % 4]:
            st.markdown(f'<div class="card"><div class="label">{label}</div><div class="value">{value}</div></div>', unsafe_allow_html=True)
        if i % 4 == 3 and i != len(cards) - 1:
            cols = st.columns(4)
    st.caption(f"Last updated: {snapshot.get('date', 'n/a')} · source: {snapshot.get('source')} · refresh window: 12h")

# ---------------------------------------------------------------------------
# Historical crowd
# ---------------------------------------------------------------------------
st.markdown('<div class="section">Historical Crowd</div>', unsafe_allow_html=True)
hist_df = dl.load_merged_history().copy()
if "date" in hist_df.columns:
    hist_df["date"] = pd.to_datetime(hist_df["date"], errors="coerce").dt.normalize()
if "pilgrims" in hist_df.columns:
    hist_df["pilgrims"] = pd.to_numeric(hist_df["pilgrims"], errors="coerce")
hist_df = hist_df.dropna(subset=["date"]).sort_values("date")
valid_hist = hist_df[hist_df["pilgrims"].notna() & (hist_df["pilgrims"] > 0) & (hist_df["pilgrims"] <= 100000)]
actuals = valid_hist.drop_duplicates("date", keep="last").set_index("date")["pilgrims"].astype(float).sort_index() if not valid_hist.empty else pd.Series(dtype=float)
if actuals.empty:
    st.warning("No historical pilgrim data available to chart.")
else:
    current_year = date.today().year
    actuals_year = actuals[actuals.index.year == current_year]
    plot_df = actuals_year.reset_index()
    plot_df.columns = ["date", "pilgrims"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=plot_df["date"], y=plot_df["pilgrims"], mode="lines",
        line=dict(color="#c84a4a", width=1.25), name="Pilgrims",
        hovertemplate="%{x|%Y-%m-%d}<br>%{y:,.0f} pilgrims<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#0e130f", plot_bgcolor="#0e130f",
        font=dict(family="JetBrains Mono, monospace", color="#bdc9c0", size=11),
        margin=dict(l=8, r=8, t=8, b=8), height=285,
        xaxis=dict(gridcolor="#1d2a20", rangeslider=dict(visible=False)),
        yaxis=dict(gridcolor="#1d2a20", title="Pilgrims", rangemode="tozero"),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Calendar data sources
# ---------------------------------------------------------------------------
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
# ---------------------------------------------------------------------------
st.markdown('<div class="section">Crowd Forecast Calendar</div>', unsafe_allow_html=True)
st.markdown(
    '<div style="color:#6d7c71;font-size:.58rem;letter-spacing:.5px;margin:-4px 0 8px;">'
    '<span style="color:#39d353;">● &lt;70K</span> &nbsp;'
    '<span style="color:#e6d447;">● 70–75K</span> &nbsp;'
    '<span style="color:#ff8b3d;">● 75–85K</span> &nbsp;'
    '<span style="color:#ff3b3b;">● 85–90K</span> &nbsp;'
    '<span style="color:#b80f18;">● 90K+</span> &nbsp;'
    '<span style="color:#d8b35a;">· GOLD DOT = MAJOR EVENT</span>'
    '</div>',
    unsafe_allow_html=True,
)

# Calendar scope: 2026 only. Historical actuals + remaining 2026 forecast.
month_min = pd.Timestamp("2026-01-01")
month_max = pd.Timestamp("2026-12-01")
if "calendar_month" not in st.session_state:
    today_month = pd.Timestamp(date.today().replace(day=1))
    st.session_state.calendar_month = min(max(today_month, month_min), month_max)

current_month = pd.Timestamp(st.session_state.calendar_month).to_period("M").to_timestamp()
current_month = min(max(current_month, month_min), month_max)
st.session_state.calendar_month = current_month

# Month navigation: January through December 2026.
months_total = (month_max.year - month_min.year) * 12 + (month_max.month - month_min.month) + 1
months_from_start = (current_month.year - month_min.year) * 12 + (current_month.month - month_min.month)
month_position = months_from_start + 1

nav_l, nav_c, nav_r = st.columns([1.2, 5.6, 1.2])
with nav_l:
    if st.button("‹ PREV", use_container_width=True, disabled=current_month <= month_min):
        y, m = month_shift(current_month.year, current_month.month, -1)
        st.session_state.calendar_month = pd.Timestamp(y, m, 1)
        st.rerun()

with nav_c:
    st.markdown(
        f'<div style="text-align:center;color:#57ff6b;font-family:monospace;letter-spacing:2px;font-size:1rem;">'
        f'{current_month.strftime("%B %Y").upper()}'
        f'<span style="color:#58655c;font-size:.55rem;letter-spacing:1px;margin-left:10px;">'
        f'{month_position}/{months_total}'
        f'</span></div>',
        unsafe_allow_html=True,
    )

with nav_r:
    if st.button("NEXT ›", use_container_width=True, disabled=current_month >= month_max):
        y, m = month_shift(current_month.year, current_month.month, 1)
        st.session_state.calendar_month = pd.Timestamp(y, m, 1)
        st.rerun()

# Small jump control so every 2026 month is directly reachable.
month_options = pd.date_range(month_min, month_max, freq="MS")
month_labels = [m.strftime("%B %Y") for m in month_options]
selected_month_idx = month_options.get_loc(current_month)

jump_label = st.selectbox(
    "Jump to month",
    month_labels,
    index=selected_month_idx,
    label_visibility="collapsed",
)
jump_month = month_options[month_labels.index(jump_label)]
if jump_month != current_month:
    st.session_state.calendar_month = jump_month
    st.rerun()

# Calendar header: one horizontal MON→SUN row above the 7-column grid.
weekday_names = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
st.markdown(
    '<div class="cal-weekdays">'
    + "".join(f'<div class="cal-week">{name}</div>' for name in weekday_names)
    + '</div>',
    unsafe_allow_html=True,
)

weeks = pycalendar.monthcalendar(current_month.year, current_month.month)
if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today() if (date.today().year == current_month.year and date.today().month == current_month.month) else date(current_month.year, current_month.month, 1)

# Forecast only through the end of the visible 2026 month.
visible_end = date(current_month.year, current_month.month, pycalendar.monthrange(current_month.year, current_month.month)[1])
future_map = {}
if latest_actual_date is not None and visible_end > latest_actual_date:
    try:
        fdf = predictor.forecast_until(visible_end.isoformat(), events_df)
        future_map = {pd.Timestamp(r["date"]).normalize(): r.to_dict() for _, r in fdf.iterrows()}
    except Exception as exc:
        st.error(f"Forecast generation failed: {exc}")

for week in weeks:
    cols = st.columns(7, gap="small")
    for idx, day_num in enumerate(week):
        with cols[idx]:
            if day_num == 0:
                st.markdown('<div class="cal-cell empty"></div>', unsafe_allow_html=True)
                continue
            d = date(current_month.year, current_month.month, day_num)
            ts = pd.Timestamp(d).normalize()
            evs = events_for_date(d)
            is_actual = ts in actual_lookup
            if is_actual:
                value = actual_lookup[ts]
                lo, hi = band_range(value)
                level, fg, bg = crowd_meta(value)
                wait = historical_wait_for_date(d)
            else:
                r = future_map.get(ts)
                if r is None:
                    try:
                        r = forecast_one_day(d.isoformat())
                        value = float(r["point_estimate"]); lo, hi = int(r["range_low"]), int(r["range_high"]); wait = r.get("wait_range_hours")
                    except Exception:
                        value = 0; lo, hi = 0, 0; wait = None
                    level, fg, bg = crowd_meta(value) if value else ("—", "#657267", "#111711")
                else:
                    value = float(r["prediction"]); lo, hi = int(r["lo"]), int(r["hi"]); wait = r.get("wait")
                    level, fg, bg = crowd_meta(value)
            selected = d == st.session_state.selected_date
            actual_class = " actual" if is_actual else ""
            special = ""
            selected_class = " cal-selected" if selected else ""
            wait_text = format_wait(wait)
            event_marker = '<span class="cal-event"></span>' if any(e["major"] for e in evs) else ''
            card_html = (
                f'<div class="cal-cell future{actual_class}{special}{selected_class}" '
                f'style="background:{bg};border-left:2px solid {fg};">'
                f'{event_marker}'
                f'<div class="cal-day">{day_num:02d}</div>'
                f'<div class="cal-range">{range_text(lo, hi) if hi else "—"}</div>'
                f'<div class="cal-wait">{wait_text}</div></div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)
            if st.button(str(day_num), key=f"cal_{d.isoformat()}", use_container_width=True, help=f"Select {d.isoformat()}"):
                st.session_state.selected_date = d
                st.rerun()

st.caption("GREY = verified historical actual · COLORED = crowd level · GOLD DOT = major Tirumala event · CALENDAR: 2026 ONLY")

selected_date = st.session_state.selected_date

# ---------------------------------------------------------------------------
# Selected-date details
# ---------------------------------------------------------------------------
st.markdown('<div class="section">Selected Date Intelligence</div>', unsafe_allow_html=True)
payload = day_payload(selected_date)
events_today = payload["events"]

status_label = "ACTUAL TTD DATA" if payload["is_actual"] else "MODEL FORECAST"
main_level = payload["level"]
level_label, level_color, _ = crowd_meta(payload["value"])
wait_text = format_wait(payload["wait"])

left, right = st.columns([1.3, .7], gap="small")
with left:
    st.markdown(
        f'<div class="detail-main">'
        f'<div class="detail-kicker">{status_label}</div>'
        f'<div class="detail-title">{selected_date.strftime("%A · %d %B %Y")}</div>'
        f'<div class="detail-range">{range_text(payload["lo"], payload["hi"])}</div>'
        f'<div style="color:#7f8d82;font-size:.65rem;letter-spacing:1px;">EXPECTED / OBSERVED PILGRIMS</div>'
        f'<div style="margin-top:12px;color:{level_color};font-size:.7rem;font-weight:700;letter-spacing:1.4px;">{level_label}</div>'
        f'</div>', unsafe_allow_html=True,
    )
    if wait_text != "—":
        st.markdown(f'<div class="card" style="margin-top:10px;"><div class="label">SARVA DARSHAN WAIT · APPROXIMATE</div><div class="value">{wait_text}</div></div>', unsafe_allow_html=True)
with right:
    event_lines = "<br>".join(f"• {e['name']}" for e in events_today) if events_today else "No scheduled Tirumala event"
    st.markdown(f'<div class="card"><div class="label">TIRUMALA EVENT</div><div class="value" style="font-size:.92rem;">{event_lines}</div></div>', unsafe_allow_html=True)

# Human-readable factors
if not payload["is_actual"]:
    try:
        result = predictor.predict_pilgrims(selected_date, events_df)
        row = result.get("feature_row", {})
        factors = []
        if row.get("is_weekend"):
            factors.append("Weekend")
        if row.get("is_long_weekend"):
            factors.append("Long weekend")
        if row.get("is_public_holiday"):
            factors.append(str(row.get("holiday_name") or "Public holiday"))
        elif row.get("is_any_source_state_holiday"):
            factors.append("Source-state holiday")
        if row.get("is_vaikunta_ekadashi"):
            factors.append("Vaikunta Ekadashi")
        if row.get("is_rathasapthami"):
            factors.append("Rathasaptami")
        if row.get("is_pournami"):
            factors.append("Pournami")
        if row.get("pilgrims_lag_1d") is not None:
            factors.append(f"Previous-day crowd: {float(row['pilgrims_lag_1d']):,.0f}")
        if row.get("pilgrims_prev_year") is not None:
            factors.append(f"Previous-year reference: {float(row['pilgrims_prev_year']):,.0f}")
        if events_today:
            factors.append("Official Tirumala event")
        st.markdown('<div class="card" style="margin-top:10px;"><div class="label">WHY THIS FORECAST?</div>' + ("".join(f'<div class="factor">• {x}</div>' for x in factors) if factors else '<div class="factor">No single dominant factor identified.</div>') + '</div>', unsafe_allow_html=True)

        # Historical comparison
        if not hist_df.empty:
            same_month_day = hist_df[(hist_df["date"].dt.month == selected_date.month) & (hist_df["date"].dt.day == selected_date.day)]["pilgrims"] if "pilgrims" in hist_df.columns else pd.Series(dtype=float)
            if not same_month_day.empty:
                st.caption(f"Historical same-date reference: mean {same_month_day.mean():,.0f} pilgrims across available years.")
    except Exception:
        pass

with st.expander("ADVANCED FORECAST DATA / MODEL INPUTS"):
    if payload["is_actual"]:
        st.write("This date uses actual TTD data; no model forecast was used for the main calendar cell.")
    else:
        try:
            result = predictor.predict_pilgrims(selected_date, events_df)
            row = pd.Series(result.get("feature_row", {}), dtype="object")
            st.dataframe(row.rename("value").to_frame(), use_container_width=True)
        except Exception as exc:
            st.error(f"Could not load model input details: {exc}")

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
st.caption("Prototype build · Production model: future-safe Optuna CatBoost · Historical actuals are preferred whenever available.")