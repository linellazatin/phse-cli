"""Chart package — interactive charts via lightweight-charts-python."""

try:
    from .renderer import render_chart
except ImportError:
    render_chart = None  # type: ignore[misc,assignment]

__all__ = ["render_chart"]
