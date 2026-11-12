"""Signal generation from technical indicators."""

from __future__ import annotations

from .models import AnalysisResult, IndicatorResult, Signal


def generate_signals(result: IndicatorResult, current_price: float) -> AnalysisResult:
    """Generate trading signals from computed indicators.

    Uses simple, well-known technical analysis rules:
    - SMA crossovers (short > long = bullish)
    - EMA crossovers (12 > 26 = bullish)
    - RSI levels (<30 oversold/buy, >70 overbought/sell)
    - Bollinger Band positions (below lower = buy, above upper = sell)
    - MACD histogram direction
    """
    signals: list[Signal] = []

    # ── SMA Crossovers ────────────────────────────────────────────────
    if result.sma_7 and result.sma_20:
        if current_price > result.sma_7 > result.sma_20:
            signals.append(Signal("SMA 7/20", "BUY", 0.6, "Price above SMA7 > SMA20 (bullish alignment)"))
        elif current_price < result.sma_7 < result.sma_20:
            signals.append(Signal("SMA 7/20", "SELL", 0.6, "Price below SMA7 < SMA20 (bearish alignment)"))
        elif result.sma_7 > result.sma_20 and current_price < result.sma_7:
            signals.append(Signal("SMA 7/20", "NEUTRAL", 0.3, "SMA7 > SMA20 but price pulling back"))

    if result.sma_50 and result.sma_200:
        if current_price > result.sma_50 > result.sma_200:
            signals.append(Signal("Golden Cross", "BUY", 0.8, "Price above SMA50 > SMA200 (golden cross)"))
        elif current_price < result.sma_50 < result.sma_200:
            signals.append(Signal("Death Cross", "SELL", 0.8, "Price below SMA50 < SMA200 (death cross)"))

    # ── EMA Crossover ─────────────────────────────────────────────────
    if result.ema_12 and result.ema_26:
        if result.ema_12 > result.ema_26:
            signals.append(Signal("EMA 12/26", "BUY", 0.5, f"EMA12 ({result.ema_12:.2f}) > EMA26 ({result.ema_26:.2f})"))
        else:
            signals.append(Signal("EMA 12/26", "SELL", 0.5, f"EMA12 ({result.ema_12:.2f}) < EMA26 ({result.ema_26:.2f})"))

    # ── RSI ───────────────────────────────────────────────────────────
    if result.rsi_14 is not None:
        if result.rsi_14 < 30:
            signals.append(Signal("RSI 14", "BUY", 0.7, f"RSI at {result.rsi_14:.1f} (oversold < 30)"))
        elif result.rsi_14 > 70:
            signals.append(Signal("RSI 14", "SELL", 0.7, f"RSI at {result.rsi_14:.1f} (overbought > 70)"))
        elif result.rsi_14 < 45:
            signals.append(Signal("RSI 14", "BUY", 0.3, f"RSI at {result.rsi_14:.1f} (approaching oversold)"))
        elif result.rsi_14 > 55:
            signals.append(Signal("RSI 14", "SELL", 0.3, f"RSI at {result.rsi_14:.1f} (approaching overbought)"))

    # ── Bollinger Bands ───────────────────────────────────────────────
    if result.bb_upper and result.bb_lower and result.bb_middle:
        if current_price <= result.bb_lower:
            signals.append(Signal("Bollinger", "BUY", 0.6, f"Price ({current_price:.2f}) at/below lower band ({result.bb_lower:.2f})"))
        elif current_price >= result.bb_upper:
            signals.append(Signal("Bollinger", "SELL", 0.6, f"Price ({current_price:.2f}) at/above upper band ({result.bb_upper:.2f})"))
        elif current_price > result.bb_middle:
            signals.append(Signal("Bollinger", "NEUTRAL", 0.2, f"Price above middle band ({result.bb_middle:.2f})"))
        else:
            signals.append(Signal("Bollinger", "NEUTRAL", 0.2, f"Price below middle band ({result.bb_middle:.2f})"))

    # ── MACD ──────────────────────────────────────────────────────────
    if result.macd_line is not None and result.macd_signal is not None:
        if result.macd_line > result.macd_signal:
            signals.append(Signal("MACD", "BUY", 0.5, f"MACD line ({result.macd_line:.3f}) above signal ({result.macd_signal:.3f})"))
        else:
            signals.append(Signal("MACD", "SELL", 0.5, f"MACD line ({result.macd_line:.3f}) below signal ({result.macd_signal:.3f})"))

        if result.macd_hist is not None:
            if result.macd_hist > 0:
                signals.append(Signal("MACD Hist", "BUY", 0.3, f"MACD histogram positive ({result.macd_hist:.3f})"))
            else:
                signals.append(Signal("MACD Hist", "SELL", 0.3, f"MACD histogram negative ({result.macd_hist:.3f})"))

    # ── Composite Score ───────────────────────────────────────────────
    buy_score = sum(s.strength for s in signals if s.direction == "BUY")
    sell_score = sum(s.strength for s in signals if s.direction == "SELL")
    score = (buy_score - sell_score) / max(len(signals), 1)

    if score >= 0.3:
        composite = "BUY"
        confidence = min(buy_score / 3.0, 1.0)
    elif score <= -0.3:
        composite = "SELL"
        confidence = min(sell_score / 3.0, 1.0)
    else:
        composite = "HOLD"
        confidence = 0.5

    # ── Support/Resistance ────────────────────────────────────────────
    # Use recent highs/lows (last 20 bars)
    # These will be set by the caller with OHLCV data
    support = None
    resistance = None

    return AnalysisResult(
        symbol=result.symbol,
        indicators=result,
        signals=signals,
        composite_signal=composite,
        composite_confidence=confidence,
        composite_score=score,
        support_level=support,
        resistance_level=resistance,
    )
