"""PSE data module.

Provides multiple data sources with automatic fallback:
- PseEdgeClient: Full-featured (quotes, history, fundamentals) via edge.pse.com.ph
- FramesPseClient: Lightweight snapshot parser via frames.pse.com.ph
- UnifiedPseClient: Auto-fallback between sources
"""

from .exceptions import PseCacheError, PseHttpError, PseScrapeError
from .frames_pse import FramesPseClient
from .models import OHLCV, AnalysisResult, Company, Quote, TechnicalSignal
from .pse_edge import PseEdgeClient
from .unified import UnifiedPseClient

__all__ = [
    "OHLCV",
    "AnalysisResult",
    "Company",
    "FramesPseClient",
    "PseCacheError",
    "PseEdgeClient",
    "PseHttpError",
    "PseScrapeError",
    "Quote",
    "TechnicalSignal",
    "UnifiedPseClient",
]
