"""Price alerts — JSON file storage with threshold checking."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..config import get_settings
from ..data.models import Quote


@dataclass
class PriceAlert:
    """A price alert for a symbol."""
    symbol: str
    threshold: float
    above: bool  # True = above, False = below
    triggered: bool = False
    triggered_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _alerts_path() -> Path:
    """Return the path to the alerts JSON file."""
    settings = get_settings()
    wl_dir = Path(settings.cache_dir) / "watchlist"
    wl_dir.mkdir(parents=True, exist_ok=True)
    return wl_dir / "alerts.json"


def _load_alerts() -> list[PriceAlert]:
    """Load alerts from JSON file."""
    path = _alerts_path()
    if not path.exists():
        return []
    try:
        with open(path) as f:
            data = json.load(f)
        return [PriceAlert(**a) for a in data] if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError, TypeError):
        return []


def _save_alerts(alerts: list[PriceAlert]) -> None:
    """Save alerts to JSON file."""
    path = _alerts_path()
    with open(path, "w") as f:
        json.dump([asdict(a) for a in alerts], f, indent=2)


def alert_add(symbol: str, threshold: float, above: bool = True) -> str:
    """Add a price alert."""
    symbol = symbol.upper()
    alerts = _load_alerts()
    # Check for duplicate
    for a in alerts:
        if a.symbol == symbol and abs(a.threshold - threshold) < 0.001 and a.above == above:
            return f"Alert for '{symbol}' at {a.threshold} ({'above' if a.above else 'below'}) already exists"
    alert = PriceAlert(
        symbol=symbol,
        threshold=threshold,
        above=above,
    )
    alerts.append(alert)
    _save_alerts(alerts)
    direction = "above" if above else "below"
    return f"Alert: '{symbol}' {direction} {threshold}"


def alert_remove(symbol: str, threshold: Optional[float] = None) -> str:
    """Remove a price alert."""
    alerts = _load_alerts()
    if threshold is not None:
        alerts = [a for a in alerts if not (a.symbol == symbol and abs(a.threshold - threshold) < 0.001)]
    else:
        alerts = [a for a in alerts if a.symbol != symbol]
    _save_alerts(alerts)
    if threshold is not None:
        return f"Removed alert for '{symbol}' at {threshold}"
    return f"Removed all alerts for '{symbol}'"


def alert_list() -> list[dict]:
    """Return current alerts."""
    alerts = _load_alerts()
    return [asdict(a) for a in alerts]


def alert_check(current_price: float, symbol: str) -> tuple[list[PriceAlert], float]:
    """Check if any alerts are triggered for a symbol at the given price.

    Returns (triggered_alerts, triggering_price).
    """
    symbol = symbol.upper()
    alerts = _load_alerts()
    triggered = []
    for alert in alerts:
        if alert.symbol != symbol or alert.triggered:
            continue
        if alert.above and current_price >= alert.threshold:
            alert.triggered = True
            alert.triggered_at = datetime.now(timezone.utc).isoformat()
            triggered.append(alert)
        elif not alert.above and current_price <= alert.threshold:
            alert.triggered = True
            alert.triggered_at = datetime.now(timezone.utc).isoformat()
            triggered.append(alert)
    if triggered:
        _save_alerts(alerts)
    return triggered, current_price


def alert_reset(symbol: Optional[str] = None) -> str:
    """Reset triggered alerts."""
    alerts = _load_alerts()
    if symbol:
        symbol = symbol.upper()
        alerts = [a if not (a.symbol == symbol and a.triggered) else _reset_alert(a) for a in alerts]
    else:
        alerts = [_reset_alert(a) for a in alerts]
    _save_alerts(alerts)
    return "Alerts reset"


def _reset_alert(alert: PriceAlert) -> PriceAlert:
    """Reset a single alert."""
    return PriceAlert(
        symbol=alert.symbol,
        threshold=alert.threshold,
        above=alert.above,
        triggered=False,
        triggered_at=None,
        created_at=alert.created_at,
    )
