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
                if self.use_unified:
                    quote = self.client.get_quote(company.symbol)
                else:
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

    def bulk_scan(self,
                  sector: str | None = None,
                  min_price: float | None = None,
                  max_price: float | None = None,
                  min_volume: int | None = None,
                  top_gainers: bool = False,
                  top_losers: bool = False,
                  most_active: bool = False,
                  limit: int = 50,
                  enrich: bool = False,
                  symbols: set[str] | None = None) -> tuple[list[ScanResult], str]:
        """Fast bulk scan using frames.pse.com.ph single-response data.

        Fetches all 300+ stocks in one HTTP call, processes in-memory.
        Optionally enriches with pse_edge for market_cap/P-E.

        Returns (results, source) where source indicates data origin.
        """
        from ..data.frames_pse import FramesPseClient

        frames = FramesPseClient(self.settings)
        stocks = frames._get_raw_stocks()
        if not stocks:
            return [], "frames"

        # Build sector lookup from pse_edge (only when enrich=True)
        sector_map: dict[str, str] = {}
        subsector_map: dict[str, str] = {}
        if enrich:
            try:
                companies = self.client.get_companies()
                sector_map = {c.symbol.upper(): c.sector for c in companies if c.sector}
                subsector_map = {c.symbol.upper(): c.subsector for c in companies if c.subsector}
            except Exception:
                pass

        # Build market cap lookup from pse_edge (via unified for speed)
        mcap_map: dict[str, float] = {}
        pe_map: dict[str, float] = {}
        if enrich:
            try:
                from ..data.pse_edge import PseEdgeClient
                edge = PseEdgeClient(self.settings)
                # Only enrich symbols that were requested, or first N results
                target_symbols = symbols if symbols else set()
                if not target_symbols:
                    # No specific symbols requested: enrich first 50
                    target_symbols = {s.get("StockSymbol", "").strip().upper()
                                      for s in stocks[:50]}
                for sym in target_symbols:
                    # Use unified client to resolve (frames first = faster)
                    company = self.client.resolve_symbol(sym)
                    if company and company.cmpy_id:
                        try:
                            q = edge.get_quote(company.cmpy_id, company.symbol)
                            if q.market_cap:
                                mcap_map[sym] = q.market_cap
                            if q.pe_ratio:
                                pe_map[sym] = q.pe_ratio
                        except Exception:
                            pass
            except Exception:
                pass

        # Process stocks from frames data
        results = []
        for s in stocks:
            symbol = s.get("StockSymbol", "").strip().upper()
            name = s.get("StockName", "").strip()

            try:
                price = float(s.get("Price", "0")) if s.get("Price") else None
                change = float(s.get("Change", "0")) if s.get("Change") else None
                pct_change = float(s.get("PercentChange", "0")) if s.get("PercentChange") else None
                volume = int(s.get("Volume", "0")) if s.get("Volume") else 0
                raw_value = s.get("Value", "0")
                value = float(str(raw_value).replace(",", "")) if raw_value else None
            except (ValueError, TypeError):
                continue

            results.append(ScanResult(
                symbol=symbol,
                company_name=name,
                last_price=price,
                change=change,
                percent_change=pct_change,
                volume=volume,
                value=value,
                market_cap=mcap_map.get(symbol),
                sector=sector_map.get(symbol, ""),
                subsector=subsector_map.get(symbol, ""),
                pe_ratio=pe_map.get(symbol),
            ))

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

        source = "frames+edge" if enrich else "frames"
        return results[:limit], source

    def scan_symbols(self, symbols: set[str], enrich: bool = False) -> list[ScanResult]:
        """Quick lookup: fetch quotes for specific symbols via unified client."""
        if not symbols:
            return []

        # Build company name lookup (more reliable than quote parsing)
        name_map: dict[str, str] = {}
        try:
            companies = self.client.get_companies()
            name_map = {c.symbol.upper(): c.name for c in companies}
        except Exception:
            pass

        results = []
        for sym in symbols:
            try:
                if self.use_unified:
                    q = self.client.get_quote(sym)
                else:
                    company = self.client.resolve_symbol(sym)
                    if company:
                        q = self.client.get_quote(company.cmpy_id, company.symbol)
                    else:
                        continue
                # Use company name from company list (more reliable)
                company_name = name_map.get(sym.upper(), q.company_name or sym)
                results.append(ScanResult(
                    symbol=q.symbol,
                    company_name=company_name,
                    last_price=q.last_price,
                    change=q.change,
                    percent_change=q.percent_change,
                    volume=q.volume,
                    value=q.value,
                    market_cap=q.market_cap,
                    pe_ratio=q.pe_ratio,
                ))
            except Exception:
                continue
        return results
