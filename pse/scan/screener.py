"""Scanner module for PSE stock screening."""

from __future__ import annotations

from typing import Optional

from .config import Settings, get_settings
from .data.models import ScanResult
from .data.pse_edge import PseEdgeClient


class StockScreener:
    """Screen PSE stocks by various criteria."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.client = PseEdgeClient(self.settings)

    def scan(self,
             sector: Optional[str] = None,
             min_price: Optional[float] = None,
             max_price: Optional[float] = None,
             min_volume: Optional[int] = None,
             top_gainers: bool = False,
             top_losers: bool = False,
             limit: int = 50) -> list[ScanResult]:
        """Run a stock screen with the given filters.

        Returns results sorted by the active criteria.
        """
        # Get all companies
        companies = self.client.get_companies()
        if not companies:
            return []

        # Fetch quotes
        results = []
        for company in companies:
            try:
                quote = self.client.get_quote(company.cmpy_id, company.symbol)
                results.append(ScanResult(
                    symbol=quote.symbol,
                    company_name=quote.company_name,
                    last_price=quote.last_price,
                    change=quote.change,
                    percent_change=quote.percent_change,
                    volume=quote.volume,
                    market_cap=quote.market_cap,
                    sector=company.sector,
                    pe_ratio=quote.pe_ratio,
                ))
            except Exception:
                continue

        # Apply filters
        if sector:
            results = [r for r in results
                       if sector.lower() in (r.sector or "").lower()]

        if min_price:
            results = [r for r in results if (r.last_price or 0) >= min_price]

        if max_price:
            results = [r for r in results if (r.last_price or float("inf")) <= max_price]

        if min_volume:
            results = [r for r in results if (r.volume or 0) >= min_volume]

        # Sort
        if top_gainers:
            results.sort(key=lambda r: r.percent_change or 0, reverse=True)
        elif top_losers:
            results.sort(key=lambda r: r.percent_change or 0)
        else:
            results.sort(key=lambda r: r.symbol)

        return results[:limit]
