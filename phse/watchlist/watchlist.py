"""Watchlist management — JSON file storage."""

from __future__ import annotations

import json
from pathlib import Path

from ..config import get_settings


def _watchlist_path() -> Path:
    """Return the path to the watchlist JSON file."""
    settings = get_settings()
    wl_dir = Path(settings.cache_dir) / "watchlist"
    wl_dir.mkdir(parents=True, exist_ok=True)
    return wl_dir / "watchlist.json"


def _load_watchlist() -> list[str]:
    """Load watchlist from JSON file."""
    path = _watchlist_path()
    if not path.exists():
        return []
    try:
        with open(path) as f:
            data = json.load(f)
        return list(data) if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _save_watchlist(symbols: list[str]) -> None:
    """Save watchlist to JSON file."""
    path = _watchlist_path()
    with open(path, "w") as f:
        json.dump(symbols, f, indent=2)


def watchlist_add(symbol: str) -> str:
    """Add a symbol to the watchlist."""
    symbols = _load_watchlist()
    symbol = symbol.upper()
    if symbol in symbols:
        return f"Symbol '{symbol}' already in watchlist"
    symbols.append(symbol)
    _save_watchlist(symbols)
    return f"Added '{symbol}' to watchlist"


def watchlist_remove(symbol: str) -> str:
    """Remove a symbol from the watchlist."""
    symbols = _load_watchlist()
    symbol = symbol.upper()
    if symbol not in symbols:
        return f"Symbol '{symbol}' not in watchlist"
    symbols.remove(symbol)
    _save_watchlist(symbols)
    return f"Removed '{symbol}' from watchlist"


def watchlist_list() -> list[str]:
    """Return current watchlist."""
    return _load_watchlist()


def watchlist_clear() -> str:
    """Clear the entire watchlist."""
    _save_watchlist([])
    return "Watchlist cleared"
