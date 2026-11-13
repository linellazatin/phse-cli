"""Scanner module for PSE stock screening."""

from __future__ import annotations

from ..config import Settings, get_settings
from ..data.models import ScanResult
from ..data.pse_edge import PseEdgeClient
from ..data.unified import UnifiedPseClient


class StockScreener:
    """Screen PSE stocks by various criteria."""

    def __init__(self, settings: Settings | None = None, use_unified: bool = True):
        self.settings = settings or get_settings()
        self.use_unified = use_unified
        if use_unified:
            self.client = UnifiedPseClient(self.settings)
        else:
            self.client = PseEdgeClient(self.settings)

    def scan(self,
             sector: str | None = None,
             min_price: float | None = None,
             max_price: float | None = None,
             min_volume: int | None = None,
             top_gainers: bool = False,
             top_losers: bool = False,
             most_active: bool = False,
             limit: int = 50) -> list[ScanResult]:
        """Run a stock screen with the given filters.

        Returns results sorted by the active criteria.
        """
        # Get all companies
        companies = self.client.get_companies()
        if not companies:
            return []

        # Build company lookup for names
        companies_by_symbol = {c.symbol.upper(): c for c in companies}

        # Fetch quotes
        results = []
        for company in companies:
            try:
                quote = self.client.get_quote(company.cmpy_id, company.symbol)
                company_name = companies_by_symbol.get(company.symbol.upper(), company).name
                # Use quote.value if available (from frames), otherwise calculate
                trade_value = quote.value
                if trade_value is None and quote.volume and quote.last_price:
                    trade_value = quote.volume * quote.last_price

                results.append(ScanResult(
                    symbol=quote.symbol,
                    company_name=company_name,
                    last_price=quote.last_price,
                    change=quote.change,
                    percent_change=quote.percent_change,
                    volume=quote.volume,
                    value=trade_value,
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
        elif most_active:
            results.sort(key=lambda r: r.value or 0, reverse=True)
        else:
            results.sort(key=lambda r: r.symbol)

        return results[:limit]
