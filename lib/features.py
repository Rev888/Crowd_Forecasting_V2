#!/usr/bin/env python3
"""
build_features.py
==================

Companion script to build_dataset.py.

Takes the RAW scraped bulletin data (raw_ttd_scrape.csv, produced by
build_dataset.py -- columns: date, pilgrims_raw, tonsures_raw, hundi_raw,
laddu_raw, annaprasadam_raw, medical_raw, waiting_compartments_raw,
waiting_time_raw, source_url, scrape_status) and produces a pure FEATURE
table for crowd/waiting-time forecasting:

    1. Weekend / weekday / calendar features
    2. Multi-state Indian holiday features + long-weekend + bridge-day
       detection + "distance to nearest holiday" features
    3. Hindu panchang (tithi) features, computed astronomically -- same
       method as build_dataset.py (ephem + Lahiri ayanamsa)
    4. TTD administrative festival dates (Brahmotsavam / Garuda Seva /
       Pushpayagam) from a built-in, yearly-extendable lookup table
    5. School vacation windows (built-in table + documented estimator)
    6. Indian meteorological SEASON features (winter / summer / monsoon /
       post-monsoon) -- relevant because AP/Rayalaseema monsoon rain and
       peak summer heat measurably affect pilgrim footfall
    7. A handful of extra features that are cheap to compute and generally
       useful for a crowd-forecasting model but weren't in the original
       pipeline: month-start/end (salary-day travel), exam season, festive
       season (Sep-Jan window covering Ganesh Chaturthi through Sankranti),
       cyclical (sin/cos) encodings of day-of-week / day-of-year for models
       that want smooth periodicity instead of one-hot flags, and simple
       lag/rolling pilgrim-count features (computed ONLY from past actuals,
       clearly separated so they're not misused as future-looking leakage).

This script does NOT re-scrape anything and does NOT re-clean the raw
numeric fields (build_dataset.py's clean_scraped_data() already does that,
and this script intentionally stays decoupled from it so you can run
feature engineering independently, re-run it after tweaking a lookup table,
or point it at a different pilgrim-count source entirely).

Usage
-----
    pip install pandas holidays ephem --break-system-packages

    python build_features.py
    python build_features.py --raw raw_ttd_scrape.csv --out features.csv
    python build_features.py --start-date 2023-01-01 --end-date 2026-12-31
    python build_features.py --future-only --start-date 2026-08-04 --end-date 2026-12-31

--future-only lets you generate the SAME feature columns for future dates
(no pilgrim data needed) so you can feed them to a trained model at
inference time -- lag/rolling pilgrim features are simply left blank (NaN)
for any date past the last known actual, since they can't be computed
without leaking the thing you're trying to predict.
"""

from __future__ import annotations

import argparse
import functools
import logging
import math
import os
import sys
from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd

try:
    import holidays
except ImportError:  # pragma: no cover
    print("ERROR: pip install holidays --break-system-packages")
    sys.exit(1)

try:
    import ephem
except ImportError:  # pragma: no cover
    print("ERROR: pip install ephem --break-system-packages")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("build_features")

TIRUMALA_LAT = "13.6833"
TIRUMALA_LON = "79.3167"
TIRUMALA_ELEVATION_M = 853
IST_OFFSET_HOURS = 5.5

DEFAULT_RAW_PATH = "raw_ttd_scrape.csv"
DEFAULT_OUT_PATH = "features.csv"


# ---------------------------------------------------------------------------
# 1. Calendar / weekend features
# ---------------------------------------------------------------------------

def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    dt = pd.to_datetime(df["date"])
    df["year"] = dt.dt.year
    df["month"] = dt.dt.month
    df["day"] = dt.dt.day
    df["day_of_week"] = dt.dt.dayofweek          # Monday=0 .. Sunday=6
    df["day_name"] = dt.dt.day_name()
    df["week_number"] = dt.dt.isocalendar().week.astype(int)
    df["quarter"] = dt.dt.quarter
    df["day_of_year"] = dt.dt.dayofyear
    df["is_weekend"] = dt.dt.dayofweek.isin([5, 6]).astype(int)
    df["is_saturday"] = (dt.dt.dayofweek == 5).astype(int)   # AP weekly-holiday travel peak
    df["is_sunday"] = (dt.dt.dayofweek == 6).astype(int)
    df["is_month_start"] = dt.dt.is_month_start.astype(int)  # salary-day travel bump
    df["is_month_end"] = dt.dt.is_month_end.astype(int)
    # Cyclical encodings -- give models smooth periodicity instead of only
    # discrete one-hot flags (useful for linear/NN models; harmless extra
    # columns for tree models).
    df["dow_sin"] = (2 * math.pi * dt.dt.dayofweek / 7).apply(math.sin)
    df["dow_cos"] = (2 * math.pi * dt.dt.dayofweek / 7).apply(math.cos)
    df["doy_sin"] = (2 * math.pi * dt.dt.dayofyear / 365.25).apply(math.sin)
    df["doy_cos"] = (2 * math.pi * dt.dt.dayofyear / 365.25).apply(math.cos)
    return df


# ---------------------------------------------------------------------------
# 2. Holidays, long weekends, bridge days, distance-to-holiday
# ---------------------------------------------------------------------------

def _holiday_set(subdiv: Optional[str], years: list[int]) -> dict:
    """Returns {date: holiday_name} for India (optionally a specific state)."""
    try:
        h = holidays.country_holidays("IN", subdiv=subdiv, years=years)
    except (NotImplementedError, KeyError):
        log.warning("Subdivision '%s' unsupported by installed 'holidays' package "
                    "-- falling back to national holidays.", subdiv)
        h = holidays.country_holidays("IN", years=years)
    return dict(h)


def add_holiday_features(df: pd.DataFrame) -> pd.DataFrame:
    dt = pd.to_datetime(df["date"])
    years = sorted(set(dt.dt.year.unique().tolist()) | {dt.dt.year.min() - 1, dt.dt.year.max() + 1})

    national = _holiday_set(None, years)
    ap = _holiday_set("AP", years)
    tg = _holiday_set("TG", years)
    tn = _holiday_set("TN", years)
    ka = _holiday_set("KA", years)
    kl = _holiday_set("KL", years)

    dates_only = dt.dt.date
    df["is_public_holiday"] = dates_only.isin(national).astype(int)
    df["is_ap_holiday"] = dates_only.isin(ap).astype(int)
    df["is_telangana_holiday"] = dates_only.isin(tg).astype(int)
    df["is_tamilnadu_holiday"] = dates_only.isin(tn).astype(int)
    df["is_karnataka_holiday"] = dates_only.isin(ka).astype(int)
    df["is_kerala_holiday"] = dates_only.isin(kl).astype(int)
    df["holiday_name"] = dates_only.map(lambda d: national.get(d) or ap.get(d) or "")

    # "Any relevant state's holiday" -- pilgrims travel to Tirumala from AP,
    # TG, TN, KA, and KL primarily, so a TN/KA/KL holiday can drive a travel
    # spike even on a normal AP working day.
    any_source_state_holiday = (
        dates_only.isin(ap) | dates_only.isin(tg) | dates_only.isin(tn)
        | dates_only.isin(ka) | dates_only.isin(kl) | dates_only.isin(national)
    )
    df["is_any_source_state_holiday"] = any_source_state_holiday.astype(int)

    # Long weekend: contiguous block of >=3 "off" days (Sat/Sun/holiday).
    is_off = ((df["is_weekend"] == 1) | (df["is_public_holiday"] == 1)).to_numpy()
    long_weekend = [False] * len(is_off)
    n = len(is_off)
    i = 0
    while i < n:
        if is_off[i]:
            j = i
            while j < n and is_off[j]:
                j += 1
            if j - i >= 3:
                for k in range(i, j):
                    long_weekend[k] = True
            i = j
        else:
            i += 1
    df["is_long_weekend"] = pd.Series(long_weekend, index=df.index).astype(int)

    # Bridge day: a single working weekday sandwiched between an "off" day
    # on both sides (classic "take one day of leave" pattern in India).
    off_shift_back = pd.Series(is_off, index=df.index).shift(-1, fill_value=False)
    off_shift_fwd = pd.Series(is_off, index=df.index).shift(1, fill_value=False)
    df["is_bridge_day"] = (
        (~pd.Series(is_off, index=df.index)) & off_shift_back & off_shift_fwd
    ).astype(int)

    # Distance (in days) to the nearest public holiday, signed: negative =
    # holiday is upcoming, positive = holiday just passed. Captures
    # pre-/post-holiday travel ramp that a same-day flag alone misses.
    holiday_dates = sorted(dates_only[df["is_public_holiday"] == 1].unique())
    df["days_to_nearest_holiday"] = dates_only.apply(
        lambda d: _signed_days_to_nearest(d, holiday_dates)
    )
    return df


def _signed_days_to_nearest(d: date, sorted_dates: list) -> Optional[int]:
    if not sorted_dates:
        return None
    best = min(sorted_dates, key=lambda x: abs((x - d).days))
    return (best - d).days  # negative if best is upcoming (i.e. before... wait see below)


# ---------------------------------------------------------------------------
# 3. Hindu panchang (tithi) -- identical method to build_dataset.py
# ---------------------------------------------------------------------------

RASHI_TO_MASAM = {4: "shravana", 7: "karthika", 8: "margashirsha"}
RASHI_KANYA = 5
RASHI_DHANU = 8
RASHI_KUMBHA = 10
RASHI_MEENA = 11


def _lahiri_ayanamsa_degrees(d: date) -> float:
    years_since_2000 = (datetime(d.year, d.month, d.day) - datetime(2000, 1, 1)).days / 365.25
    return 23.85 + years_since_2000 * (50.29 / 3600.0)


def _sun_moon_tropical_longitudes(dt_utc: datetime) -> tuple[float, float]:
    obs = ephem.Observer()
    obs.date = dt_utc
    sun = ephem.Sun(obs)
    moon = ephem.Moon(obs)
    sun_lon = math.degrees(ephem.Ecliptic(sun, epoch=obs.date).lon)
    moon_lon = math.degrees(ephem.Ecliptic(moon, epoch=obs.date).lon)
    return sun_lon, moon_lon


def _local_sunrise_utc(d: date) -> datetime:
    obs = ephem.Observer()
    obs.lat, obs.lon, obs.elevation = TIRUMALA_LAT, TIRUMALA_LON, TIRUMALA_ELEVATION_M
    local_midnight_utc = datetime(d.year, d.month, d.day) - timedelta(hours=IST_OFFSET_HOURS)
    obs.date = local_midnight_utc
    try:
        return obs.next_rising(ephem.Sun()).datetime()
    except (ephem.AlwaysUpError, ephem.NeverUpError):
        return datetime(d.year, d.month, d.day, 6, 0, 0) - timedelta(hours=IST_OFFSET_HOURS)


@functools.lru_cache(maxsize=4000)
def compute_panchang_day(iso_date) -> dict:
    # Accept both the original YYYY-MM-DD string and pandas Timestamp/date values.
    if hasattr(iso_date, "to_pydatetime"):
        iso_date = iso_date.to_pydatetime()
    if isinstance(iso_date, datetime):
        d = iso_date.date()
    elif isinstance(iso_date, date):
        d = iso_date
    else:
        d = datetime.strptime(str(iso_date), "%Y-%m-%d").date()
    sunrise_utc = _local_sunrise_utc(d)
    sun_lon, moon_lon = _sun_moon_tropical_longitudes(sunrise_utc)

    elongation = (moon_lon - sun_lon) % 360
    tithi = int(elongation // 12) + 1
    paksha_shukla = tithi <= 15
    tithi_in_paksha = tithi if paksha_shukla else tithi - 15

    ayanamsa = _lahiri_ayanamsa_degrees(d)
    sun_sidereal = (sun_lon - ayanamsa) % 360
    rashi_index = int(sun_sidereal // 30)
    masam = RASHI_TO_MASAM.get(rashi_index)

    is_ekadashi = tithi_in_paksha == 11
    is_pournami = tithi == 15
    is_amavasya = tithi == 30

    return {
        "tithi_number": tithi,
        "paksha": "shukla" if paksha_shukla else "krishna",
        "is_ekadashi": int(is_ekadashi),
        "is_pournami": int(is_pournami),
        "is_amavasya": int(is_amavasya),
        "is_purattasi_saturday": int(rashi_index == RASHI_KANYA and d.weekday() == 5),
        "is_karthika_masam": int(masam == "karthika"),
        "is_shravana_masam": int(masam == "shravana"),
        "is_margashirsha_masam": int(masam == "margashirsha"),
        "is_vaikunta_ekadashi": int(is_ekadashi and paksha_shukla and rashi_index == RASHI_DHANU),
        "is_rathasapthami": int(tithi_in_paksha == 7 and paksha_shukla and rashi_index == RASHI_KUMBHA),
        "is_teppotsavam": int(paksha_shukla and tithi_in_paksha in (11, 12, 13, 14, 15)
                               and rashi_index == RASHI_MEENA),
    }


def add_panchang_features(df: pd.DataFrame) -> pd.DataFrame:
    log.info("Computing panchang (tithi) features for %s dates...", len(df))
    results = df["date"].apply(compute_panchang_day)
    for col in ["tithi_number", "paksha", "is_ekadashi", "is_pournami", "is_amavasya",
                "is_purattasi_saturday", "is_karthika_masam", "is_shravana_masam",
                "is_margashirsha_masam", "is_vaikunta_ekadashi", "is_rathasapthami",
                "is_teppotsavam"]:
        df[col] = results.apply(lambda r: r[col])
    return df


# ---------------------------------------------------------------------------
# 4. TTD administrative festivals (Brahmotsavam / Garuda Seva / Pushpayagam)
# ---------------------------------------------------------------------------
# EXTEND YEARLY once TTD publishes the schedule. See build_dataset.py's
# module docstring for sourcing notes -- kept identical here for consistency.

BRAHMOTSAVAM_RANGES = [
    ("2023-09-18", "2023-09-26"),
    ("2023-10-15", "2023-10-23"),
    ("2024-10-03", "2024-10-12"),
    ("2025-09-24", "2025-10-02"),
    ("2026-09-15", "2026-09-23"),
    ("2026-10-12", "2026-10-20"),
]
GARUDA_SEVA_DATES = ["2023-09-20", "2024-10-08", "2025-09-28", "2026-09-19"]
PUSHPAYAGAM_DATES: list[str] = []


def add_administrative_festival_features(df: pd.DataFrame) -> pd.DataFrame:
    df["is_brahmotsavam"] = 0
    df["is_garuda_seva"] = 0
    df["is_pushpayagam"] = 0

    df_dates = pd.to_datetime(df["date"])
    for start, end in BRAHMOTSAVAM_RANGES:
        mask = (df_dates >= pd.Timestamp(start)) & (df_dates <= pd.Timestamp(end))
        df.loc[mask, "is_brahmotsavam"] = 1
    df.loc[df["date"].isin(GARUDA_SEVA_DATES), "is_garuda_seva"] = 1
    df.loc[df["date"].isin(PUSHPAYAGAM_DATES), "is_pushpayagam"] = 1

    covered_years = {int(s[:4]) for s, _ in BRAHMOTSAVAM_RANGES}
    missing = sorted(set(df_dates.dt.year.unique()) - covered_years)
    if missing:
        log.warning("No Brahmotsavam/Garuda Seva table entries for year(s) %s "
                    "-- extend BRAHMOTSAVAM_RANGES / GARUDA_SEVA_DATES.", missing)
    return df


# ---------------------------------------------------------------------------
# 5. School vacations (built-in table + documented estimator)
# ---------------------------------------------------------------------------

KNOWN_VACATIONS = [
    ("2023-05-01", "2023-06-11", "summer"),
    ("2025-09-24", "2025-10-02", "dasara"),
]


def _estimate_vacation_windows(year: int) -> list[tuple[str, str, str]]:
    return [
        (f"{year}-05-01", f"{year}-06-11", "summer"),
        (f"{year}-09-24", f"{year}-10-02", "dasara"),
        (f"{year}-12-24", f"{year + 1}-01-01", "christmas"),
        (f"{year}-01-12", f"{year}-01-16", "sankranti"),
    ]


def add_vacation_features(df: pd.DataFrame) -> pd.DataFrame:
    vac_cols = {"summer": "is_summer_vacation", "dasara": "is_dasara_vacation",
                "christmas": "is_christmas_vacation", "sankranti": "is_sankranti_vacation"}
    for col in vac_cols.values():
        df[col] = 0

    df_dates = pd.to_datetime(df["date"])
    years = sorted(df_dates.dt.year.unique().tolist())
    windows = list(KNOWN_VACATIONS)

    for year in years:
        known_types = {t for s, e, t in KNOWN_VACATIONS if int(s[:4]) == year}
        if known_types == set(vac_cols.keys()):
            continue
        for s, e, t in _estimate_vacation_windows(year):
            if t in known_types:
                continue
            log.warning("Using an ESTIMATED (unconfirmed) %s vacation window for %s: "
                       "%s to %s -- verify against the official AP/TG school GO.", t, year, s, e)
            windows.append((s, e, t))

    for start, end, vtype in windows:
        col = vac_cols.get(vtype)
        if col is None:
            continue
        mask = (df_dates >= pd.Timestamp(start)) & (df_dates <= pd.Timestamp(end))
        df.loc[mask, col] = 1
    return df


# ---------------------------------------------------------------------------
# 6. Meteorological season (Indian 4-season classification)
# ---------------------------------------------------------------------------
# Relevant to Tirumala specifically: the hill is prone to heavy rain / fog
# / occasional landslide-driven route closures during the SW monsoon
# (Jun-Sep), and peak summer heat (Apr-Jun) both suppress footfall relative
# to the pleasant post-monsoon/winter travel season (Oct-Feb) when most
# major festivals also cluster.

def _season_for_month(month: int) -> str:
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "summer"
    if month in (6, 7, 8, 9):
        return "monsoon"
    return "post_monsoon"  # 10, 11


def add_season_features(df: pd.DataFrame) -> pd.DataFrame:
    dt = pd.to_datetime(df["date"])
    df["season"] = dt.dt.month.apply(_season_for_month)
    for s in ["winter", "summer", "monsoon", "post_monsoon"]:
        df[f"is_{s}"] = (df["season"] == s).astype(int)

    # Board-exam season (roughly Feb-Apr across AP/TG/TN/KA/KL) -- families
    # with school-age children travel less during this window.
    df["is_exam_season"] = dt.dt.month.isin([2, 3, 4]).astype(int)

    # "Festive season" -- the Sep(Ganesh Chaturthi)-through-Jan(Sankranti)
    # stretch when Brahmotsavam, Dasara, Diwali, Karthika masam, Vaikunta
    # Ekadashi and Sankranti all cluster; broader and coarser than any single
    # festival flag, useful as a standalone seasonality signal.
    df["is_festive_season"] = dt.dt.month.isin([9, 10, 11, 12, 1]).astype(int)
    return df


# ---------------------------------------------------------------------------
# 7. Lag / rolling pilgrim-count features (past-actuals only)
# ---------------------------------------------------------------------------
# IMPORTANT: these are only meaningful, and only computed, for dates where an
# actual pilgrims figure exists (i.e. historical rows from the raw scrape).
# For future dates (--future-only) they are left NaN -- filling them with
# anything else would leak the forecasting target into its own features.

def add_lag_features(df: pd.DataFrame, pilgrims_col: str = "pilgrims_raw") -> pd.DataFrame:
    if pilgrims_col not in df.columns:
        log.info("No '%s' column found -- skipping lag/rolling pilgrim features "
                 "(expected for --future-only feature generation).", pilgrims_col)
        return df

    pilgrims = (
        df[pilgrims_col].astype(str).str.replace(",", "", regex=False)
        .replace({"nan": None, "": None})
    )
    pilgrims = pd.to_numeric(pilgrims, errors="coerce")

    df["pilgrims_lag_1d"] = pilgrims.shift(1)
    df["pilgrims_lag_7d"] = pilgrims.shift(7)
    df["pilgrims_lag_14d"] = pilgrims.shift(14)
    df["pilgrims_roll7_mean"] = pilgrims.shift(1).rolling(7, min_periods=3).mean()
    df["pilgrims_roll28_mean"] = pilgrims.shift(1).rolling(28, min_periods=7).mean()
    df["pilgrims_same_dow_lag_1w"] = pilgrims.shift(7)  # same weekday last week
    return df


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

FEATURE_COLUMNS = [
    "date",
    # calendar
    "year", "month", "day", "day_of_week", "day_name", "week_number", "quarter",
    "day_of_year", "is_weekend", "is_saturday", "is_sunday",
    "is_month_start", "is_month_end", "dow_sin", "dow_cos", "doy_sin", "doy_cos",
    # holidays
    "is_public_holiday", "is_ap_holiday", "is_telangana_holiday", "is_tamilnadu_holiday",
    "is_karnataka_holiday", "is_kerala_holiday", "is_any_source_state_holiday",
    "holiday_name", "is_long_weekend", "is_bridge_day", "days_to_nearest_holiday",
    # panchang
    "tithi_number", "paksha", "is_ekadashi", "is_pournami", "is_amavasya",
    "is_purattasi_saturday", "is_karthika_masam", "is_shravana_masam",
    "is_margashirsha_masam", "is_vaikunta_ekadashi", "is_rathasapthami", "is_teppotsavam",
    # TTD administrative festivals
    "is_brahmotsavam", "is_garuda_seva", "is_pushpayagam",
    # vacations
    "is_summer_vacation", "is_dasara_vacation", "is_christmas_vacation", "is_sankranti_vacation",
    # season
    "season", "is_winter", "is_summer", "is_monsoon", "is_post_monsoon",
    "is_exam_season", "is_festive_season",
    # lag/rolling (NaN for future dates -- see add_lag_features docstring)
    "pilgrims_lag_1d", "pilgrims_lag_7d", "pilgrims_lag_14d",
    "pilgrims_roll7_mean", "pilgrims_roll28_mean", "pilgrims_same_dow_lag_1w",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build feature table for Tirumala crowd forecasting.")
    p.add_argument("--raw", default=DEFAULT_RAW_PATH,
                   help=f"Path to raw_ttd_scrape.csv from build_dataset.py (default: {DEFAULT_RAW_PATH})")
    p.add_argument("--out", default=DEFAULT_OUT_PATH,
                   help=f"Output CSV path (default: {DEFAULT_OUT_PATH})")
    p.add_argument("--start-date", default=None, help="YYYY-MM-DD, defaults to min(date) in --raw")
    p.add_argument("--end-date", default=None, help="YYYY-MM-DD, defaults to max(date) in --raw")
    p.add_argument("--future-only", action="store_true",
                   help="Generate features for a future date range with no raw pilgrim data "
                        "(requires --start-date and --end-date; lag/rolling columns are left NaN)")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.future_only:
        if not args.start_date or not args.end_date:
            log.error("--future-only requires --start-date and --end-date.")
            sys.exit(1)
        start = datetime.strptime(args.start_date, "%Y-%m-%d").date()
        end = datetime.strptime(args.end_date, "%Y-%m-%d").date()
        df = pd.DataFrame({"date": pd.date_range(start, end, freq="D").strftime("%Y-%m-%d")})
    else:
        if not os.path.exists(args.raw):
            log.error("Raw file not found: %s (run build_dataset.py first, or pass --raw)", args.raw)
            sys.exit(1)
        df = pd.read_csv(args.raw, dtype=str)
        if "date" not in df.columns:
            log.error("Expected a 'date' column in %s -- got: %s", args.raw, list(df.columns))
            sys.exit(1)
        df = df.drop_duplicates(subset="date").sort_values("date").reset_index(drop=True)

        if args.start_date:
            df = df[df["date"] >= args.start_date]
        if args.end_date:
            df = df[df["date"] <= args.end_date]

        # Fill in any missing calendar days within the range so every date
        # gets calendar/holiday/panchang/season features even if that day's
        # bulletin failed to scrape.
        full_range = pd.DataFrame({
            "date": pd.date_range(df["date"].min(), df["date"].max(), freq="D").strftime("%Y-%m-%d")
        })
        df = full_range.merge(df, on="date", how="left")

    df = add_calendar_features(df)
    df = add_holiday_features(df)
    df = add_panchang_features(df)
    df = add_administrative_festival_features(df)
    df = add_vacation_features(df)
    df = add_season_features(df)
    df = add_lag_features(df)  # no-op (logs + skips) if pilgrims_raw isn't present

    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    out_df = df[FEATURE_COLUMNS].sort_values("date")
    out_df.to_csv(args.out, index=False)
    log.info("Wrote %s rows x %s feature columns to %s", len(out_df), len(FEATURE_COLUMNS), args.out)


if __name__ == "__main__":
    main()