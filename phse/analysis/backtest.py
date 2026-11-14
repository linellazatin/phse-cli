"""Simple backtesting engine for signal logic."""

from __future__ import annotations

from dataclasses import dataclass

from ..data.models import OHLCV


@dataclass
class BacktestResult:
    """Results from a backtest run."""
    symbol: str
    strategy: str
    period_days: int
    total_return_pct: float
    buy_count: int
    sell_count: int
    win_rate: float  # percentage of profitable trades
    max_drawdown_pct: float
    sharpe_ratio: float  # annualized


def backtest_sma_crossover(
    ohlcv: list[OHLCV],
    symbol: str,
    short_period: int = 7,
    long_period: int = 20,
) -> BacktestResult:
    """Backtest a simple SMA crossover strategy.

    Rules:
    - BUY when short SMA crosses above long SMA
    - SELL when short SMA crosses below long SMA
    - Hold cash between signals (no position = 0% return)
    """
    if len(ohlcv) < long_period + 10:
        return BacktestResult(
            symbol=symbol, strategy=f"SMA {short_period}/{long_period}",
            period_days=len(ohlcv), total_return_pct=0.0,
            buy_count=0, sell_count=0, win_rate=0.0,
            max_drawdown_pct=0.0, sharpe_ratio=0.0,
        )

    closes = [o.close for o in ohlcv]
    n = len(closes)

    # Compute SMAs
    short_sma = []
    long_sma = []
    for i in range(n):
        if i < short_period - 1:
            short_sma.append(None)
        else:
            short_sma.append(sum(closes[i - short_period + 1:i + 1]) / short_period)

        if i < long_period - 1:
            long_sma.append(None)
        else:
            long_sma.append(sum(closes[i - long_period + 1:i + 1]) / long_period)

    # Simulate trades
    position = False  # False = cash, True = stock
    entry_prices = []  # track actual entry prices
    exit_prices = []  # track actual exit prices
    buys = 0
    sells = 0

    for i in range(long_period, n):
        if short_sma[i] is None or long_sma[i] is None:
            continue

        # Handle first valid point: if short > long and no position, enter (initial golden cross)
        if i == long_period and not position and short_sma[i] > long_sma[i]:
            position = True
            entry_prices.append(closes[i])
            buys += 1
        elif short_sma[i - 1] is not None and long_sma[i - 1] is not None:
            # Golden cross: short crosses above long
            if not position and short_sma[i] > long_sma[i] and short_sma[i - 1] <= long_sma[i - 1]:
                position = True
                entry_prices.append(closes[i])
                buys += 1
            # Death cross: short crosses below long
            elif position and short_sma[i] < long_sma[i] and short_sma[i - 1] >= long_sma[i - 1]:
                position = False
                exit_prices.append(closes[i])
                sells += 1

    # Close any open position at the end
    if position:
        exit_prices.append(closes[n - 1])
        sells += 1

    # Calculate returns from actual entry/exit pairs
    trade_count = min(len(entry_prices), len(exit_prices))
    if trade_count == 0:
        total_return = 0.0
        win_rate = 0.0
        trade_returns = []
    else:
        trade_returns = []
        wins = 0
        for i in range(trade_count):
            trade_return = (exit_prices[i] - entry_prices[i]) / entry_prices[i] * 100
            trade_returns.append(trade_return)
            if trade_return > 0:
                wins += 1
        # Compound returns: (1 + r1)(1 + r2)... - 1
        compound_factor = 1.0
        for r in trade_returns:
            compound_factor *= (1 + r / 100)
        total_return = (compound_factor - 1) * 100
        win_rate = wins / trade_count * 100 if trade_count > 0 else 0

    # Max drawdown
    peak = closes[long_period]
    max_dd = 0.0
    for i in range(long_period, n):
        peak = max(peak, closes[i])
        dd = (peak - closes[i]) / peak * 100
        max_dd = max(max_dd, dd)

    # Sharpe ratio (simplified annualized)
    if trade_count > 1 and trade_returns:
        avg_return = sum(trade_returns) / len(trade_returns)
        variance = sum((r - avg_return) ** 2 for r in trade_returns) / (len(trade_returns) - 1)
        std_dev = variance ** 0.5
        sharpe = (avg_return / std_dev) * (252 ** 0.5) if std_dev > 0 else 0.0
    else:
        sharpe = 0.0

    return BacktestResult(
        symbol=symbol,
        strategy=f"SMA {short_period}/{long_period} Crossover",
        period_days=n,
        total_return_pct=total_return,
        buy_count=buys,
        sell_count=sells,
        win_rate=win_rate,
        max_drawdown_pct=max_dd,
        sharpe_ratio=sharpe,
    )
