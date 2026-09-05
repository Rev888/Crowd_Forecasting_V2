"""
Live TTD bulletin scraper, ported from tml.py (build_dataset.py).

Fetches the latest darshan bulletin(s) from https://news.tirumala.org over
HTTPS only. On any failure (network, parse, robots block, etc.) the caller
falls back to the stored raw_ttd_scrape.csv data instead of crashing --
see get_latest_snapshot() in lib/data_loader.py.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://news.tirumala.org"
USER_AGENT = (
    "TirumalaCrowdIntelligenceApp/1.0 "
    "(public-interest darshan-wait-time dashboard)"
)
REQUEST_TIMEOUT = 10


@dataclass
class ScrapedDay:
    date: str
    pilgrims_raw: Optional[str] = None
    tonsures_raw: Optional[str] = None
    hundi_raw: Optional[str] = None
    laddu_raw: Optional[str] = None
    annaprasadam_raw: Optional[str] = None
    medical_raw: Optional[str] = None
    waiting_compartments_raw: Optional[str] = None
    waiting_time_raw: Optional[str] = None
    source_url: Optional[str] = None
    scrape_status: str = "ok"


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    s.verify = True  # HTTPS certificate verification always on
    return s


def _fetch_bulletin_for_date(session: requests.Session, d: date) -> Optional[ScrapedDay]:
    dd_mm_yyyy = d.strftime("%d-%m-%Y")
    naive_url = f"{BASE_URL}/total-pilgrims-who-had-darshan-on-{dd_mm_yyyy}"
    try:
        resp = session.get(naive_url, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
    except requests.exceptions.RequestException:
        return None

    return _parse_bulletin_html(resp.text, d, resp.url)


def _parse_bulletin_html(html: str, d: date, url: str) -> ScrapedDay:
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("article") or soup.find("div", class_=re.compile("entry-content|post-content", re.I))
    text = article.get_text(separator=" ", strip=True) if article else soup.get_text(separator=" ", strip=True)

    def find(pattern: str) -> Optional[str]:
        m = re.search(pattern, text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    pilgrims = find(r"darshan on[^\d]*\d{1,2}[./]\d{1,2}[./]\d{2,4}\s*[:\-]?\s*([\d,]+)")
    tonsures = find(r"Tonsures?\s*[:\-]?\s*([\d,]+)")
    hundi = find(r"Hundi\s*(?:kanukalu)?\s*[:\-]?\s*([\d,.]+)\s*CR")
    laddu = find(r"Laddu\s*sale[.\u2026:\-]*\s*([\d,.]+)\s*Lac")
    annaprasadam = find(r"Annaprasadams?[.\u2026:\-]*\s*([\d,.]+)\s*Lac")
    medical = find(r"Medical\s*treatments?[.\u2026:\-]*\s*([\d,]+)")
    waiting_compartments = find(
        r"Waiting\s*Compartments?[.\u2026:\-]*\s*(.*?)(?=Approx\.|Darsh?an\s*Time|$)"
    )

    if "Tokens)" in text:
        time_section = text.split("Tokens)")[-1]
    elif re.search(r"Darsh?an\s*Time", text, re.IGNORECASE):
        time_section = re.split(r"Darsh?an\s*Time", text, flags=re.IGNORECASE)[-1]
    else:
        time_section = ""
    time_match = re.search(
        r"(\d+(?:\.\d+)?\s*(?:[\u2013-]\s*\d+(?:\.\d+)?)?)\s*H\b", time_section, re.IGNORECASE
    )
    waiting_time = time_match.group(1).strip() if time_match else None

    return ScrapedDay(
        date=d.strftime("%Y-%m-%d"),
        pilgrims_raw=pilgrims,
        tonsures_raw=tonsures,
        hundi_raw=hundi,
        laddu_raw=laddu,
        annaprasadam_raw=annaprasadam,
        medical_raw=medical,
        waiting_compartments_raw=waiting_compartments,
        waiting_time_raw=waiting_time,
        source_url=url,
        scrape_status="ok",
    )


def fetch_latest(lookback_days: int = 5) -> Optional[ScrapedDay]:
    """
    Try today, then walk backwards up to `lookback_days`, and return the
    most recent day with a successfully parsed pilgrim count. Returns None
    if nothing could be fetched (caller should fall back to stored data).
    """
    session = _session()
    d = date.today()
    for _ in range(lookback_days):
        record = _fetch_bulletin_for_date(session, d)
        if record is not None and record.pilgrims_raw:
            return record
        d -= timedelta(days=1)
    return None
