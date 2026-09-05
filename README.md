# 🛕 Tirumala Crowd Predictor

A retro pixel-art dashboard that monitors and forecasts daily pilgrim footfall at
Tirumala, and translates that into the number people actually care about: **how
long the ticketless (Sarva Darshan) queue is likely to be.**

Footfall is predicted by a CatBoost model over 77 date-derived features —
calendar, multi-state holidays, Panchangam (tithi/masam), the official TTD
Divya Utsavam calendar, school-vacation windows and seasonality — combined with
lagged crowd history. The dashboard reads the latest official TTD bulletin live,
and falls back to a stored snapshot when the site is unreachable.

> **This is an independent, unofficial project.** It is not affiliated with,
> associated with, or endorsed by Tirumala Tirupati Devasthanams (TTD). See
> [Disclaimer](#-disclaimer).

---

## ✨ What it does

**Live operational monitoring** — scrapes the latest darshan bulletin from
`news.tirumala.org` (pilgrim count, wait time, tonsures, hundi, laddu and
annaprasadam sales, medical cases, waiting compartments). Any failure falls back
to the last known-good stored row instead of breaking the page, and the UI
always states which of the two you are looking at.

**Crowd calendar** — a month heatmap where each day is coloured by its crowd
band. Days backed by real observations carry a tick; the rest are model
forecasts. Click any day for its detail.

**Selected-day detail** — expected pilgrims, expected ticketless-darshan wait,
the crowd band on a gradient meter, and an `OBSERVED` / `PREDICTED` tag so the
provenance of the number is never ambiguous.

**Why this day** — the calendar, holiday and Panchangam flags actually driving
that day's forecast, surfaced as chips (weekend, named public holiday,
Brahmotsavam, Ekadashi, Pournami, vacation windows, season…). These are read
from the model's own computed feature row, not re-derived for display.

**Utsavams / festivals** — TTD calendar entries active on the selected day, with
event type, importance and date span.

**Trend & forecast chart** — trailing observed history joined to the forecast
horizon, so the handover between real data and prediction is visible, shaded by
crowd band.

**Best days to visit** — the quietest upcoming days in the displayed month,
ranked, with their expected wait.

**Month summary** — average, busiest and quietest day, observed-vs-forecast
split, festival-day count, and a **CSV export** of the whole month.

**Data & model panel** — how much history is loaded, its date range, the live
bulletin source, the forecast horizon, and the crowd-band cut points currently
in effect.

### Nothing is hardcoded

Every number, colour threshold, label and date range in the UI is derived at
runtime from the datasets and the model. In particular the six-band crowd scale
is computed from the **observed footfall distribution** (the 20/40/60/80/92
percentiles in `lib/crowd_levels.py`), so the scale recalibrates itself as new
data arrives rather than relying on fixed thresholds. The only fixed content is
the page layout, the disclaimer copy, and the decorative pixel artwork.

---

## 🚀 Setup

Requires **Python 3.9+**.

```bash
git clone <your-repo-url>
cd "Tirmula Project"
```

```bash
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
```

```bash
streamlit run app.py
```

The dashboard opens at `http://localhost:8501`. It works fully offline using the
bundled CSVs — the live scrape is an enhancement, not a requirement.

---

## 🏗 Project structure

| Path | Purpose |
| --- | --- |
| `app.py` | Dashboard layout, interaction and rendering. Holds no thresholds of its own. |
| `lib/predictor.py` | Inference layer. Binds to the saved model at runtime (feature names and categorical indices are read from the model), builds future-safe feature rows, runs recursive multi-day forecasts, and estimates wait times. |
| `lib/features.py` | Feature engineering: calendar, multi-state holidays, Panchangam (tithi/paksha/masam via `ephem`), TTD festivals, vacation windows, seasonality, lags. |
| `lib/scraper.py` | HTTPS-only scraper for the daily TTD bulletin. |
| `lib/data_loader.py` | Cached dataset loading, the unified observed-footfall series, and the live-scrape-with-fallback snapshot. |
| `lib/crowd_levels.py` | Crowd banding: percentile thresholds, labels, colours, meter position. |
| `lib/styles.py` | The whole stylesheet, behind one set of design tokens. |
| `lib/pixel_art.py` | The pixel-art deity motif, stored as run-length spans and rendered to SVG. |
| `backtest_optuna.py` | Walk-forward backtest that rebuilds each day's features using only prior information. |
| `data/` | `merged.csv` (engineered history), `raw_ttd_scrape.csv` (scraped bulletins), `ttd_tirumala_events_2026_2027.csv` (official Divya Utsavam calendar). |
| `tirumala_future_safe_optuna.cbm` | The production model (77 features, 7 categorical). |
| `tirumala_catboost.cbm` | Earlier model, kept for reference. |

---

## 🧠 Model & methodology

**No future peeking.** The production model deliberately excludes same-day
operational bulletin fields (`waiting_time_raw`, `tonsures_raw`, `hundi_raw`
and the rest) — those are unknowable in advance, and `lib/predictor.py` asserts
their absence from the model schema. A forecast uses only date-derived features
plus crowd history strictly *before* the target date.

**Recursive multi-day forecasting.** Observed values are immutable. Beyond the
last observed day, each prediction is appended to a running series so the next
day's lag features have something to read. Error therefore compounds with
distance, which is why the dashboard caps the horizon at 400 days and says so
rather than extrapolating indefinitely.

**Wait-time estimates** are not a model output. They are the historical *median*
recorded wait for the volume band a prediction falls into, derived from
`merged.csv` — a lookup, presented as approximate.

### Backtest accuracy

Walk-forward over 1,258 days (2023-01-16 → 2026-08-03), each day predicted using
only prior information:

| Metric | Value |
| --- | --- |
| MAE | ~3,777 pilgrims/day |
| RMSE | ~5,086 |
| MAPE | 5.52% |
| Median APE | 4.29% |
| Within 5% | 56.9% of days |
| Within 10% | 88.0% of days |

Reproduce with:

```bash
python backtest_optuna.py
```

### Known data caveats

- School-vacation windows for some years are **estimated**, not confirmed
  against the official AP/TG school GO; the loader logs a warning for each. They
  feed real model features, so verify them before trusting festival-season
  peaks.
- The bundled TTD event calendar covers 2026–2027. Outside that range, event
  features are simply absent rather than wrong.

---

## ⚠️ Disclaimer

This is an **independent and unofficial project** created for informational and
planning purposes only. It is not affiliated with, associated with, or endorsed
by Tirumala Tirupati Devasthanams (TTD), and does not represent official TTD
information or advisories.

Crowd levels are predicted using ML models on available historical and
contextual data. Predictions are estimates and cannot guarantee actual crowd
conditions. Real-world conditions vary due to unforeseen events, operational
changes, weather and festivals.

Please use these predictions **only as a planning reference**. The developers are
not responsible for any loss, injury, delay, inconvenience or other consequences
resulting from reliance on the information provided.
