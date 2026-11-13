"""Configuration for Philippine Securities Engine (phse) CLI"""

import os
from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel, frozen=True):
    """Application settings. Loaded from env vars with defaults."""

    # PSE Edge base URL
    pse_base_url: str = "https://edge.pse.com.ph"

    # HTTP settings
    request_timeout: float = 30.0
    max_retries: int = 3
    throttle_delay: float = 0.5  # seconds between requests

    # Cache settings
    cache_dir: Path = Path.home() / ".phse-cli" / "cache"
    cache_ttl_seconds: int = 3600  # 1 hour for live data
    cache_ttl_eod_seconds: int = 86400  # 24 hours for EOD data

    # Watchlist
    watchlist_path: Path = Path.home() / ".phse-cli" / "watchlist.json"

    # Market hours (Asia/Manila)
    market_open_hour: int = 9
    market_open_minute: int = 30
    market_close_hour: int = 15
    market_close_minute: int = 0

    @property
    def db_path(self) -> Path:
        return self.cache_dir / "phse.db"

    @property
    def company_cache_path(self) -> Path:
        return self.cache_dir / "companies.json"


def get_settings() -> Settings:
    """Return settings, loading from environment if available."""
    settings = Settings()
    if os.environ.get("PSE_BASE_URL"):
        settings = Settings(
            pse_base_url=os.environ["PSE_BASE_URL"],
        )
    return settings
