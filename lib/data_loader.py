"""Data loading with Streamlit caching. Historical CSVs use @st.cache_data;
the model uses @st.cache_resource (in predictor.py)."""
from __future__ import annotations

import os
from datetime import date

import pandas as pd
import streamlit as st

from . import scraper

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

MERGED_CSV = os.path.join(DATA_DIR, "merged.csv")
RAW_SCRAPE_CSV = os.path.join(DATA_DIR, "raw_ttd_scrape.csv")
EVENTS_CSV = os.path.join(DATA_DIR, "ttd_tirumala_events_2026_2027.csv")

OPERATIONAL_FIELDS = [
    ("pilgrims", "Pilgrims (darshan)"),
    ("waiting_time", "Approx. Sarva Darshan wait"),
    ("waiting_compartments", "Waiting compartments"),
    ("tonsures", "Tonsures"),
    ("hundi", "Hundi kanukalu (Cr)"),
    ("laddu", "Laddu sales (Lakh)"),
    ("annaprasadam", "Annaprasadam (Lakh)"),
    ("medical", "Medical cases treated"),
]


def _to_number(raw):
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    import re
    cleaned = re.sub(r"[,\s]", "", str(raw))
    try:
        return float(cleaned)
    except ValueError:
        return None


@st.cache_data(show_spinner=False)
def load_merged_history() -> pd.DataFrame:
    """Historical crowd dataset (merged.csv) -- used for the trend chart and
    as one source of past-actual pilgrim counts for lag features."""
    df = pd.read_csv(MERGED_CSV)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    df["pilgrims"] = df["pilgrims_raw"].apply(_to_number)
    return df


@st.cache_data(show_spinner=False)
def load_raw_scrape() -> pd.DataFrame:
    """Latest TTD operational scrape data (raw_ttd_scrape.csv)."""
    df = pd.read_csv(RAW_SCRAPE_CSV)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    df["pilgrims"] = df["pilgrims_raw"].apply(_to_number)
    return df


@st.cache_data(show_spinner=False)
def load_events() -> pd.DataFrame:
    """Official TTD Divya Utsavam calendar (future Tirumala events only)."""
    df = pd.read_csv(EVENTS_CSV)
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce").dt.normalize()
    df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce").dt.normalize()
    return df.dropna(subset=["start_date", "end_date"]).reset_index(drop=True)


def build_actuals_series() -> pd.Series:
    """Unified, deduplicated series of known real pilgrim counts, indexed
    by normalized Timestamp date. raw_ttd_scrape.csv is preferred where it
    overlaps merged.csv since it is the more recently scraped source."""
    merged = load_merged_history()[["date", "pilgrims"]].dropna()
    raw = load_raw_scrape()[["date", "pilgrims"]].dropna()
    combined = pd.concat([merged, raw]).drop_duplicates(subset="date", keep="last")
    return combined.set_index("date")["pilgrims"].sort_index()


@st.cache_data(show_spinner=False, ttl=1800)
def get_latest_snapshot() -> dict:
    """
    Latest available TTD operational snapshot. Tries a live HTTPS scrape
    first; on ANY failure, falls back to the last known-good row in
    raw_ttd_scrape.csv rather than crashing the app.
    """
    live = None
    try:
        live = scraper.fetch_latest(lookback_days=5)
    except Exception:
        live = None

    if live is not None and live.pilgrims_raw:
        return {
            "date": live.date,
            "pilgrims": _to_number(live.pilgrims_raw),
            "waiting_time": live.waiting_time_raw,
            "waiting_compartments": live.waiting_compartments_raw,
            "tonsures": _to_number(live.tonsures_raw),
            "hundi": _to_number(live.hundi_raw),
            "laddu": _to_number(live.laddu_raw),
            "annaprasadam": _to_number(live.annaprasadam_raw),
            "medical": _to_number(live.medical_raw),
            "source": "live",
            "source_url": live.source_url,
        }

    # Fallback: most recent successfully-scraped row on disk.
    raw = load_raw_scrape()
    ok = raw[raw["pilgrims"].notna()].sort_values("date")
    if ok.empty:
        return {"source": "unavailable"}
    last = ok.iloc[-1]
    return {
        "date": last["date"].strftime("%Y-%m-%d"),
        "pilgrims": last["pilgrims"],
        "waiting_time": last.get("waiting_time_raw"),
        "waiting_compartments": last.get("waiting_compartments_raw"),
        "tonsures": _to_number(last.get("tonsures_raw")),
        "hundi": _to_number(last.get("hundi_raw")),
        "laddu": _to_number(last.get("laddu_raw")),
        "annaprasadam": _to_number(last.get("annaprasadam_raw")),
        "medical": _to_number(last.get("medical_raw")),
        "source": "stored_fallback",
        "source_url": last.get("source_url"),
    }


def events_on_or_near(target: date, window_days: int = 0) -> pd.DataFrame:
    events = load_events()
    ts = pd.Timestamp(target)
    lo = ts - pd.Timedelta(days=window_days)
    hi = ts + pd.Timedelta(days=window_days)
    return events[(events["start_date"] <= hi) & (events["end_date"] >= lo)]
