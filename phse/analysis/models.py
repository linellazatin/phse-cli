"""Analysis result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class IndicatorResult:
    """Container for computed technical indicators."""
    symbol: str
    sma_7: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    rsi_14: Optional[float] = None
    macd_line: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    atr_14: Optional[float] = None
    vwap: Optional[float] = None


@dataclass
class Signal:
    """A single trading signal."""
    name: str
    direction: str  # "BUY", "SELL", "NEUTRAL"
    strength: float  # 0.0 to 1.0
    reason: str


@dataclass
class AnalysisResult:
    """Complete analysis for a stock."""
    symbol: str
    indicators: IndicatorResult
    signals: list[Signal] = field(default_factory=list)
    composite_signal: str = "NEUTRAL"  # BUY, HOLD, SELL
    composite_confidence: float = 0.0  # 0.0 to 1.0
    composite_score: float = 0.0  # -1.0 (strong sell) to +1.0 (strong buy)
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
