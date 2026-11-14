"""Pydantic models for PSE data."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

# ── Company ──────────────────────────────────────────────────────────────

class Company(BaseModel):
    """A listed company on the PSE."""

    symbol: str
    name: str
    sector: str = ""
    subsector: str = ""
    cmpy_id: int = 0
    listing_date: date | None = None


# ── Quote ────────────────────────────────────────────────────────────────

class Quote(BaseModel):
    """Latest stock quote for a company."""

    symbol: str
    company_name: str

    # Price data
    last_price: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    previous_close: float | None = None

    # Derived
    change: float | None = None
    percent_change: float | None = None

    # Volume & value
    volume: int | None = None
    value: float | None = None  # in PHP
    average_price: float | None = None

    # Market data
    market_cap: float | None = None
    pe_ratio: float | None = None
    pb_ratio: float | None = None
    book_value: float | None = None
    sector: str = ""
    subsector: str = ""

    # Range
    week_52_high: float | None = None
    week_52_low: float | None = None

    # Metadata
    as_of: datetime | None = None
    stale: bool = False


# ── OHLCV ────────────────────────────────────────────────────────────────

class OHLCV(BaseModel):
    """Single day of price data."""

    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


# ── Scanner Results ──────────────────────────────────────────────────────

class ScanResult(BaseModel):
    """Result of a stock screen."""

    symbol: str
    company_name: str
    last_price: float | None = None
    change: float | None = None
    percent_change: float | None = None
    volume: int | None = None
    value: float | None = None  # trading value = volume × price
    market_cap: float | None = None
    sector: str = ""
    subsector: str = ""
    pe_ratio: float | None = None


# ── Watchlist ────────────────────────────────────────────────────────────

class WatchlistEntry(BaseModel):
    """A stock in the watchlist."""

    symbol: str
    company_name: str
    added_at: datetime = Field(default_factory=datetime.now)
    alerts: list[Alert] = []


class Alert(BaseModel):
    """Price alert."""

    alert_type: str  # "above" or "below"
    price: float
    triggered: bool = False
    triggered_at: datetime | None = None


# ── Market Summary ───────────────────────────────────────────────────────
# Note: AnalysisResult and TechnicalSignal were removed from this module.
# Use phse.analysis.models.AnalysisResult and phse.analysis.models.Signal instead.

class MarketSummary(BaseModel):
    """PSE market summary."""

    pse_index: float | None = None
    psei_index: float | None = None
    advancers: int | None = None
    decliners: int | None = None
    unchanged: int | None = None
    total_volume: int | None = None
    total_value: float | None = None
    as_of: datetime | None = None
