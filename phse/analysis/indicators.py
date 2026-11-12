"""Technical indicator calculations using pandas and ta."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd
import ta

from ..data.models import OHLCV
from .models import IndicatorResult


@dataclass
class _IndicatorInput:
    """Internal input container for indicator calculations."""
    close: pd.Series
    high: pd.Series
    low: pd.Series
    volume: pd.Series


def _build_input(ohlcv: list[OHLCV]) -> _IndicatorInput:
    """Build pandas Series from OHLCV data."""
    df = pd.DataFrame([
        {"close": o.close, "high": o.high, "low": o.low, "volume": o.volume}
        for o in ohlcv
    ])
    return _IndicatorInput(
        close=df["close"],
        high=df["high"],
        low=df["low"],
        volume=df["volume"],
    )


def compute_indicators(ohlcv: list[OHLCV], symbol: str = "") -> IndicatorResult:
    """Compute all technical indicators for OHLCV data.

    Requires at least 20 bars for meaningful results.
    """
    if len(ohlcv) < 20:
        result = IndicatorResult(symbol=symbol)
        # VWAP can still be computed with minimal data
        if len(ohlcv) >= 1:
            df = pd.DataFrame([{"close": o.close, "high": o.high, "low": o.low, "volume": o.volume}
                               for o in ohlcv])
            typical_price = (df["high"] + df["low"] + df["close"]) / 3
            vol_sum = df["volume"].cumsum()
            if vol_sum.iloc[-1] > 0:
                result.vwap = float((typical_price * df["volume"]).cumsum().iloc[-1] / vol_sum.iloc[-1])
        return result

    inp = _build_input(ohlcv)

    result = IndicatorResult(symbol=symbol)

    # ── SMAs ──────────────────────────────────────────────────────────
    for period, attr in [(7, "sma_7"), (20, "sma_20"), (50, "sma_50"), (200, "sma_200")]:
        if len(inp.close) >= period:
            sma = ta.trend.SMAIndicator(close=inp.close, window=period)
            val = sma.sma_indicator().iloc[-1]
            if pd.notna(val):
                setattr(result, attr, float(val))

    # ── EMAs ──────────────────────────────────────────────────────────
    for period, attr in [(12, "ema_12"), (26, "ema_26")]:
        if len(inp.close) >= period:
            ema = ta.trend.EMAIndicator(close=inp.close, window=period)
            val = ema.ema_indicator().iloc[-1]
            if pd.notna(val):
                setattr(result, attr, float(val))

    # ── RSI ───────────────────────────────────────────────────────────
    if len(inp.close) >= 15:
        rsi = ta.momentum.RSIIndicator(close=inp.close, window=14)
        val = rsi.rsi().iloc[-1]
        if pd.notna(val):
            result.rsi_14 = float(val)

    # ── MACD ──────────────────────────────────────────────────────────
    if len(inp.close) >= 35:
        macd = ta.trend.MACD(close=inp.close, window_fast=12, window_slow=26, window_sign=9)
        result.macd_line = float(macd.macd().iloc[-1]) if pd.notna(macd.macd().iloc[-1]) else None
        result.macd_signal = float(macd.macd_signal().iloc[-1]) if pd.notna(macd.macd_signal().iloc[-1]) else None
        result.macd_hist = float(macd.macd_diff().iloc[-1]) if pd.notna(macd.macd_diff().iloc[-1]) else None

    # ── Bollinger Bands ───────────────────────────────────────────────
    if len(inp.close) >= 20:
        bb = ta.volatility.BollingerBands(close=inp.close, window=20, window_dev=2)
        result.bb_upper = float(bb.bollinger_hband().iloc[-1]) if pd.notna(bb.bollinger_hband().iloc[-1]) else None
        result.bb_middle = float(bb.bollinger_mavg().iloc[-1]) if pd.notna(bb.bollinger_mavg().iloc[-1]) else None
        result.bb_lower = float(bb.bollinger_lband().iloc[-1]) if pd.notna(bb.bollinger_lband().iloc[-1]) else None

    # ── ATR ───────────────────────────────────────────────────────────
    if len(inp.high) >= 15:
        atr = ta.volatility.AverageTrueRange(high=inp.high, low=inp.low, close=inp.close, window=14)
        val = atr.average_true_range().iloc[-1]
        if pd.notna(val):
            result.atr_14 = float(val)

    # ── VWAP (approximation for daily data) ───────────────────────────
    if len(inp.close) >= 1:
        typical_price = (inp.high + inp.low + inp.close) / 3
        result.vwap = float((typical_price * inp.volume).cumsum().iloc[-1] / inp.volume.cumsum().iloc[-1])

    return result
