"""PSE Edge scraper — fetch and parse data from edge.pse.com.ph."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from ..config import Settings, get_settings
from .exceptions import PseHttpError
from .models import OHLCV, Company, Quote


@dataclass
class HealthCheckResult:
    """Result of a PSE Edge health check."""
    healthy: bool
    entry_count: int = 0
    error: str | None = None


# Module-level health check cache: {timestamp: HealthCheckResult}
_health_cache: dict[str, tuple[HealthCheckResult, float]] = {}


class PseEdgeClient:
    """HTTP client + parser for PSE Edge endpoints."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.base_url = self.settings.pse_base_url
        self._client = httpx.Client(
            timeout=self.settings.request_timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "phse-cli/0.1.1 (CLI; +https://github.com/phse-cli)",
                "Accept": "text/html,application/xhtml+xml,application/json,*/*",
            },
        )

    def _get(self, path: str, params: dict | None = None) -> httpx.Response:
        """Make a GET request to PSE Edge."""
        url = urljoin(self.base_url, path)
        try:
            resp = self._client.get(url, params=params)
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError as e:
            raise PseHttpError(str(e), status_code=e.response.status_code, url=url) from e
        except httpx.RequestError as e:
            raise PseHttpError(f"Request failed: {e}", url=url) from e

    def _post(self, path: str, data: dict | None = None,
              json: dict | None = None) -> httpx.Response:
        """Make a POST request to PSE Edge."""
        url = urljoin(self.base_url, path)
        try:
            resp = self._client.post(url, data=data, json=json)
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError as e:
            raise PseHttpError(str(e), status_code=e.response.status_code, url=url) from e
        except httpx.RequestError as e:
            raise PseHttpError(f"Request failed: {e}", url=url) from e

    def _throttle(self):
        """Throttle requests to be gentle on PSE Edge."""
        time.sleep(self.settings.throttle_delay)

    # ── Company Directory ───────────────────────────────────────────────

    def get_companies(self) -> list[Company]:
        """Fetch the list of all listed companies from PSE Edge.

        Uses the search.ax endpoint which returns paginated results.
        """
        cached = None
        try:
            from .cache import Cache
            cache = Cache(self.settings)
            cached = cache.get("companies")
        except Exception:
            pass

        if cached:
            return [Company(**c) for c in cached]

        companies = []
        page = 1
        total_pages = 1

        while page <= total_pages:
            self._throttle()
            resp = self._post("/companyDirectory/search.ax", data={"pageNo": str(page)})
            soup = BeautifulSoup(resp.text, "lxml")

            # Parse total pages from count
            count_span = soup.find("span", class_="count")
            if count_span:
                count_text = count_span.get_text()
                page_match = re.search(r"\[\s*(\d+)\s*/\s*(\d+)\s*\]", count_text)
                if page_match:
                    total_pages = int(page_match.group(2))

            # Parse company table
            table = soup.find("table", class_="list")
            if not table:
                break

            tbody = table.find("tbody")
            if not tbody:
                break

            for row in tbody.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if len(cells) < 5:
                    continue

                cells_text = [c.get_text(strip=True) for c in cells]
                name = cells_text[0]
                symbol = cells_text[1]
                sector = cells_text[2]
                subsector = cells_text[3]
                listing_str = cells_text[4]

                # Extract cmpy_id from cmDetail onclick
                link = row.find("a")
                cmpy_id = 0
                if link:
                    onclick = link.get("onclick", "")
                    match = re.search(r"cmDetail\('\s*(\d+)\s*'", onclick)
                    if match:
                        cmpy_id = int(match.group(1))

                # Parse listing date
                listing_date = None
                if listing_str:
                    try:
                        listing_date = datetime.strptime(listing_str, "%b %d, %Y").date()
                    except ValueError:
                        pass

                if symbol and cmpy_id > 0:
                    companies.append(Company(
                        symbol=symbol,
                        name=name,
                        sector=sector,
                        subsector=subsector,
                        cmpy_id=cmpy_id,
                        listing_date=listing_date,
                    ))

            page += 1
            if page > 20:  # safety limit
                break

        # Cache the result
        try:
            from .cache import Cache
            cache = Cache(self.settings)
            cache.set("companies", [c.model_dump() for c in companies],
                      ttl_seconds=self.settings.cache_ttl_eod_seconds)
        except Exception:
            pass

        return companies

    def resolve_symbol(self, symbol: str) -> Company | None:
        """Resolve a stock symbol to a Company by searching the directory."""
        companies = self.get_companies()
        symbol_upper = symbol.upper()
        for company in companies:
            if company.symbol.upper() == symbol_upper:
                return company
        return None

    # ── Stock Quote ─────────────────────────────────────────────────────

    def get_quote(self, cmpy_id: int, symbol: str = "") -> Quote:
        """Fetch the latest stock quote for a company."""
        # If only symbol is provided, resolve to cmpy_id
        if cmpy_id == 0 and symbol:
            company = self.resolve_symbol(symbol)
            if company:
                cmpy_id = company.cmpy_id
                symbol = company.symbol
        elif cmpy_id == 0 and not symbol:
            raise ValueError("Either cmpy_id or symbol must be provided")

        self._throttle()
        resp = self._get(f"/companyPage/stockData.do?cmpy_id={cmpy_id}")
        soup = BeautifulSoup(resp.text, "lxml")

        # Parse the quote data from the page
        quote_data = self._parse_quote_page(soup)
        quote_data["symbol"] = symbol
        quote_data["cmpy_id"] = cmpy_id
        return Quote(**quote_data)

    def _parse_quote_page(self, soup: BeautifulSoup) -> dict:
        """Parse stock quote data from the HTML page.

        The quote table has 6 cells per row: label, value, label, value, label, value.
        """
        result = {
            "company_name": "",
            "last_price": None,
            "open": None,
            "high": None,
            "low": None,
            "previous_close": None,
            "change": None,
            "percent_change": None,
            "volume": None,
            "value": None,
            "average_price": None,
            "market_cap": None,
            "pe_ratio": None,
            "pb_ratio": None,
            "book_value": None,
            "week_52_high": None,
            "week_52_low": None,
            "as_of": None,
        }

        # Company name
        title = soup.find("h1") or soup.find("div", class_=re.compile(r"company-name|title"))
        if title:
            result["company_name"] = title.get_text(strip=True)

        # Find the quote table: has 3+ rows with 6 cells each
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) >= 3:
                for row in rows:
                    cells = row.find_all(["td", "th"])
                    if len(cells) == 6:
                        self._extract_quote_fields(result, cells)
                    elif len(cells) == 4:
                        self._extract_metadata_fields(result, cells)

        # Extract company name from the page header
        if not result["company_name"]:
            h2 = soup.find("h2")
            if h2:
                result["company_name"] = h2.get_text(strip=True)
            else:
                # Try to get from the company directory page title
                title = soup.find("title")
                if title and title.string:
                    result["company_name"] = title.string.strip()

        # Parse change from text if not directly available
        if result["change"] is None and result["last_price"] and result["previous_close"]:
            result["change"] = result["last_price"] - result["previous_close"]
            if result["previous_close"]:
                result["percent_change"] = (result["change"] / result["previous_close"]) * 100

        return result

    def _extract_quote_fields(self, result: dict, cells) -> None:
        """Extract quote fields from a row of 6 cells (label, value, label, value, label, value)."""
        for i in range(0, len(cells), 2):
            if i + 1 >= len(cells):
                break
            label = cells[i].get_text(strip=True).rstrip(":").lower()
            value_text = cells[i + 1].get_text(strip=True).replace("\xa0", " ")
            value = self._parse_float(value_text)

            if "last" in label and "traded" in label:
                result["last_price"] = value
            elif label == "open":
                result["open"] = value
            elif label == "high":
                result["high"] = value
            elif label == "low":
                result["low"] = value
            elif "previous" in label and "close" in label:
                result["previous_close"] = value
            elif "change" in label:
                # Handle multi-line: "down \n   0.100\n  ( 1.46%)"
                change_match = re.search(r"([+-]?[\d,]+\.?\d*)\s*\(\s*([\d.]+)%\s*\)", value_text.replace("\n", " "))
                if change_match:
                    result["change"] = self._parse_float(change_match.group(1))
                    result["percent_change"] = self._parse_percent(change_match.group(2))
                else:
                    result["change"] = value
            elif label == "volume":
                result["volume"] = self._parse_int(value_text)
            elif label == "value" and "average" not in label:
                result["value"] = value
            elif "average" in label:
                result["average_price"] = value
            elif "market" in label and "cap" in label:
                result["market_cap"] = self._parse_float(value_text.replace("%", ""))
            elif "pe" in label:
                result["pe_ratio"] = value
            elif "sector" in label and "pe" in label:
                result["sector_pe"] = value
            elif "pb" in label or "book value" in label:
                result["pb_ratio"] = value
            elif "book" in label and "value" in label:
                result["book_value"] = value
            elif "52" in label and "high" in label:
                result["week_52_high"] = value
            elif "52" in label and "low" in label:
                result["week_52_low"] = value
            elif "outstanding" in label or "listed" in label:
                result["outstanding_shares"] = self._parse_int(value_text.replace(",", ""))
            elif "foreign" in label:
                result["foreign_limit"] = self._parse_float(value_text.replace("%", ""))

    def _extract_metadata_fields(self, result: dict, cells) -> None:
        """Extract metadata fields from a row of 4 cells (label, value, label, value)."""
        for i in range(0, len(cells), 2):
            if i + 1 >= len(cells):
                break
            label = cells[i].get_text(strip=True).rstrip(":").lower()
            value_text = cells[i + 1].get_text(strip=True).replace("\xa0", " ")
            value = self._parse_float(value_text)

            if "market" in label and ("cap" in label or "capitalization" in label):
                result["market_cap"] = self._parse_float(value_text.replace(",", ""))
            elif "outstanding" in label:
                result["outstanding_shares"] = self._parse_int(value_text.replace(",", ""))
            elif "listed" in label and "shares" in label:
                result["listed_shares"] = self._parse_int(value_text.replace(",", ""))
            elif "issued" in label and "shares" in label:
                result["issued_shares"] = self._parse_int(value_text.replace(",", ""))
            elif "foreign" in label and ("limit" in label or "ownership" in label):
                result["foreign_limit"] = self._parse_float(value_text.replace("%", ""))
            elif "free float" in label:
                result["free_float"] = self._parse_float(value_text.replace("%", ""))
            elif "par value" in label:
                result["par_value"] = value
            elif "board lot" in label:
                result["board_lot"] = int(value) if value else None
            elif "issue type" in label:
                result["issue_type"] = value_text
            elif "isin" in label:
                result["isin"] = value_text
            elif "listing" in label and "date" in label:
                result["listing_date"] = value_text

    # ── Price History ───────────────────────────────────────────────────

    def get_price_history(self, cmpy_id: int, symbol: str = "",
                          period: str = "1m") -> list[OHLCV]:
        """Fetch historical price data for a company.

        Args:
            cmpy_id: Company ID from PSE Edge
            symbol: Stock symbol
            period: Time period - 1m, 3m, 6m, 1y

        Returns:
            List of OHLCV data points
        """
        # If only symbol is provided, resolve to cmpy_id
        if cmpy_id == 0 and symbol:
            company = self.resolve_symbol(symbol)
            if company:
                cmpy_id = company.cmpy_id
                symbol = company.symbol
        elif cmpy_id == 0 and not symbol:
            return []

        # Map period to date range
        end_date = datetime.now(UTC).date()
        periods = {
            "1m": 30,
            "3m": 90,
            "6m": 180,
            "1y": 365,
        }
        days = periods.get(period, 30)
        start_date = end_date - timedelta(days=max(1, days - 1))

        # Try cached data first
        try:
            from .cache import Cache
            cache = Cache(self.settings)
            cached = cache.get_ohlcv(
                symbol or str(cmpy_id),
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
            )
            if cached:
                return [OHLCV(**bar) for bar in cached]
        except Exception:
            pass

        self._throttle()

        # Fetch from PSE Edge chart endpoint
        # The chart endpoint is typically: /companyPage/chart.do or similar
        # Try the stockData page which includes chart data
        resp = self._get(f"/companyPage/stockData.do?cmpy_id={cmpy_id}")
        soup = BeautifulSoup(resp.text, "lxml")

        # Look for chart data in the page (usually in a JSON script tag or table)
        ohlcv_data = self._parse_chart_data(soup, start_date, end_date)

        if not ohlcv_data:
            # Try AJAX chart endpoint
            ohlcv_data = self._fetch_chart_ajax(cmpy_id, start_date, end_date)

        # Cache the data
        if ohlcv_data:
            try:
                from .cache import Cache
                cache = Cache(self.settings)
                cache.set_ohlcv(symbol or str(cmpy_id),
                                [bar.model_dump() for bar in ohlcv_data])
            except Exception:
                pass

        return ohlcv_data

    def _parse_chart_data(self, soup: BeautifulSoup,
                          start_date, end_date) -> list[OHLCV]:
        """Parse OHLCV data from the stock data page."""
        ohlcv = []

        # Look for chart data in script tags (JSON data)
        for script in soup.find_all("script"):
            text = script.string or ""
            if "chartData" in text or "chart_data" in text or "priceData" in text:
                try:
                    data = json.loads(text)
                    if isinstance(data, dict) and "data" in data:
                        for point in data["data"]:
                            if isinstance(point, (list, tuple)) and len(point) >= 5:
                                try:
                                    date_str = str(point[0])
                                    # Parse date
                                    trade_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                                    if start_date <= trade_date <= end_date:
                                        ohlcv.append(OHLCV(
                                            date=trade_date,
                                            open=float(point[1]),
                                            high=float(point[2]),
                                            low=float(point[3]),
                                            close=float(point[4]),
                                            volume=int(point[5]) if len(point) > 5 else 0,
                                        ))
                                except (ValueError, IndexError):
                                    continue
                except json.JSONDecodeError:
                    pass

        # Also try to parse from a table
        if not ohlcv:
            table = soup.find("table", id="tblChart") or soup.find("table", class_=re.compile(r"chart"))
            if table:
                for row in table.find_all("tr")[1:]:  # skip header
                    cells = row.find_all("td")
                    if len(cells) >= 5:
                        try:
                            date_str = cells[0].get_text(strip=True)
                            trade_date = datetime.strptime(date_str, "%b %d, %Y").date()
                            if start_date <= trade_date <= end_date:
                                ohlcv.append(OHLCV(
                                    date=trade_date,
                                    open=float(cells[1].get_text(strip=True)),
                                    high=float(cells[2].get_text(strip=True)),
                                    low=float(cells[3].get_text(strip=True)),
                                    close=float(cells[4].get_text(strip=True)),
                                    volume=int(cells[5].get_text(strip=True).replace(",", ""))
                                    if len(cells) > 5 else 0,
                                ))
                        except (ValueError, IndexError):
                            continue

        return ohlcv

    def _fetch_chart_ajax(self, cmpy_id: int, start_date, end_date) -> list[OHLCV]:
        """Fetch chart data via the DisclosureCht AJAX endpoint."""
        ohlcv = []

        # Get security_id from the stockData page
        security_id = None
        try:
            resp = self._get(f"/companyPage/stockData.do?cmpy_id={cmpy_id}")
            soup = BeautifulSoup(resp.text, "lxml")
            sel = soup.find("select", attrs={"name": "security_id"})
            if sel:
                opt = sel.find("option", attrs={"selected": True})
                if opt:
                    security_id = opt.get("value")
        except Exception:
            pass

        if not security_id:
            return []

        # Use the correct endpoint with MM/DD/YYYY date format
        resp = self._post("/common/DisclosureCht.ax",
            json={
                "cmpy_id": str(cmpy_id),
                "security_id": security_id,
                "startDate": start_date.strftime("%m/%d/%Y"),
                "endDate": end_date.strftime("%m/%d/%Y"),
            })

        if resp.status_code != 200:
            return []

        data = resp.json()
        chart_data = data.get("chartData", [])

        for point in chart_data:
            try:
                date_str = point.get("CHART_DATE", "")
                trade_date = datetime.strptime(date_str, "%b %d, %Y %H:%M:%S").date()
                ohlcv.append(OHLCV(
                    date=trade_date,
                    open=float(point.get("OPEN", 0)),
                    high=float(point.get("HIGH", 0)),
                    low=float(point.get("LOW", 0)),
                    close=float(point.get("CLOSE", 0)),
                    volume=int(point.get("VALUE", 0)),
                ))
            except (ValueError, KeyError, TypeError):
                continue

        return ohlcv

    # ── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _parse_float(text: str) -> float | None:
        """Parse a float from text, handling commas, percentages, and trailing text."""
        if not text or text in {"N/A", "-"}:
            return None
        text = text.replace(",", "").replace("%", "").strip()
        # Extract leading number (handles "6.83\n    (Nov 11, 2026)")
        match = re.match(r"([+-]?[\d]*\.?\d+)", text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    @staticmethod
    def _parse_int(text: str) -> int | None:
        """Parse an integer from text, handling commas."""
        if not text or text in {"N/A", "-"}:
            return None
        text = text.replace(",", "")
        try:
            return int(float(text))
        except ValueError:
            return None

    @staticmethod
    def _parse_percent(text: str) -> float | None:
        """Parse a percentage value from text."""
        if not text:
            return None
        # Handle formats like "0.52%", "+0.52%", "-0.52%", "0.52"
        text = text.replace("%", "").strip()
        text = text.removeprefix("+")
        try:
            return float(text)
        except ValueError:
            return None

    # ── Health Check ──────────────────────────────────────────────────

    def health_check(self) -> HealthCheckResult:
        """Smoke test PSE Edge availability.

        Checks HTTP reachability and validates the company directory
        returns a plausible number of entries. Result is cached for
        5 minutes to avoid repeated pings.
        """
        now = time.time()
        cache_key = "edge_health"
        cached = _health_cache.get(cache_key)
        if cached and (now - cached[1]) < 300:
            return cached[0]

        try:
            resp = self._get("/companyDirectory/search.ax")
            if resp.status_code != 200:
                result = HealthCheckResult(healthy=False, error=f"HTTP {resp.status_code}")
                _health_cache[cache_key] = (result, now)
                return result

            soup = BeautifulSoup(resp.text, "lxml")
            count_span = soup.find("span", class_="count")
            entry_count = 0
            if count_span:
                count_text = count_span.get_text()
                page_match = re.search(r"\[\s*(\d+)\s*/\s*(\d+)\s*\]", count_text)
                if page_match:
                    entry_count = int(page_match.group(2))

            # Also count table rows as a sanity check
            table = soup.find("table", class_="list")
            if table:
                rows = table.find_all("tr")
                entry_count = max(entry_count, len(rows))

            result = HealthCheckResult(
                healthy=entry_count > 50,
                entry_count=entry_count,
            )
        except Exception as e:
            result = HealthCheckResult(healthy=False, error=str(e))

        _health_cache[cache_key] = (result, now)
        return result
