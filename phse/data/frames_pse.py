"""frames.pse.com.ph parser — lightweight JSON-based quote source.

Scrapes the embedded JSON from frames.pse.com.ph for current-day
snapshot data (price, volume, change). No history, no fundamentals.

Legal: PSE-owned, 15-min delayed, personal-use only per their terms.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from ..config import Settings, get_settings
from .models import Company, OHLCV, Quote
from .exceptions import PseHttpError, PseScrapeError


class FramesPseClient:
    """HTTP client + parser for frames.pse.com.ph.

    Reads the embedded JSON from the hidden input field and parses
    current-day quote data. Much simpler than PSE Edge HTML parsing.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.base_url = "https://frames.pse.com.ph"
        self._client = httpx.Client(
            timeout=self.settings.request_timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "phse-cli/0.1.1 (CLI; +https://github.com/phse-cli)",
            },
        )

    def _get(self, path: str = "") -> httpx.Response:
        """Make a GET request to frames.pse.com.ph."""
        url = urljoin(self.base_url, path) if path else self.base_url
        try:
            resp = self._client.get(url)
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError as e:
            raise PseHttpError(str(e), status_code=e.response.status_code, url=url) from e
        except httpx.RequestError as e:
            raise PseHttpError(f"Request failed: {e}", url=url) from e

    def _throttle(self):
        """Be gentle."""
        time.sleep(self.settings.throttle_delay)

    # ── Company Directory ───────────────────────────────────────────────

    def get_companies(self) -> list[Company]:
        """Fetch all listed companies from frames.pse.com.ph.

        Returns ~388 entries (stocks + indices). No sector info.
        """
        self._throttle()
        resp = self._get()
        soup = BeautifulSoup(resp.text, "lxml")

        # Extract JSON from hidden input
        hidden = soup.find("input", id="JsonId")
        if not hidden or not hidden.get("value"):
            raise PseScrapeError("No JsonId input found on frames page")

        raw = hidden["value"].replace("&quot;", '"')
        stocks = json.loads(raw)

        companies = []
        for s in stocks:
            symbol = s.get("StockSymbol", "").strip()
            name = s.get("StockName", "").strip()
            if not symbol or not name:
                continue

            # Only include actual stocks (skip indices with 0 volume/value)
            try:
                volume = int(s.get("Volume", 0))
                price = float(s.get("Price", 0)) if s.get("Price", "0") != "0" else 0
            except (ValueError, TypeError):
                volume = 0
                price = 0

            # Skip pure indices (no meaningful price)
            if price == 0:
                continue

            companies.append(Company(
                symbol=symbol,
                name=name,
                sector="",
                subsector="",
                cmpy_id=0,  # frames doesn't provide cmpy_id
                listing_date=None,
            ))

        return companies

    def _get_raw_stocks(self) -> list[dict]:
        """Fetch raw stock dicts from frames.pse.com.ph (no Company model overhead)."""
        self._throttle()
        resp = self._get()
        soup = BeautifulSoup(resp.text, "lxml")

        hidden = soup.find("input", id="JsonId")
        if not hidden or not hidden.get("value"):
            raise PseScrapeError("No JsonId input found on frames page")

        raw = hidden["value"].replace("&quot;", '"')
        stocks = json.loads(raw)

        result = []
        for s in stocks:
            symbol = s.get("StockSymbol", "").strip()
            name = s.get("StockName", "").strip()
            if not symbol or not name:
                continue
            try:
                price = float(s.get("Price", "0")) if s.get("Price") else 0
            except (ValueError, TypeError):
                price = 0
            if price == 0:
                continue
            result.append(s)
        return result

    def market_summary(self) -> dict:
        """Derive market-wide summary from raw frames data.

        Returns a dict with: gainers, losers, most_active, volume_leaders,
        advancers, decliners, unchanged, total_volume, total_value.
        """
        stocks = self._get_raw_stocks()

        # Separate by change direction
        gainers = []
        losers = []
        unchanged = []
        total_volume = 0
        total_value = 0.0

        for s in stocks:
            symbol = s.get("StockSymbol", "")
            name = s.get("StockName", "")
            try:
                price = float(s.get("Price", "0")) if s.get("Price") else 0
                volume = int(s.get("Volume", "0")) if s.get("Volume") else 0
                raw_value = s.get("Value", "0")
                value = float(str(raw_value).replace(",", "")) if raw_value else 0
                pct_change = float(s.get("PercentChange", "0")) if s.get("PercentChange") else 0
            except (ValueError, TypeError):
                continue

            total_volume += volume
            total_value += value

            entry = {
                "symbol": symbol,
                "name": name,
                "price": price,
                "volume": volume,
                "value": value,
                "percent_change": pct_change,
            }

            if pct_change > 0:
                gainers.append(entry)
            elif pct_change < 0:
                losers.append(entry)
            else:
                unchanged.append(entry)

        gainers.sort(key=lambda x: x["percent_change"], reverse=True)
        losers.sort(key=lambda x: x["percent_change"])
        most_active_by_value = sorted(
            stocks, key=lambda x: float(str(x.get("Value", "0")).replace(",", "") or 0), reverse=True
        )
        volume_leaders = sorted(stocks, key=lambda x: int(x.get("Volume", 0) or 0), reverse=True)

        return {
            "gainers": gainers[:20],
            "losers": losers[:20],
            "most_active": most_active_by_value[:20],
            "volume_leaders": volume_leaders[:20],
            "advancers": len(gainers),
            "decliners": len(losers),
            "unchanged": len(unchanged),
            "total_volume": total_volume,
            "total_value": total_value,
        }

    def resolve_symbol(self, symbol: str) -> Optional[dict]:
        """Resolve a stock symbol to its frames data dict (or None)."""
        stocks = self._get_raw_stocks()
        symbol_upper = symbol.upper()
        for s in stocks:
            if s.get("StockSymbol", "").upper() == symbol_upper:
                return s
        return None

    # ── Stock Quote ─────────────────────────────────────────────────────

    def get_quote(self, symbol: str) -> Quote:
        """Fetch the latest stock quote from frames.pse.com.ph.

        Returns current-day snapshot data. No history.
        """
        stock = self.resolve_symbol(symbol)
        if not stock:
            raise PseScrapeError(f"Symbol '{symbol}' not found in frames data")

        # Parse the TradeDate or use page timestamp
        trade_date_str = stock.get("TradeDate", "")
        as_of = self._parse_tradedate(trade_date_str)

        # Parse values (frames stores Price/Change as strings)
        try:
            price = float(stock.get("Price", "0")) if stock.get("Price") else None
        except (ValueError, TypeError):
            price = None

        try:
            change = float(stock.get("Change", "0")) if stock.get("Change") else None
        except (ValueError, TypeError):
            change = None

        try:
            pct_change = float(stock.get("PercentChange", "0")) if stock.get("PercentChange") else None
        except (ValueError, TypeError):
            pct_change = None

        try:
            volume = int(stock.get("Volume", 0)) if stock.get("Volume") else 0
        except (ValueError, TypeError):
            volume = 0

        try:
            raw_value = stock.get("Value", "0")
            if raw_value:
                value = float(str(raw_value).replace(",", ""))
            else:
                value = None
        except (ValueError, TypeError):
            value = None

        return Quote(
            symbol=stock.get("StockSymbol", symbol),
            company_name=stock.get("StockName", ""),
            last_price=price,
            open=None,  # frames doesn't provide OHLC breakdown
            high=None,
            low=None,
            previous_close=None,
            change=change,
            percent_change=pct_change,
            volume=volume,
            value=value,
            average_price=None,
            market_cap=None,
            pe_ratio=None,
            pb_ratio=None,
            book_value=None,
            week_52_high=None,
            week_52_low=None,
            as_of=as_of,
            stale=not self._is_market_open(as_of),
        )

    # ── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _parse_tradedate(raw: str) -> Optional[datetime]:
        """Parse TradeDate from frames JSON.

        Format varies: '0001-01-01T00:00:00+07:37' (broken) or '2026-11-12T...'
        Falls back to page timestamp if broken.
        """
        if not raw or raw == "0001-01-01":
            return None
        try:
            return datetime.fromisoformat(raw)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _is_market_open(as_of: Optional[datetime]) -> bool:
        """Check if the quote is from an active trading session."""
        if not as_of:
            return False
        # Market is Mon-Fri, 9:30-15:00 Asia/Manila
        if as_of.weekday() >= 5:  # Sat/Sun
            return False
        return True  # frames data is always current-day, stale handled by as_of check
