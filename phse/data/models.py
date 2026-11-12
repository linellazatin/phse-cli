"""Pydantic models for PSE data."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Company ──────────────────────────────────────────────────────────────

class Company(BaseModel):
    """A listed company on the PSE."""

    symbol: str
    name: str
    sector: str = ""
    subsector: str = ""
    cmpy_id: int = 0
    listing_date: Optional[date] = None


# ── Quote ────────────────────────────────────────────────────────────────

class Quote(BaseModel):
    """Latest stock quote for a company."""

    symbol: str
    company_name: str

    # Price data
    last_price: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    previous_close: Optional[float] = None

    # Derived
    change: Optional[float] = None
    percent_change: Optional[float] = None

    # Volume & value
    volume: Optional[int] = None
    value: Optional[float] = None  # in PHP
    average_price: Optional[float] = None

    # Market data
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    book_value: Optional[float] = None

    # Range
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None

    # Metadata
    as_of: Optional[datetime] = None
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


# ── Technical Indicators ─────────────────────────────────────────────────

class TechnicalSignal(BaseModel):
    """A single technical signal."""

    indicator: str
    signal: str  # "BUY", "SELL", "NEUTRAL"
    value: float
    description: str = ""


class AnalysisResult(BaseModel):
    """Complete analysis for a stock."""

    symbol: str
    company_name: str

    # Current quote
    last_price: Optional[float] = None

    # Indicators
    sma_7: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    rsi_14: Optional[float] = None
    macd_line: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_middle: Optional[float] = None
    bollinger_lower: Optional[float] = None
    atr_14: Optional[float] = None

    # Signals
    signals: list[TechnicalSignal] = []

    # Composite
    recommendation: str = "HOLD"  # BUY, SELL, HOLD
    confidence: float = 0.0  # 0-100
    summary: str = ""


# ── Scanner Results ──────────────────────────────────────────────────────

class ScanResult(BaseModel):
    """Result of a stock screen."""

    symbol: str
    company_name: str
    last_price: Optional[float] = None
    change: Optional[float] = None
    percent_change: Optional[float] = None
    volume: Optional[int] = None
    value: Optional[float] = None  # trading value = volume × price
    market_cap: Optional[float] = None
    sector: str = ""
    pe_ratio: Optional[float] = None


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
    triggered_at: Optional[datetime] = None


# ── Market Summary ───────────────────────────────────────────────────────

class MarketSummary(BaseModel):
    """PSE market summary."""

    pse_index: Optional[float] = None
    psei_index: Optional[float] = None
    advancers: Optional[int] = None
    decliners: Optional[int] = None
    unchanged: Optional[int] = None
    total_volume: Optional[int] = None
    total_value: Optional[float] = None
    as_of: Optional[datetime] = None
