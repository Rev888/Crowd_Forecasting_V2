"""Tirumala Crowd Predictor — Streamlit dashboard.

A retro pixel-art dashboard for monitoring and forecasting pilgrim footfall at
Tirumala, backed by a CatBoost model over calendar, holiday, Panchangam and
official TTD-event features.

Design rule for this file: **nothing numeric is hardcoded**. Every figure,
colour threshold, label, date range and chart series is derived at runtime from
the datasets in ``data/`` and the model in ``tirumala_*.cbm``. The only fixed
content is the layout, the copy in the disclaimers, and the decorative pixel
artwork in ``lib/pixel_art.py``.
"""
from __future__ import annotations

import calendar as pycalendar
import re
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib import crowd_levels as cl
from lib import data_loader as dl
from lib import pixel_art
from lib import predictor
from lib.styles import DASHBOARD_CSS

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Tirumala Crowd Predictor",
    page_icon="🛕",
    layout="wide",
)

# Injected with st.html rather than st.markdown: st.markdown runs its input
# through the Markdown parser first, which mangles CSS attribute selectors
# such as [class*="..."] into emphasis tags and silently drops those rules.
st.html(f"<style>{DASHBOARD_CSS}</style>")

# How far past the last observed day we are willing to run the recursive
# forecast. Beyond this the model is extrapolating from its own output for so
# long that the result is not worth showing, so the UI says so instead.
MAX_FORECAST_DAYS = 400

# Number of trailing observed days drawn on the trend chart.
TREND_HISTORY_DAYS = 45

# How many quiet days to rank in the "best days to visit" panel.
QUIET_DAY_COUNT = 5


# ---------------------------------------------------------------------------
# Small formatting helpers
# ---------------------------------------------------------------------------

def fmt(value, suffix: str = "", decimals: int = 0) -> str:
    """Format a number with thousands separators, or an em dash if missing."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    try:
        return f"{value:,.{decimals}f}{suffix}"
    except (TypeError, ValueError):
        return str(value)


def ordinal(n: int) -> str:
    """Render a day number with its English ordinal suffix (1st, 2nd, 16th)."""
    if 11 <= (n % 100) <= 13:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def parse_wait_range(raw) -> tuple[float, float] | None:
    """Pull an (lo, hi) hour range out of raw TTD wait text like "19-20"."""
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    numbers = [
        float(x)
        for x in re.findall(r"\d+(?:\.\d+)?", str(raw).replace("–", "-"))
    ]
    if not numbers:
        return None
    if len(numbers) == 1:
        return numbers[0], numbers[0]
    return min(numbers[:2]), max(numbers[:2])


def coerce_wait(value) -> tuple[float, float] | None:
    """Normalise a wait value into an (lo, hi) pair or None.

    The forecast table stores waits as tuples, but a column holding tuples
    alongside missing entries can surface as NaN — which is truthy, so it has
    to be filtered out explicitly rather than relying on a falsiness check.
    """
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, (tuple, list)) and len(value) >= 2:
        try:
            return float(value[0]), float(value[1])
        except (TypeError, ValueError):
            return None
    return parse_wait_range(value)


def format_wait(pair) -> str:
    """Render a wait range as "19-20 Hours" (or "15 Hours" when flat)."""
    pair = coerce_wait(pair)
    if not pair:
        return "—"
    lo, hi = pair
    if round(lo, 1) == round(hi, 1):
        return f"{lo:g} Hours"
    return f"{lo:g}-{hi:g} Hours"


def month_shift(year: int, month: int, delta: int) -> tuple[int, int]:
    """Move a (year, month) pair by ``delta`` months."""
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def month_bounds(anchor: date) -> tuple[date, date]:
    """First and last calendar day of the month containing ``anchor``."""
    last = pycalendar.monthrange(anchor.year, anchor.month)[1]
    return anchor.replace(day=1), anchor.replace(day=last)


# ---------------------------------------------------------------------------
# Data loading. Everything below is derived from disk or the live scraper.
# ---------------------------------------------------------------------------

@st.cache_data(ttl=12 * 60 * 60, show_spinner=False)
def load_snapshot() -> dict:
    """Latest TTD operational bulletin (live scrape, or stored fallback)."""
    return dl.get_latest_snapshot()


@st.cache_data(show_spinner=False)
def load_history() -> pd.DataFrame:
    """Historical daily rows, normalised and sorted by date."""
    df = dl.load_merged_history().copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    df["pilgrims"] = pd.to_numeric(df["pilgrims"], errors="coerce")
    return df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_actuals() -> pd.Series:
    """Observed daily footfall, deduplicated and filtered to plausible values."""
    series = dl.build_actuals_series()
    series.index = pd.to_datetime(series.index).normalize()
    series = cl.clean_actuals(series)
    return series[~series.index.duplicated(keep="last")].sort_index()


@st.cache_data(show_spinner=False)
def load_event_calendar() -> pd.DataFrame:
    """Official TTD Divya Utsavam calendar, using whatever range the file covers."""
    df = dl.load_events()
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce")
    return df.dropna(subset=["start_date", "end_date"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_thresholds() -> list[float]:
    """The six-band crowd scale, recomputed from the observed distribution."""
    return cl.compute_thresholds(load_actuals())


snapshot = load_snapshot()
hist_df = load_history()
actuals = load_actuals()
events_df = load_event_calendar()
thresholds = load_thresholds()

# Fast date -> observed value lookup, and the edge of observed data.
actual_lookup: dict[pd.Timestamp, float] = {
    pd.Timestamp(k).normalize(): float(v) for k, v in actuals.items()
}
last_actual_date: date | None = (
    pd.Timestamp(actuals.index.max()).date() if not actuals.empty else None
)
forecast_limit: date | None = (
    last_actual_date + timedelta(days=MAX_FORECAST_DAYS) if last_actual_date else None
)


# ---------------------------------------------------------------------------
# Forecast access
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner="Running the crowd forecast…")
def forecast_table(end_iso: str) -> pd.DataFrame:
    """Recursive forecast from the last observed day through ``end_iso``.

    The forecast is recursive, so a distant month costs a few seconds on first
    request; the result is cached per end date thereafter.
    """
    return predictor.forecast_until(end_iso, events_df)


def forecast_map(end_day: date) -> dict[pd.Timestamp, dict]:
    """Forecast rows keyed by normalised timestamp, empty on any failure."""
    if last_actual_date is None or end_day <= last_actual_date:
        return {}
    if forecast_limit is not None and end_day > forecast_limit:
        end_day = forecast_limit
    try:
        table = forecast_table(end_day.isoformat())
    except Exception:
        # A model or feature failure must never take the dashboard down; the
        # affected cells simply render as "no data".
        return {}
    return {
        pd.Timestamp(row["date"]).normalize(): row.to_dict()
        for _, row in table.iterrows()
    }


@st.cache_data(show_spinner=False)
def wait_estimate_for(value: float) -> tuple[float, float] | None:
    """Historical median wait for the volume band ``value`` falls into."""
    try:
        return predictor._estimate_wait(float(value))
    except Exception:
        return None


def observed_wait_for(day: date) -> tuple[float, float] | None:
    """Recorded wait time for a past day, if the bulletin captured one."""
    rows = hist_df[hist_df["date"] == pd.Timestamp(day).normalize()]
    if rows.empty:
        return None
    row = rows.iloc[-1]
    for column in ("waiting_time_raw", "waiting_time"):
        if column in row.index:
            parsed = parse_wait_range(row[column])
            if parsed:
                return parsed
    return None


def events_for(day: date) -> list[dict]:
    """TTD calendar entries active on ``day``."""
    if events_df.empty:
        return []
    ts = pd.Timestamp(day).normalize()
    active = events_df[(events_df["start_date"] <= ts) & (events_df["end_date"] >= ts)]

    out: list[dict] = []
    for _, row in active.iterrows():
        name = row.get("calendar_label") or row.get("event_name") or "TTD event"
        out.append(
            {
                "name": str(name),
                "type": row.get("event_type"),
                "importance": row.get("importance"),
                "major": bool(row.get("major_event")),
                "start": row["start_date"].date(),
                "end": row["end_date"].date(),
            }
        )
    return out


def day_record(day: date, forecasts: dict[pd.Timestamp, dict] | None = None) -> dict:
    """Everything the UI needs about one day: value, provenance, band, wait.

    Observed data always wins over the model. When neither is available the
    record is marked unknown and the UI renders it as inert.
    """
    ts = pd.Timestamp(day).normalize()
    observed = actual_lookup.get(ts)

    if observed is not None:
        value, is_actual = float(observed), True
        wait = observed_wait_for(day) or wait_estimate_for(observed)
    else:
        row = (forecasts or {}).get(ts)
        if row is None:
            row = forecast_map(day).get(ts)
        if row is None:
            return {
                "date": day,
                "value": None,
                "is_actual": False,
                "known": False,
                "label": "No data",
                "fill": cl.UNKNOWN_FILL,
                "band": None,
                "wait": None,
                "events": events_for(day),
            }
        value, is_actual = float(row["prediction"]), False
        wait = coerce_wait(row.get("wait")) or wait_estimate_for(value)

    label, _, fill = cl.describe(value, thresholds)
    return {
        "date": day,
        "value": value,
        "is_actual": is_actual,
        "known": True,
        "label": label,
        "fill": fill,
        "band": cl.display_band(value),
        "wait": wait,
        "events": events_for(day),
    }


def month_records(anchor: date) -> dict[date, dict]:
    """Day records for every day of ``anchor``'s month, batching the forecast."""
    first, last = month_bounds(anchor)
    forecasts = forecast_map(last)
    return {
        d: day_record(d, forecasts)
        for d in pd.date_range(first, last).date
    }


# ---------------------------------------------------------------------------
# Context: which computed features are driving a given day
# ---------------------------------------------------------------------------

# (feature flag, chip label, tone). "hot" pushes crowds up, "cool" is neutral
# context. Labels are shown only when the underlying computed flag is set.
CONTEXT_FLAGS: tuple[tuple[str, str, str], ...] = (
    ("is_long_weekend", "Long weekend", "hot"),
    ("is_bridge_day", "Bridge day", "hot"),
    ("is_public_holiday", "Public holiday", "hot"),
    ("is_vaikunta_ekadashi", "Vaikunta Ekadashi", "hot"),
    ("is_rathasapthami", "Rathasapthami", "hot"),
    ("is_teppotsavam", "Teppotsavam", "hot"),
    ("is_brahmotsavam", "Brahmotsavam", "hot"),
    ("is_garuda_seva", "Garuda Seva", "hot"),
    ("is_pushpayagam", "Pushpayagam", "hot"),
    ("is_purattasi_saturday", "Purattasi Saturday", "hot"),
    ("is_ekadashi", "Ekadashi", "cool"),
    ("is_pournami", "Pournami", "cool"),
    ("is_amavasya", "Amavasya", "cool"),
    ("is_karthika_masam", "Karthika masam", "cool"),
    ("is_shravana_masam", "Shravana masam", "cool"),
    ("is_margashirsha_masam", "Margashirsha masam", "cool"),
    ("is_summer_vacation", "Summer vacation", "hot"),
    ("is_dasara_vacation", "Dasara vacation", "hot"),
    ("is_christmas_vacation", "Christmas vacation", "hot"),
    ("is_sankranti_vacation", "Sankranti vacation", "hot"),
    ("is_exam_season", "Exam season", "cool"),
)


@st.cache_data(show_spinner=False)
def context_chips(iso_day: str) -> list[tuple[str, str]]:
    """Build (label, tone) chips from the model's own computed feature row."""
    try:
        features = predictor._date_features(date.fromisoformat(iso_day))
    except Exception:
        return []

    chips: list[tuple[str, str]] = []

    # Day of week, taken from the computed calendar features.
    day_name = features.get("day_name")
    if day_name:
        weekend = bool(features.get("is_weekend"))
        chips.append((str(day_name), "hot" if weekend else "cool"))

    # Named holiday, when the holiday calendar supplies a name.
    holiday_name = features.get("holiday_name")
    if isinstance(holiday_name, str) and holiday_name.strip():
        chips.append((holiday_name.strip(), "hot"))

    for flag, label, tone in CONTEXT_FLAGS:
        value = features.get(flag)
        if value is None or pd.isna(value):
            continue
        # "Public holiday" is redundant once we have the holiday's actual name.
        if flag == "is_public_holiday" and any(
            tone_ == "hot" and label_ == str(holiday_name).strip()
            for label_, tone_ in chips
        ):
            continue
        if bool(value):
            chips.append((label, tone))

    season = features.get("season")
    if isinstance(season, str) and season.strip():
        chips.append((season.strip().title(), "cool"))

    # Preserve order while dropping duplicate labels.
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for label, tone in chips:
        if label.lower() in seen:
            continue
        seen.add(label.lower())
        unique.append((label, tone))
    return unique


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
today = date.today()
st.session_state.setdefault("cal_month", today.replace(day=1))
st.session_state.setdefault("selected_date", today)

view_month: date = st.session_state.cal_month
selected: date = st.session_state.selected_date


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
coverage = (
    f"observed data {actuals.index.min().date()} → {last_actual_date}"
    if last_actual_date
    else "no observed data available"
)
st.markdown(
    "<div class='tci-header'>"
    "<h1>Tirumala Crowd Predictor</h1>"
    f"<div class='tagline'>ML crowd forecasting for Tirumala · {coverage}</div>"
    "</div>",
    unsafe_allow_html=True,
)

main_left, main_right = st.columns([2.4, 1], gap="large")


# ---------------------------------------------------------------------------
# Shared renderers
# ---------------------------------------------------------------------------

def swatch_strip(active_index: int | None, size: int = 38) -> str:
    """The six-square crowd scale, lit up to ``active_index``."""
    cells = []
    for i, (_, _, fill) in enumerate(cl.BANDS):
        classes = ["legend-swatch"]
        if active_index is None or i > active_index:
            classes.append("dim")
        if active_index is not None and i == active_index:
            classes.append("active")
        cells.append(
            f"<div class='{' '.join(classes)}' "
            f"style='background:{fill};width:{size}px;height:{size}px;'></div>"
        )
    return f"<div class='legend-row'>{''.join(cells)}</div>"


def gradient_meter(value: float | None) -> str:
    """The gradient scale bar with a marker at ``value``'s position."""
    position = cl.scale_position(value, thresholds) * 100
    return (
        "<div class='meter'>"
        f"<div class='meter-bar' style='background:{cl.gradient_css()};'></div>"
        f"<div class='meter-marker' style='left:{position:.2f}%;'></div>"
        "</div>"
    )


# ===========================================================================
# LEFT COLUMN
# ===========================================================================
with main_left:
    # -----------------------------------------------------------------------
    # Latest observed bulletin + live crowd scale
    # -----------------------------------------------------------------------
    snapshot_date = snapshot.get("date", "n/a")
    st.markdown(
        f"<div class='section'>Latest data - {snapshot_date}</div>",
        unsafe_allow_html=True,
    )

    top_left, top_right = st.columns([1.35, 1], gap="medium")

    with top_left:
        # Distinguish a successful live scrape from the stored fallback so the
        # freshness of these numbers is never ambiguous.
        is_live = snapshot.get("source") == "live"
        status_class = "latest-status" if is_live else "latest-status is-fallback"
        status_text = (
            f"live scrape · {snapshot_date}"
            if is_live
            else f"stored bulletin · {snapshot_date}"
        )
        st.markdown(
            "<div class='latest-box'>"
            f"<div class='{status_class}'>last refreshed on {snapshot_date} "
            f"({status_text})</div>"
            f"<div class='latest-big'>{fmt(snapshot.get('pilgrims'))} pilgrims</div>"
            f"<div class='latest-big'>"
            f"{format_wait(parse_wait_range(snapshot.get('waiting_time')))}</div>"
            "<div class='latest-stats'>"
            f"<span>Tonsures: {fmt(snapshot.get('tonsures'))}</span>"
            f"<span>Hundi kanukalu: {fmt(snapshot.get('hundi'), ' CR', 2)}</span>"
            f"<span>Laddu sale… {fmt(snapshot.get('laddu'), ' Lac', 2)}</span>"
            f"<span>Annaprasadams… {fmt(snapshot.get('annaprasadam'), ' Lac', 2)}</span>"
            f"<span>Medical cases: {fmt(snapshot.get('medical'))}</span>"
            f"<span class='wide'>Waiting Compartments: "
            f"{snapshot.get('waiting_compartments') or '—'}</span>"
            "</div></div>",
            unsafe_allow_html=True,
        )

    with top_right:
        # The strip and its caption both read off the latest observed value,
        # so the label always matches the highlighted square.
        latest_value = snapshot.get("pilgrims")
        latest_label, _, latest_fill = cl.describe(latest_value, thresholds)
        latest_index = cl.level_index(latest_value, thresholds)

        rank_note = ""
        if latest_value is not None and not actuals.empty:
            # Where this day sits against all recorded history.
            percentile = float((actuals <= float(latest_value)).mean() * 100)
            rank_note = (
                f"busier than {percentile:.0f}% of the "
                f"{len(actuals):,} recorded days"
            )

        st.markdown(
            "<div style='margin-top:10px;'>"
            + swatch_strip(latest_index)
            + f"<div class='legend-caption' style='color:{latest_fill};'>"
            f"{latest_label}</div>"
            + (f"<div class='legend-sub'>{rank_note}</div>" if rank_note else "")
            + "</div>",
            unsafe_allow_html=True,
        )

    # -----------------------------------------------------------------------
    # Future crowd predictor: calendar + selected-day detail
    # -----------------------------------------------------------------------
    st.markdown(
        "<div class='section' style='margin-top:22px;'>Future crowd predictor:</div>",
        unsafe_allow_html=True,
    )

    cal_col, detail_col = st.columns([1.45, 1], gap="medium")

    with cal_col:
        nav_title, nav_prev, nav_today, nav_next = st.columns([1.7, 0.5, 0.95, 0.5])
        with nav_title:
            st.markdown(
                f"<div class='cal-month'>{view_month.strftime('%B %Y')}</div>",
                unsafe_allow_html=True,
            )
        with nav_prev:
            if st.button("◄", key="prev_month", width="stretch",
                         help="Previous month"):
                y, m = month_shift(view_month.year, view_month.month, -1)
                st.session_state.cal_month = date(y, m, 1)
                st.rerun()
        with nav_today:
            if st.button("Today", key="today_btn", width="stretch",
                         help="Jump back to the current month"):
                st.session_state.cal_month = today.replace(day=1)
                st.session_state.selected_date = today
                st.rerun()
        with nav_next:
            if st.button("►", key="next_month", width="stretch",
                         help="Next month"):
                y, m = month_shift(view_month.year, view_month.month, 1)
                st.session_state.cal_month = date(y, m, 1)
                st.rerun()

        st.markdown(
            "<div class='cal-weekdays'>"
            + "".join(
                f"<div class='cal-wk'>{name}</div>"
                for name in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
            )
            + "</div>",
            unsafe_allow_html=True,
        )

        # One batched forecast covers the whole visible month.
        records = month_records(view_month)

        for week_index, week in enumerate(
            pycalendar.monthcalendar(view_month.year, view_month.month)
        ):
            # Each week row lives in a keyed container so the stylesheet can
            # target the calendar's own column rows precisely. Without a marker
            # the only handle is :has(.cal-cell), which also matches the outer
            # page rows and would squeeze the whole layout on narrow screens.
            week_row = st.container(key=f"calweek-{week_index}")
            with week_row:
                cells = st.columns(7, gap="small")
            for position, day_number in enumerate(week):
                with cells[position]:
                    if day_number == 0:
                        st.markdown(
                            "<div class='cal-cell empty'></div>",
                            unsafe_allow_html=True,
                        )
                        continue

                    day = date(view_month.year, view_month.month, day_number)
                    record = records[day]

                    classes = ["cal-cell"]
                    if not record["known"]:
                        classes.append("muted")
                    if record["is_actual"]:
                        classes.append("actual")
                    if day == today:
                        classes.append("today")
                    if day == selected:
                        classes.append("cal-selected")

                    st.markdown(
                        f"<div class='{' '.join(classes)}' aria-hidden='true' "
                        f"style='background:{record['fill']};'>{day_number}</div>",
                        unsafe_allow_html=True,
                    )

                    # A transparent button is layered over the tile to capture
                    # the click; its tooltip carries the day's numbers.
                    if record["known"]:
                        origin = "observed" if record["is_actual"] else "forecast"
                        tip = (
                            f"{day:%d %b %Y} · {record['label']} · "
                            f"{record['value']:,.0f} pilgrims ({origin})"
                        )
                    else:
                        tip = f"{day:%d %b %Y} · no data available"

                    if st.button(
                        str(day_number),
                        key=f"cal_{day.isoformat()}",
                        width="stretch",
                        help=tip,
                    ):
                        st.session_state.selected_date = day
                        st.rerun()

        if forecast_limit is not None and month_bounds(view_month)[0] > forecast_limit:
            st.markdown(
                "<div class='panel'><div class='fest-name none'>"
                f"This month is beyond the {MAX_FORECAST_DAYS}-day forecast "
                f"horizon (which ends {forecast_limit:%d %b %Y}). The model "
                "would be extrapolating entirely from its own output, so no "
                "prediction is shown.</div></div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            "<div class='cal-legend'>"
            "<span>■ tick = observed data</span>"
            "<span>▫ dashed = today</span>"
            "<span>□ green = selected</span>"
            "</div>",
            unsafe_allow_html=True,
        )

    # -----------------------------------------------------------------------
    # Selected date detail
    # -----------------------------------------------------------------------
    selected_record = records.get(selected) or day_record(selected)

    with detail_col:
        origin_class = "actual" if selected_record["is_actual"] else "forecast"
        origin_text = "OBSERVED" if selected_record["is_actual"] else "PREDICTED"
        level_label = selected_record["label"]
        _, _, level_fill = cl.describe(selected_record["value"], thresholds)
        heading = "Recorded crowd level:" if selected_record["is_actual"] else "Predicted crowd level:"

        st.markdown(
            "<div class='panel'>"
            "<div class='panel-title'>Selected Date "
            f"<span class='origin-tag {origin_class}'>{origin_text}</span></div>"
            "<div class='detail-head'>"
            "<div class='date-box'>"
            f"<div class='day-name'>{selected:%A}</div>"
            f"<div class='day-num'>{ordinal(selected.day)}</div>"
            f"<div class='month-yr'>{selected:%B %Y}</div>"
            "</div>"
            "<div style='flex:1;'>"
            + gradient_meter(selected_record["value"])
            + f"<div style='font-size:var(--t-xs);color:var(--muted);'>{heading}</div>"
            f"<div class='level-headline' style='color:{level_fill};'>"
            f"{level_label}</div>"
            "</div></div>"
            "<div class='info-label'>Expected pilgrims</div>"
            f"<div class='info-value'>{cl.band_text(selected_record['band'])}</div>"
            f"<div class='info-note'>point estimate "
            f"{fmt(selected_record['value'])}</div>"
            "<div class='info-label'>Expected waiting time in ticketless<br>"
            "free darshan</div>"
            f"<div class='info-value'>{format_wait(selected_record['wait'])}</div>"
            "</div>",
            unsafe_allow_html=True,
        )

        # Why this day looks the way it does — read from the computed features.
        chips = context_chips(selected.isoformat())
        if chips:
            st.markdown(
                "<div class='panel'>"
                "<div class='panel-title'>Why this day</div>"
                "<div class='chip-row'>"
                + "".join(
                    f"<span class='chip {tone}'>{label}</span>"
                    for label, tone in chips
                )
                + "</div></div>",
                unsafe_allow_html=True,
            )

    # -----------------------------------------------------------------------
    # Festivals on the selected day
    # -----------------------------------------------------------------------
    events_today = selected_record["events"]
    festival_html = [
        "<div class='panel'>",
        "<div class='panel-title'>□ Utsavams/Festivals this day:</div>",
    ]
    if events_today:
        for event in events_today:
            span = (
                f"{event['start']:%d %b} – {event['end']:%d %b %Y}"
                if event["start"] != event["end"]
                else f"{event['start']:%d %b %Y}"
            )
            detail = " · ".join(
                str(part)
                for part in (event["type"], f"importance {event['importance']}", span)
                if part not in (None, "", "nan")
            )
            marker = " ★" if event["major"] else ""
            festival_html.append(
                f"<div class='fest-name'>{event['name']}{marker}</div>"
                f"<div class='fest-meta'>{detail}</div>"
            )
    else:
        festival_html.append(
            "<div class='fest-name none'>No scheduled events</div>"
        )
    festival_html.append(
        f"<div class='fest-date'>{selected:%d-%m-%Y}</div></div>"
    )
    st.markdown("".join(festival_html), unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Analysis tabs: trend, quiet days, month summary, data provenance
    # -----------------------------------------------------------------------
    trend_tab, quiet_tab, summary_tab, data_tab = st.tabs(
        ["Trend & forecast", "Best days to visit", "Month summary", "Data & model"]
    )

    with trend_tab:
        # Trailing observed history joined to the forecast for the visible
        # month, so the handover between the two is visible.
        month_end = month_bounds(view_month)[1]
        history_tail = actuals.tail(TREND_HISTORY_DAYS)

        figure = go.Figure()
        if not history_tail.empty:
            figure.add_trace(
                go.Scatter(
                    x=list(history_tail.index),
                    y=[float(v) for v in history_tail.values],
                    name="Observed",
                    mode="lines",
                    line=dict(color="#00ff41", width=2),
                    hovertemplate="%{x|%d %b %Y}<br>%{y:,.0f} pilgrims<extra>Observed</extra>",
                )
            )

        horizon = forecast_map(month_end)
        if horizon:
            ordered = sorted(horizon.items())
            figure.add_trace(
                go.Scatter(
                    x=[ts for ts, _ in ordered],
                    y=[float(row["prediction"]) for _, row in ordered],
                    name="Forecast",
                    mode="lines",
                    line=dict(color="#ed7d32", width=2, dash="dot"),
                    hovertemplate="%{x|%d %b %Y}<br>%{y:,.0f} pilgrims<extra>Forecast</extra>",
                )
            )

        if figure.data:
            # Zoom to the plotted values (with a little headroom) rather than
            # letting the axis run from zero and flatten the series.
            plotted = [y for trace in figure.data for y in trace.y]
            span = max(plotted) - min(plotted) or 1.0
            plot_range = [min(plotted) - span * 0.15, max(plotted) + span * 0.15]

            # Shade the crowd bands behind the series so the lines can be read
            # against the same scale used everywhere else in the dashboard.
            edges = [
                min(plot_range[0], thresholds[0] - 1),
                *thresholds,
                max(plot_range[1], thresholds[-1] + 1),
            ]
            for i, (_, _, fill) in enumerate(cl.BANDS):
                figure.add_hrect(
                    y0=edges[i], y1=edges[i + 1],
                    fillcolor=fill, opacity=0.10, line_width=0, layer="below",
                )
            figure.update_layout(
                height=320,
                margin=dict(l=8, r=8, t=28, b=8),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="VT323, monospace", size=15, color="#8b9a90"),
                legend=dict(orientation="h", y=1.16, x=0, bgcolor="rgba(0,0,0,0)"),
                hovermode="x unified",
                yaxis=dict(
                    title="Pilgrims / day",
                    gridcolor="rgba(255,255,255,0.06)",
                    zeroline=False,
                    range=plot_range,
                ),
                xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
            )
            figure.add_vline(
                x=pd.Timestamp(selected),
                line=dict(color="#00e5ff", width=1, dash="dash"),
            )
            st.plotly_chart(figure, width="stretch",
                            config={"displayModeBar": False})
        else:
            st.markdown(
                "<div class='fest-name none'>No series available to plot.</div>",
                unsafe_allow_html=True,
            )

    with quiet_tab:
        # Rank the visible month's days from quietest upward, skipping days
        # already in the past relative to today.
        candidates = [
            record
            for day, record in sorted(records.items())
            if record["known"] and day >= today
        ]
        candidates.sort(key=lambda r: r["value"])

        if candidates:
            st.markdown(
                f"<div class='panel-title'>Quietest upcoming days in "
                f"{view_month:%B %Y}</div>",
                unsafe_allow_html=True,
            )
            rows = []
            for record in candidates[:QUIET_DAY_COUNT]:
                rows.append(
                    "<div class='rank-row'>"
                    f"<div class='rank-chip' style='background:{record['fill']};'></div>"
                    f"<div class='rank-day'>{record['date']:%a %d %b}</div>"
                    f"<div>{record['label']}</div>"
                    f"<div class='rank-val'>{record['value']:,.0f} · "
                    f"{format_wait(record['wait'])}</div>"
                    "</div>"
                )
            st.markdown("".join(rows), unsafe_allow_html=True)
        else:
            st.markdown(
                "<div class='fest-name none'>No upcoming days with data in this "
                "month. Use ► to look further ahead.</div>",
                unsafe_allow_html=True,
            )

    with summary_tab:
        known = [r for r in records.values() if r["known"]]
        if known:
            values = [r["value"] for r in known]
            busiest = max(known, key=lambda r: r["value"])
            quietest = min(known, key=lambda r: r["value"])
            observed_count = sum(1 for r in known if r["is_actual"])
            event_days = sum(1 for r in known if r["events"])

            a, b, c = st.columns(3)
            a.markdown(
                "<div class='panel'><div class='info-label'>Average / day</div>"
                f"<div class='info-value'>{sum(values) / len(values):,.0f}</div>"
                f"<div class='info-note'>{len(known)} days · {observed_count} observed, "
                f"{len(known) - observed_count} forecast</div></div>",
                unsafe_allow_html=True,
            )
            b.markdown(
                "<div class='panel'><div class='info-label'>Busiest day</div>"
                f"<div class='info-value'>{busiest['date']:%d %b}</div>"
                f"<div class='info-note'>{busiest['value']:,.0f} · "
                f"{busiest['label']}</div></div>",
                unsafe_allow_html=True,
            )
            c.markdown(
                "<div class='panel'><div class='info-label'>Quietest day</div>"
                f"<div class='info-value'>{quietest['date']:%d %b}</div>"
                f"<div class='info-note'>{quietest['value']:,.0f} · "
                f"{quietest['label']}</div></div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div class='legend-sub'>{event_days} day(s) this month carry a "
                "TTD calendar entry.</div>",
                unsafe_allow_html=True,
            )

            # Let the user take the month's numbers away with them.
            export = pd.DataFrame(
                [
                    {
                        "date": r["date"].isoformat(),
                        "day": f"{r['date']:%A}",
                        "pilgrims": round(r["value"]),
                        "crowd_level": r["label"],
                        "source": "observed" if r["is_actual"] else "forecast",
                        "expected_wait_hours": format_wait(r["wait"]),
                        "events": " | ".join(e["name"] for e in r["events"]),
                    }
                    for r in sorted(known, key=lambda r: r["date"])
                ]
            )
            st.download_button(
                f"Download {view_month:%B %Y} forecast (CSV)",
                data=export.to_csv(index=False).encode("utf-8"),
                file_name=f"tirumala_crowd_{view_month:%Y_%m}.csv",
                mime="text/csv",
            )
        else:
            st.markdown(
                "<div class='fest-name none'>No data for this month.</div>",
                unsafe_allow_html=True,
            )

    with data_tab:
        model_path = Path(predictor.MODEL_PATH) if hasattr(predictor, "MODEL_PATH") else None
        ladder = " · ".join(f"{t:,.0f}" for t in thresholds)
        st.markdown(
            "<div class='panel'>"
            "<div class='panel-title'>Where these numbers come from</div>"
            f"<p style='font-size:var(--t-xs);color:var(--muted);line-height:1.5;'>"
            f"Observed history: <b>{len(actuals):,}</b> days "
            f"({actuals.index.min().date()} → {last_actual_date}).<br>"
            f"TTD calendar entries loaded: <b>{len(events_df):,}</b>"
            + (
                f" ({events_df['start_date'].min().date()} → "
                f"{events_df['end_date'].max().date()})"
                if not events_df.empty
                else ""
            )
            + "<br>"
            f"Latest bulletin source: <b>{snapshot.get('source', 'unknown')}</b><br>"
            f"Forecast horizon: up to <b>{forecast_limit}</b> "
            f"({MAX_FORECAST_DAYS} days past the last observed day).<br>"
            f"Crowd-band cut points, recomputed from the observed distribution "
            f"at the {'/'.join(f'{q:.0%}' for q in cl.QUANTILE_CUTS)} percentiles: "
            f"<b>{ladder}</b>."
            + (f"<br>Model file: <b>{model_path.name}</b>" if model_path else "")
            + "</p></div>",
            unsafe_allow_html=True,
        )


# ===========================================================================
# RIGHT COLUMN: artwork + disclaimer
# ===========================================================================
with main_right:
    st.markdown(
        f"<div class='deity-wrap'>{pixel_art.render_svg()}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='disclaimer-box'>"
        "<h3>⚠ DISCLAIMER</h3>"
        "<p>This is an independent and unofficial project created for "
        "informational and planning purposes. It is not affiliated with, "
        "associated with, or endorsed by Tirumala Tirupati Devasthanams (TTD) "
        "and does not represent official TTD information or advisories.</p>"
        "</div>",
        unsafe_allow_html=True,
    )


# ===========================================================================
# FULL WIDTH: forecast disclaimer
# ===========================================================================
st.markdown(
    "<div class='forecast-disclaimer'>"
    "<h3>Forecast Disclaimer:</h3>"
    "<p>Crowd levels are predicted using Machine Learning (ML) models based on "
    "available historical and contextual data. Predictions are estimates and "
    "cannot guarantee actual crowd conditions. Real-world conditions may vary "
    "due to unforeseen events, operational changes, weather, festivals, and "
    "other factors.</p>"
    "<p>Please use these predictions only as a planning reference. The "
    "developers are not responsible for any loss, injury, delay, "
    "inconvenience, or other consequences resulting from reliance on the "
    "information provided.</p>"
    "</div>",
    unsafe_allow_html=True,
)
