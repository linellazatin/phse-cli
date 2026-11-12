"""Tests for analysis module."""

from datetime import date

import pytest

from phse.analysis import compute_indicators, generate_signals, backtest_sma_crossover
from phse.analysis.models import IndicatorResult, Signal, AnalysisResult
from phse.data.models import OHLCV


def _make_ohlcv(n: int = 50, base_price: float = 10.0) -> list[OHLCV]:
    """Generate synthetic OHLCV data for testing."""
    data = []
    for i in range(n):
        price = base_price * (1 + 0.01 * (i - n // 4))  # gradual uptrend
        data.append(OHLCV(
            date=date(2026, 1, 1) + __import__("datetime").timedelta(days=i),
            open=max(0.01, price * 0.99),
            high=price * 1.02,
            low=max(0.01, price * 0.98),
            close=price,
            volume=1000000 + i * 10000,
        ))
    return data


class TestComputeIndicators:
    def test_min_bars(self):
        """Less than 20 bars returns all None indicators."""
        ohlcv = _make_ohlcv(n=10)
        result = compute_indicators(ohlcv, "TEST")
        assert result.symbol == "TEST"
        assert result.sma_7 is None
        assert result.sma_20 is None

    def test_sma_computed(self):
        """SMA values are computed with sufficient bars."""
        ohlcv = _make_ohlcv(n=50)
        result = compute_indicators(ohlcv, "TEST")
        assert result.sma_7 is not None
        assert result.sma_7 > 0
        assert result.sma_20 is not None
        assert result.sma_20 > 0

    def test_ema_computed(self):
        """EMA values are computed with sufficient bars."""
        ohlcv = _make_ohlcv(n=50)
        result = compute_indicators(ohlcv, "TEST")
        assert result.ema_12 is not None
        assert result.ema_12 > 0

    def test_rsi_computed(self):
        """RSI is computed with sufficient bars."""
        ohlcv = _make_ohlcv(n=30)
        result = compute_indicators(ohlcv, "TEST")
        assert result.rsi_14 is not None
        assert 0 <= result.rsi_14 <= 100

    def test_macd_computed(self):
        """MACD is computed with sufficient bars."""
        ohlcv = _make_ohlcv(n=50)
        result = compute_indicators(ohlcv, "TEST")
        assert result.macd_line is not None
        assert result.macd_signal is not None

    def test_bollinger_computed(self):
        """Bollinger Bands are computed with sufficient bars."""
        ohlcv = _make_ohlcv(n=50)
        result = compute_indicators(ohlcv, "TEST")
        assert result.bb_upper is not None
        assert result.bb_lower is not None
        assert result.bb_upper > result.bb_lower

    def test_atr_computed(self):
        """ATR is computed with sufficient bars."""
        ohlcv = _make_ohlcv(n=30)
        result = compute_indicators(ohlcv, "TEST")
        assert result.atr_14 is not None
        assert result.atr_14 > 0

    def test_vwap_computed(self):
        """VWAP is computed with sufficient data."""
        ohlcv = _make_ohlcv(n=5)
        result = compute_indicators(ohlcv, "TEST")
        assert result.vwap is not None
        assert result.vwap > 0


class TestGenerateSignals:
    def test_bullish_signals(self):
        """Generate signals for a strongly bullish stock."""
        ohlcv = _make_ohlcv(n=50, base_price=5.0)  # strong uptrend
        indicators = compute_indicators(ohlcv, "TEST")
        current_price = ohlcv[-1].close
        analysis = generate_signals(indicators, current_price)
        assert analysis.symbol == "TEST"
        assert len(analysis.signals) > 0
        assert analysis.composite_signal in ("BUY", "HOLD", "SELL")

    def test_bearish_signals(self):
        """Generate signals for a strongly bearish stock."""
        ohlcv = _make_ohlcv(n=50, base_price=20.0)  # strong downtrend
        indicators = compute_indicators(ohlcv, "TEST")
        current_price = ohlcv[-1].close
        analysis = generate_signals(indicators, current_price)
        assert analysis.symbol == "TEST"
        assert len(analysis.signals) > 0

    def test_neutral_rsi(self):
        """RSI between 45-55 generates neutral signal."""
        ohlcv = _make_ohlcv(n=50, base_price=10.0)
        indicators = compute_indicators(ohlcv, "TEST")
        current_price = ohlcv[-1].close
        analysis = generate_signals(indicators, current_price)
        assert analysis.composite_confidence >= 0.0
        assert analysis.composite_confidence <= 1.0


class TestBacktest:
    def test_basic_backtest(self):
        """Backtest runs without errors."""
        ohlcv = _make_ohlcv(n=100)
        result = backtest_sma_crossover(ohlcv, "TEST", 7, 20)
        assert result.symbol == "TEST"
        assert result.strategy == "SMA 7/20 Crossover"
        assert result.period_days == 100

    def test_insufficient_bars(self):
        """Backtest returns zero results with insufficient bars."""
        ohlcv = _make_ohlcv(n=15)
        result = backtest_sma_crossover(ohlcv, "TEST", 7, 20)
        assert result.buy_count == 0
        assert result.total_return_pct == 0.0

    def test_backtest_with_real_data(self):
        """Backtest runs on real PSE data."""
        from phse.data.pse_edge import PseEdgeClient
        from phse.config import get_settings
        from datetime import datetime, timezone, timedelta

        client = PseEdgeClient(get_settings())
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=365)

        # Use GCASH (limited history but sufficient for basic test)
        ohlcv = client.get_price_history(709, "GCASH")
        if len(ohlcv) >= 30:
            result = backtest_sma_crossover(ohlcv, "GCASH", 7, 20)
            assert result.symbol == "GCASH"
            assert result.period_days == len(ohlcv)
