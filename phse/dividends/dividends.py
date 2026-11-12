"""Dividend tracker — JSON-based dividend tracking."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..config import get_settings


@dataclass
class Dividend:
    """A dividend payment record."""
    symbol: str
    ex_date: str  # YYYY-MM-DD
    payment_date: str  # YYYY-MM-DD
    amount_per_share: float  # PHP
    dividend_type: str = "cash"  # cash, stock, special
    notes: str = ""


def _dividends_path() -> Path:
    """Return the path to the dividends JSON file."""
    settings = get_settings()
    d_dir = Path(settings.cache_dir) / "dividends"
    d_dir.mkdir(parents=True, exist_ok=True)
    return d_dir / "dividends.json"


def _load_dividends() -> list[Dividend]:
    """Load dividends from JSON file."""
    path = _dividends_path()
    if not path.exists():
        return []
    try:
        with open(path) as f:
            data = json.load(f)
        return [Dividend(**d) for d in data] if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError, TypeError):
        return []


def _save_dividends(dividends: list[Dividend]) -> None:
    """Save dividends to JSON file."""
    path = _dividends_path()
    with open(path, "w") as f:
        json.dump([asdict(d) for d in dividends], f, indent=2)


def dividend_add(
    symbol: str,
    ex_date: str,
    payment_date: str,
    amount: float,
    dividend_type: str = "cash",
    notes: str = "",
) -> str:
    """Add a dividend record."""
    symbol = symbol.upper()
    dividends = _load_dividends()
    # Check for duplicate
    for d in dividends:
        if d.symbol == symbol and d.ex_date == ex_date:
            return f"Dividend for '{symbol}' on {ex_date} already exists"
    dividend = Dividend(
        symbol=symbol,
        ex_date=ex_date,
        payment_date=payment_date,
        amount_per_share=amount,
        dividend_type=dividend_type,
        notes=notes,
    )
    dividends.append(dividend)
    _save_dividends(dividends)
    return f"Added dividend: {symbol} ex-{ex_date} P{amount:.4f}/share"


def dividend_remove(symbol: str, ex_date: Optional[str] = None) -> str:
    """Remove a dividend record."""
    dividends = _load_dividends()
    if ex_date:
        dividends = [d for d in dividends if not (d.symbol == symbol and d.ex_date == ex_date)]
    else:
        dividends = [d for d in dividends if d.symbol != symbol]
    _save_dividends(dividends)
    if ex_date:
        return f"Removed dividend for '{symbol}' on {ex_date}"
    return f"Removed all dividends for '{symbol}'"


def dividend_list(symbol: Optional[str] = None) -> list[dict]:
    """Return dividend records, optionally filtered by symbol."""
    dividends = _load_dividends()
    if symbol:
        symbol = symbol.upper()
        dividends = [d for d in dividends if d.symbol == symbol]
    # Sort by ex_date descending
    dividends.sort(key=lambda d: d.ex_date, reverse=True)
    return [asdict(d) for d in dividends]


def dividend_upcoming() -> list[dict]:
    """Return upcoming dividends (ex_date >= today)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dividends = dividend_list()
    return [d for d in dividends if d["ex_date"] >= today]
