"""Data-driven crowd banding.

The dashboard shows a six-step crowd scale (Low -> Extreme). The *colours* and
*labels* of those steps are a design decision, but the **thresholds are derived
from the observed pilgrim distribution** rather than hardcoded numbers, so the
scale re-calibrates automatically as new data lands in ``merged.csv`` /
``raw_ttd_scrape.csv``.

Thresholds are the 20/40/60/80/92 percentiles of all known actual daily
footfall. That places the historical median in the middle "Medium" band and
reserves the top band for genuine outlier days.
"""
from __future__ import annotations

import pandas as pd

# Percentile cut points that separate the six bands. Chosen so the historical
# median lands in band index 2 ("Medium") and the top band captures the
# ~8% heaviest days.
QUANTILE_CUTS = (0.20, 0.40, 0.60, 0.80, 0.92)

# Presentation for each band: (label, text colour, fill colour).
# Index 0 = quietest, index 5 = busiest.
BANDS = (
    ("Low crowd", "#ffffff", "#2d8a2e"),           # deep green
    ("Medium-low crowd", "#ffffff", "#6aaf2e"),    # light green
    ("Medium crowd", "#ffffff", "#d4a017"),        # yellow-gold
    ("High crowd", "#ffffff", "#e8872b"),          # orange
    ("Very high crowd", "#ffffff", "#d44a2b"),     # red-orange
    ("Extreme crowd", "#ffffff", "#8b1a1a"),       # dark red
)

# Colour used when a day has no data and no forecast at all.
UNKNOWN_FILL = "#2b2b33"
UNKNOWN_TEXT = "#6b6b78"

# Only values inside this window are treated as real observations. The raw TTD
# bulletins occasionally carry parsing artefacts (zeros, or absurd magnitudes).
PLAUSIBLE_MIN = 1_000
PLAUSIBLE_MAX = 200_000

# Fallback cut points, used only when there is not enough history to compute
# percentiles (e.g. a fresh clone with an empty dataset). Spaced across a
# realistic Tirumala footfall range purely so the UI still renders.
_COLD_START_CUTS = (55_000, 65_000, 72_000, 80_000, 88_000)


def clean_actuals(series: pd.Series) -> pd.Series:
    """Drop nulls and implausible readings from a raw pilgrim series."""
    if series is None or len(series) == 0:
        return pd.Series(dtype=float)
    numeric = pd.to_numeric(series, errors="coerce").dropna().astype(float)
    return numeric[(numeric >= PLAUSIBLE_MIN) & (numeric <= PLAUSIBLE_MAX)]


def compute_thresholds(series: pd.Series) -> list[float]:
    """Return the five ascending cut points that define the six crowd bands.

    Derived from the supplied history. Falls back to a coarse fixed ladder
    only when history is too thin to produce distinct percentiles.
    """
    values = clean_actuals(series)

    # Need a reasonable sample before percentiles mean anything.
    if len(values) < 30:
        return list(_COLD_START_CUTS)

    cuts = [float(values.quantile(q)) for q in QUANTILE_CUTS]

    # Percentiles can collapse onto each other on degenerate data. Force a
    # strictly increasing ladder so band lookup stays well defined.
    for i in range(1, len(cuts)):
        if cuts[i] <= cuts[i - 1]:
            cuts[i] = cuts[i - 1] + 1.0
    return cuts


def level_index(value: float | None, thresholds: list[float]) -> int | None:
    """Map a pilgrim count to a band index 0-5, or None when unknown."""
    if value is None or pd.isna(value) or value <= 0:
        return None
    return sum(1 for t in thresholds if float(value) >= t)


def describe(value: float | None, thresholds: list[float]) -> tuple[str, str, str]:
    """Return (label, text colour, fill colour) for a pilgrim count."""
    idx = level_index(value, thresholds)
    if idx is None:
        return "No data", UNKNOWN_TEXT, UNKNOWN_FILL
    return BANDS[idx]


def scale_position(value: float | None, thresholds: list[float]) -> float:
    """Position of ``value`` along the 0-1 crowd scale.

    Used to place the marker on the gradient meter. Each band occupies an
    equal slice of the bar, and the value is interpolated *within* its band so
    the marker moves smoothly rather than snapping between six positions.
    """
    idx = level_index(value, thresholds)
    if idx is None:
        return 0.5

    n_bands = len(BANDS)
    slice_width = 1.0 / n_bands

    # Establish the numeric span of the band this value falls into. The open
    # ended first/last bands borrow the width of their neighbour so the
    # interpolation has something finite to work with.
    if idx == 0:
        lo_edge, hi_edge = thresholds[0] - (thresholds[1] - thresholds[0]), thresholds[0]
    elif idx == n_bands - 1:
        span = thresholds[-1] - thresholds[-2]
        lo_edge, hi_edge = thresholds[-1], thresholds[-1] + span
    else:
        lo_edge, hi_edge = thresholds[idx - 1], thresholds[idx]

    if hi_edge <= lo_edge:
        within = 0.5
    else:
        within = (float(value) - lo_edge) / (hi_edge - lo_edge)
        within = min(max(within, 0.0), 1.0)

    return min(max((idx + within) * slice_width, 0.0), 1.0)


def display_band(value: float | None, size: int = 10_000) -> tuple[int, int] | None:
    """Round a count into the coarse bucket shown as "70-80k" in the UI."""
    if value is None or pd.isna(value) or value <= 0:
        return None
    lo = int(float(value) // size) * size
    return lo, lo + size


def band_text(bounds: tuple[int, int] | None) -> str:
    """Render a bucket as a compact range string, e.g. "70-80k"."""
    if not bounds:
        return "—"
    lo, hi = bounds
    return f"{lo // 1000}-{hi // 1000}k"


def gradient_css() -> str:
    """CSS ``linear-gradient`` stops for the six-band meter bar."""
    n = len(BANDS)
    stops = []
    for i, (_, _, fill) in enumerate(BANDS):
        start = (i / n) * 100
        end = ((i + 1) / n) * 100
        stops.append(f"{fill} {start:.4f}%, {fill} {end:.4f}%")
    return "linear-gradient(90deg, " + ", ".join(stops) + ")"
