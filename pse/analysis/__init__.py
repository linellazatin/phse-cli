"""Analysis package — technical indicators and signal generation."""

from .backtest import backtest_sma_crossover
from .indicators import compute_indicators
from .models import AnalysisResult, IndicatorResult, Signal
from .signals import generate_signals

__all__ = ["compute_indicators", "generate_signals", "backtest_sma_crossover",
           "IndicatorResult", "Signal", "AnalysisResult"]
