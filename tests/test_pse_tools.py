"""Tests for PSE tools core functionality."""

from datetime import date, datetime, timedelta, timezone

import pytest
from bs4 import BeautifulSoup

from pse.config import get_settings
from pse.data.models import Company, Quote, OHLCV
from pse.data.pse_edge import PseEdgeClient
from pse.data.frames_pse import FramesPseClient
from pse.data.unified import UnifiedPseClient


class TestSettings:
    def test_default_settings(self):
        settings = get_settings()
        assert settings.cache_dir is not None
        assert settings.throttle_delay >= 0

    def test_cache_path_expands_user_home(self):
        settings = get_settings()
        assert str(settings.cache_dir).startswith("/")


class TestModels:
    def test_company_creation(self):
        company = Company(symbol="DMC", name="DMCI Holdings, Inc.", cmpy_id=188)
        assert company.symbol == "DMC"
        assert company.cmpy_id == 188

    def test_quote_creation(self):
        quote = Quote(symbol="DMC", company_name="DMCI Holdings, Inc.", last_price=6.73)
        assert quote.symbol == "DMC"
        assert quote.last_price == 6.73

    def test_ohlcv_creation(self):
        ohlcv = OHLCV(date=date(2026, 11, 11), open=6.80, high=6.90, low=6.80, close=6.83, volume=11192951)
        assert ohlcv.date == date(2026, 11, 11)
        assert ohlcv.volume == 11192951


class TestPseEdgeClient:
    @pytest.fixture
    def client(self):
        return PseEdgeClient(get_settings())

    def test_resolve_symbol(self, client):
        """Test symbol resolution for known companies."""
        dmc = client.resolve_symbol("DMC")
        assert dmc is not None
        assert dmc.symbol == "DMC"
        assert dmc.cmpy_id == 188

        fgen = client.resolve_symbol("FGEN")
        assert fgen is not None
        assert fgen.symbol == "FGEN"
        assert fgen.cmpy_id == 600

    def test_resolve_gcash(self, client):
        """Test GCASH symbol resolution."""
        gcash = client.resolve_symbol("GCASH")
        assert gcash is not None
        assert gcash.symbol == "GCASH"

    def test_get_quote(self, client):
        """Test quote fetching for DMC."""
        quote = client.get_quote(188, "DMC")
        assert quote.symbol == "DMC"
        assert quote.last_price is not None
        assert quote.last_price > 0
        assert quote.high is not None
        assert quote.low is not None
        assert quote.volume is not None

    def test_get_quote_gcash(self, client):
        """Test quote fetching for GCASH."""
        quote = client.get_quote(709, "GCASH")
        assert quote.symbol == "GCASH"
        assert quote.last_price is not None
        assert quote.last_price > 0

    def test_get_price_history(self, client):
        """Test price history fetching for DMC."""
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=30)
        history = client.get_price_history(188, "DMC")
        assert len(history) > 0
        assert history[0].date >= start_date
        assert history[0].date <= end_date
        assert all(h.open > 0 for h in history)
        assert all(h.high > 0 for h in history)
        assert all(h.low > 0 for h in history)
        assert all(h.close > 0 for h in history)
        assert all(h.volume > 0 for h in history)

    def test_get_price_history_gcash(self, client):
        """Test price history fetching for GCASH."""
        history = client.get_price_history(709, "GCASH")
        assert len(history) > 0

    def test_parse_quote_fields(self):
        """Test the _extract_quote_fields method."""
        client = PseEdgeClient(get_settings())
        soup = BeautifulSoup(
            '<table><tr><td>Last Traded Price</td><td>6.73</td>'
            '<td>Open</td><td>6.83</td><td>High</td><td>6.90</td></tr></table>',
            "lxml",
        )
        table = soup.find("table")
        rows = table.find_all("tr")
        cells = rows[0].find_all(["td", "th"])
        result = {"last_price": None, "open": None, "high": None}
        client._extract_quote_fields(result, cells)
        assert result["last_price"] == 6.73
        assert result["open"] == 6.83
        assert result["high"] == 6.90

    def test_parse_float(self):
        """Test float parsing with various formats."""
        assert PseEdgeClient._parse_float("6.73") == 6.73
        assert PseEdgeClient._parse_float("1,234.56") == 1234.56
        assert PseEdgeClient._parse_float("N/A") is None
        assert PseEdgeClient._parse_float("-") is None
        assert PseEdgeClient._parse_float("6.83\n    (Nov 11, 2026)") == 6.83

    def test_parse_int(self):
        """Test integer parsing with various formats."""
        assert PseEdgeClient._parse_int("1,851,400") == 1851400
        assert PseEdgeClient._parse_int("N/A") is None
        assert PseEdgeClient._parse_int("-") is None

    def test_parse_percent(self):
        """Test percentage parsing."""
        assert PseEdgeClient._parse_percent("1.46%") == 1.46
        assert PseEdgeClient._parse_percent("+1.46%") == 1.46
        assert PseEdgeClient._parse_percent("-1.46%") == -1.46
        assert PseEdgeClient._parse_percent("N/A") is None


class TestFramesPseClient:
    @pytest.fixture
    def client(self):
        return FramesPseClient(get_settings())

    def test_resolve_symbol(self, client):
        """Test symbol resolution on frames.pse.com.ph."""
        gcash = client.resolve_symbol("GCASH")
        assert gcash is not None
        assert gcash.get("StockSymbol") == "GCASH"

        dmc = client.resolve_symbol("DMC")
        assert dmc is not None
        assert dmc.get("StockSymbol") == "DMC"

        fgen = client.resolve_symbol("FGEN")
        assert fgen is not None
        assert fgen.get("StockSymbol") == "FGEN"

    def test_resolve_unknown_symbol(self, client):
        """Test resolution of unknown symbol."""
        result = client.resolve_symbol("NONEXISTENT123")
        assert result is None

    def test_get_quote(self, client):
        """Test quote fetching from frames.pse.com.ph."""
        quote = client.get_quote("GCASH")
        assert quote.symbol == "GCASH"
        assert quote.last_price is not None
        assert quote.last_price > 0
        assert quote.volume is not None
        assert quote.volume > 0

    def test_get_quote_fgen(self, client):
        """Test quote fetching for FGEN."""
        quote = client.get_quote("FGEN")
        assert quote.symbol == "FGEN"
        assert quote.last_price is not None
        assert quote.last_price > 0

    def test_get_companies(self, client):
        """Test company list fetching."""
        companies = client.get_companies()
        assert len(companies) > 300  # frames has 388 entries, filters to ~367 stocks
        symbols = [c.symbol for c in companies]
        assert "GCASH" in symbols
        assert "DMC" in symbols
        assert "FGEN" in symbols


class TestUnifiedPseClient:
    @pytest.fixture
    def client(self):
        return UnifiedPseClient(get_settings())

    def test_get_quote_enriched(self, client):
        """Test that unified client returns enriched data."""
        quote = client.get_quote("FGEN")
        assert quote.symbol == "FGEN"
        assert quote.last_price is not None
        assert quote.last_price > 0
        # Should have pse_edge enrichment
        assert quote.open is not None or quote.high is not None
        assert quote.week_52_high is not None or quote.market_cap is not None

    def test_get_quote_gcash(self, client):
        """Test unified quote for GCASH."""
        quote = client.get_quote("GCASH")
        assert quote.symbol == "GCASH"
        assert quote.last_price is not None
        assert quote.last_price > 0

    def test_resolve_symbol(self, client):
        """Test unified symbol resolution."""
        dmc = client.resolve_symbol("DMC")
        assert dmc is not None
        assert dmc.symbol == "DMC"

    def test_get_companies_fallback(self, client):
        """Test unified company list."""
        companies = client.get_companies()
        assert len(companies) > 0
        symbols = [c.symbol for c in companies]
        assert "GCASH" in symbols

    def test_get_price_history(self, client):
        """Test unified price history."""
        history = client.get_price_history("DMC", "1m")
        assert len(history) > 0
        assert all(h.open > 0 for h in history)
        assert all(h.high > 0 for h in history)
        assert all(h.low > 0 for h in history)
        assert all(h.close > 0 for h in history)
        assert all(h.volume >= 0 for h in history)
