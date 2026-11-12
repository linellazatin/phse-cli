"""Custom exceptions for PSE Tools."""


class PseError(Exception):
    """Base exception for PSE Tools."""


class PseScrapeError(PseError):
    """Failed to parse data from PSE Edge."""

    def __init__(self, message: str, url: str = ""):
        super().__init__(message)
        self.url = url


class PseHttpError(PseError):
    """HTTP request failed."""

    def __init__(self, message: str, status_code: int = 0, url: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.url = url


class PseCacheError(PseError):
    """Cache operation failed."""


class PseSymbolNotFoundError(PseError):
    """Symbol not found in PSE directory."""

    def __init__(self, symbol: str):
        super().__init__(f"Symbol '{symbol}' not found in PSE directory.")
        self.symbol = symbol
