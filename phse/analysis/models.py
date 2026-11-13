"""Analysis result models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class IndicatorResult:
    """Container for computed technical indicators."""
    symbol: str
    sma_7: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    ema_12: float | None = None
    ema_26: float | None = None
    rsi_14: float | None = None
    macd_line: float | None = None
    macd_signal: float | None = None
    macd_hist: float | None = None
    bb_upper: float | None = None
    bb_middle: float | None = None
    bb_lower: float | None = None
    atr_14: float | None = None
    vwap: float | None = None


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
    support_level: float | None = None
    resistance_level: float | None = None
