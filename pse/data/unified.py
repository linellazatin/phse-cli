"""Unified PSE client with automatic source fallback.

Tries frames_pse first (lightweight, fast), falls back to pse_edge
(full-featured) when frames data is unavailable or history is needed.
"""

from __future__ import annotations

from typing import Optional

from ..config import Settings, get_settings
from .models import Company, OHLCV, Quote
from .pse_edge import PseEdgeClient
from .frames_pse import FramesPseClient


class UnifiedPseClient:
    """Client that uses frames_pse as primary, pse_edge as backup.

    Strategy:
    - Quotes: frames_pse first (fast, clean JSON), pse_edge fallback (richer data)
    - History: pse_edge only (frames has no history)
    - Company list: frames_pse first (388 entries), pse_edge fallback (284, with sector)
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.frames = FramesPseClient(settings)
        self.edge = PseEdgeClient(settings)

    # ── Company Directory ───────────────────────────────────────────────

    def get_companies(self) -> list[Company]:
        """Fetch companies from frames_pse, falling back to pse_edge."""
        try:
            return self.frames.get_companies()
        except Exception as e:
            return self.edge.get_companies()

    def resolve_symbol(self, symbol: str) -> Optional[Company]:
        """Resolve symbol from frames_pse, falling back to pse_edge."""
        # Try frames first (includes more symbols, including indices)
        stock = self.frames.resolve_symbol(symbol)
        if stock:
            return Company(
                symbol=stock.get("StockSymbol", symbol),
                name=stock.get("StockName", ""),
            )
        # Fallback to pse_edge (has cmpy_id, sector info)
        return self.edge.resolve_symbol(symbol)

    # ── Stock Quote ─────────────────────────────────────────────────────

    def get_quote(self, symbol: str) -> Quote:
        """Fetch quote from frames_pse, enrich with pse_edge data.

        Uses frames_pse for speed, then enriches with pse_edge for
        richer data (OHLC, market cap, P/E, etc.). Falls back to
        pse_edge-only if frames is down.
        """
        base_quote = None
        try:
            base_quote = self.frames.get_quote(symbol)
        except Exception:
            pass

        # Enrich with pse_edge data
        company = self.edge.resolve_symbol(symbol)
        if company:
            enriched = self.edge.get_quote(company.cmpy_id, symbol)
            # Merge: frames for price/volume, pse_edge for everything else
            if base_quote:
                enriched.last_price = base_quote.last_price
                enriched.change = base_quote.change
                enriched.percent_change = base_quote.percent_change
                enriched.volume = base_quote.volume
                enriched.value = base_quote.value
                enriched.as_of = base_quote.as_of
                enriched.stale = base_quote.stale
            return enriched

        if base_quote:
            return base_quote
        raise Exception(f"Could not resolve symbol: {symbol}")

    # ── Price History ───────────────────────────────────────────────────

    def get_price_history(self, symbol: str, period: str = "1m") -> list[OHLCV]:
        """Fetch price history from pse_edge (frames has no history)."""
        company = self.edge.resolve_symbol(symbol)
        if not company:
            return []
        return self.edge.get_price_history(company.cmpy_id, symbol, period)
