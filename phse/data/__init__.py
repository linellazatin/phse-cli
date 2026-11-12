"""PSE data module.

Provides multiple data sources with automatic fallback:
- PseEdgeClient: Full-featured (quotes, history, fundamentals) via edge.pse.com.ph
- FramesPseClient: Lightweight snapshot parser via frames.pse.com.ph
- UnifiedPseClient: Auto-fallback between sources
"""

from .pse_edge import PseEdgeClient
from .frames_pse import FramesPseClient
from .unified import UnifiedPseClient
from .models import Company, Quote, OHLCV, TechnicalSignal, AnalysisResult
from .exceptions import PseHttpError, PseScrapeError, PseCacheError

__all__ = [
    "PseEdgeClient",
    "FramesPseClient",
    "UnifiedPseClient",
    "Company",
    "Quote",
    "OHLCV",
    "TechnicalSignal",
    "AnalysisResult",
    "PseHttpError",
    "PseScrapeError",
    "PseCacheError",
]
