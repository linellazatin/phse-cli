"""Signal explanation — why did a stock get this signal?"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

from ..analysis import compute_indicators, generate_signals

from ..config import get_settings
from ..data.pse_edge import PseEdgeClient

console = Console()


def explain_signal(symbol: str, period: str = "1y") -> None:
    """Explain why a stock got its current signal."""
    client = PseEdgeClient(get_settings())
    
    # Fetch history
    ohlcv = client.get_price_history(0, symbol, period)
    if not ohlcv:
        console.print(f"[bold red]Could not fetch history for '{symbol}'.[/bold red]")
        return
    
    # Compute indicators and signals
    indicators = compute_indicators(ohlcv, symbol)
    current_price = ohlcv[-1].close if ohlcv else 0
    result = generate_signals(indicators, current_price)
    
    # Get composite signal
    signal_type = result.composite_signal
    confidence = result.composite_confidence * 100
    
    # Print explanation
    console.print()
    console.print(Panel(
        f"[bold]{symbol}[/bold] — Signal Explanation\n"
        f"[dim]Period: {period} | Bars: {len(ohlcv)}[/dim]",
        title=f"[bold]Why {symbol}?[/bold]",
        border_style="blue",
    ))
    
    # Signal summary
    signal_color = {
        "BUY": "green",
        "SELL": "red",
        "HOLD": "yellow",
    }.get(signal_type, "white")
    
    console.print(f"\n[bold]Composite Signal:[/bold] [{signal_color}]{signal_type}[/] ({confidence:.0f}% confidence)")
    
    # Individual signal explanations
    reasons = []
    
    # SMA signals
    if indicators.sma_7 is not None and indicators.sma_20 is not None:
        if indicators.sma_7 > indicators.sma_20:
            reasons.append(f"SMA 7 ({indicators.sma_7:.2f}) > SMA 20 ({indicators.sma_20:.2f}) — bullish crossover")
        else:
            reasons.append(f"SMA 7 ({indicators.sma_7:.2f}) < SMA 20 ({indicators.sma_20:.2f}) — bearish crossover")
    
    if indicators.sma_50 is not None and indicators.sma_200 is not None:
        if indicators.sma_50 > indicators.sma_200:
            reasons.append("SMA 50 > SMA 200 — golden cross (bullish)")
        else:
            reasons.append("SMA 50 < SMA 200 — death cross (bearish)")
    
    # EMA signals
    if indicators.ema_12 is not None and indicators.ema_26 is not None:
        if indicators.ema_12 > indicators.ema_26:
            reasons.append("EMA 12 > EMA 26 — bullish momentum")
        else:
            reasons.append("EMA 12 < EMA 26 — bearish momentum")
    
    # RSI signals
    if indicators.rsi_14 is not None:
        if indicators.rsi_14 > 70:
            reasons.append(f"RSI {indicators.rsi_14:.1f} — overbought (>70)")
        elif indicators.rsi_14 < 30:
            reasons.append(f"RSI {indicators.rsi_14:.1f} — oversold (<30)")
        else:
            reasons.append(f"RSI {indicators.rsi_14:.1f} — neutral range (30-70)")
    
    # Bollinger signals
    if indicators.bb_upper is not None and indicators.bb_lower is not None and ohlcv:
        last_close = ohlcv[-1].close
        if last_close > indicators.bb_upper:
            reasons.append(f"Price above BB upper ({indicators.bb_upper:.2f}) — overextended")
        elif last_close < indicators.bb_lower:
            reasons.append(f"Price below BB lower ({indicators.bb_lower:.2f}) — oversold")
        else:
            reasons.append(f"Price within Bollinger Bands")
    
    # MACD signals
    if indicators.macd_hist is not None:
        if indicators.macd_hist > 0:
            reasons.append(f"MACD histogram positive ({indicators.macd_hist:.4f}) — bullish momentum")
        else:
            reasons.append(f"MACD histogram negative ({indicators.macd_hist:.4f}) — bearish momentum")
    
    # Print reasons
    console.print("\n[bold]Contributing Factors:[/bold]")
    for i, reason in enumerate(reasons, 1):
        console.print(f"  {i}. {reason}")
    
    console.print()
