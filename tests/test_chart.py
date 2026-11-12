"""Tests for chart module."""

from datetime import date, timedelta

import pytest

from phse.chart.renderer import render_chart
from phse.data.models import OHLCV


def _make_ohlcv(n: int = 50, base_price: float = 10.0) -> list[OHLCV]:
    """Generate synthetic OHLCV data for testing."""
    data = []
    for i in range(n):
        price = base_price * (1 + 0.01 * (i - n // 4))
        data.append(OHLCV(
            date=date(2026, 1, 1) + timedelta(days=i),
            open=max(0.01, price * 0.99),
            high=price * 1.02,
            low=max(0.01, price * 0.98),
            close=price,
            volume=1000000 + i * 10000,
        ))
    return data


class TestRenderChart:
    def test_render_basic(self):
        """Render a basic chart without indicators."""
        ohlcv = _make_ohlcv(n=50)
        chart = render_chart("TEST", ohlcv)
        assert chart is not None
        # Chart object is created successfully
        assert hasattr(chart, 'candle_data') or hasattr(chart, 'data')

    def test_render_with_indicators(self):
        """Render a chart with indicator overlays."""
        from phse.analysis import compute_indicators

        ohlcv = _make_ohlcv(n=50)
        indicators = compute_indicators(ohlcv, "TEST")
        chart = render_chart("TEST", ohlcv, indicators)
        assert chart is not None
        assert len(chart.candle_data) == 50

    def test_render_empty_raises(self):
        """Rendering empty OHLCV raises ValueError."""
        with pytest.raises(ValueError, match="No OHLCV data"):
            render_chart("TEST", [])

    def test_render_small_data(self):
        """Rendering data with < 20 bars still works."""
        ohlcv = _make_ohlcv(n=5)
        chart = render_chart("TEST", ohlcv)
        assert chart is not None
        assert len(chart.candle_data) == 5

    def test_chart_has_volume(self):
        """Chart has volume data configured."""
        ohlcv = _make_ohlcv(n=50)
        chart = render_chart("TEST", ohlcv)
        # Chart object is created successfully with volume
        assert chart is not None
        assert hasattr(chart, 'volume_config')
