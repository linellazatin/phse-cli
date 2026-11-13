"""Chart rendering using lightweight-charts-python."""

from __future__ import annotations

import pandas as pd


# Patch pandas 3.x compatibility bug in lightweight-charts
# Pandas 3.x stores datetime precision in microseconds instead of nanoseconds,
# breaking the timestamp conversion that lightweight-charts expects.
def _apply_lc_patch():
    from lightweight_charts.abstract import AbstractChart, SeriesCommon

    def _df_datetime_format_fixed(self, df, exclude_lowercase=None):
        df = df.copy()
        list(df.columns)
        df.columns = self._format_labels(df, df.columns, df.index, exclude_lowercase)
        if not pd.api.types.is_datetime64_any_dtype(df['time']):
            df['time'] = pd.to_datetime(df['time'])
        has_intraday = not df['time'].dt.time.eq(pd.Timestamp('00:00:00').time()).all()
        if not has_intraday:
            df['time'] = df['time'].dt.strftime('%Y-%m-%d')
            return df
        self._set_interval(df)
        raw_int = df['time'].astype('int64')
        if raw_int.iloc[0] > 1e16:
            df['time'] = raw_int // 10 ** 9
        else:
            df['time'] = raw_int // 10 ** 6
        return df

    AbstractChart._df_datetime_format = _df_datetime_format_fixed
    SeriesCommon._df_datetime_format = _df_datetime_format_fixed

_apply_lc_patch()

from lightweight_charts import Chart

from ..data.models import OHLCV


def render_chart(
    symbol: str,
    ohlcv: list[OHLCV],
    indicators: object | None = None,
    title: str = "",
) -> Chart:
    """Render an interactive candlestick chart with optional indicator overlays.

    Returns a Chart object (does not block). Caller can call chart.show(block=True)
    to display the chart.
    """
    if not ohlcv:
        raise ValueError("No OHLCV data to chart")

    # Build DataFrame — going through set() ensures pandas 3.x datetime patch is applied
    df = pd.DataFrame([
        {
            "time": bar.date.strftime("%Y-%m-%d"),
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
        }
        for bar in ohlcv
    ])

    # Create chart
    chart_title = title or f"{symbol} — Candlestick Chart"
    chart = Chart(title=chart_title, width=1200, height=700)

    # Use set() so the pandas 3.x datetime fix is applied
    chart.set(df[["time", "open", "high", "low", "close", "volume"]])

    # Add indicator overlays if provided
    if indicators is not None:
        _add_indicators(chart, indicators, ohlcv)

    return chart


def _add_indicators(chart: Chart, indicators: object, ohlcv: list[OHLCV]) -> None:
    """Add indicator overlay lines to the chart."""

    def _add_line(name: str, value: float, color: str, width: int = 2, style: str = "solid") -> None:
        """Add a single indicator line. Column name must match line name."""
        df = pd.DataFrame([{
            "time": bar.date.strftime("%Y-%m-%d"),
            name: value,
        } for bar in ohlcv])
        line = chart.create_line(name=name, color=color, width=width, style=style)
        line.set(df)

    # SMA lines
    if hasattr(indicators, "sma_7") and indicators.sma_7 is not None:
        _add_line("SMA 7", indicators.sma_7, "rgba(255, 200, 50, 0.8)", 2)

    if hasattr(indicators, "sma_20") and indicators.sma_20 is not None:
        _add_line("SMA 20", indicators.sma_20, "rgba(50, 150, 255, 0.8)", 2)

    if hasattr(indicators, "sma_50") and indicators.sma_50 is not None:
        _add_line("SMA 50", indicators.sma_50, "rgba(255, 100, 50, 0.8)", 2)

    # Bollinger Bands
    if hasattr(indicators, "bb_upper") and indicators.bb_upper is not None:
        _add_line("BB Upper", indicators.bb_upper, "rgba(255, 100, 100, 0.6)", 1, "dashed")

    if hasattr(indicators, "bb_lower") and indicators.bb_lower is not None:
        _add_line("BB Lower", indicators.bb_lower, "rgba(100, 255, 100, 0.6)", 1, "dashed")
