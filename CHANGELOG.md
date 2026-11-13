# Changelog

## [0.1.1] - 2026-01-15

### Fixed

- **`phse alert check`**: Alert output now shows the actual triggering price (not the threshold repeated twice) and includes the UTC datetime when the alert was triggered. 
  - Previously: `Price 7.00 crossed below 7.00`. Now: `Price 6.64 crossed below 7.00 (2026-01-15 14:30:00 UTC)`.
- **pyproject**: fixed chart extra pypi name → `lightweight-charts` (was `lightweight-charts-python`)
- **README**: Fixed architecture diagram (`phse/watchlist/` is a directory, not a file), added missing `phse/data/exceptions.py`, added `--most-active`/`-m` and `--min-volume` scan flags, added `--period` to signals command, fixed chart toggle syntax
- **ruff checks**: fixed source files per ruff check results

### Added

- **PSE Edge health check**: Added `HealthCheckResult` dataclass and `health_check()` to `PseEdgeClient`. Pings `/companyDirectory/search.ax`, validates >50 entries, caches result 5 min. `UnifiedPseClient.get_companies()` uses health check: 
  - when pse_edge healthy, merges frames + pse_edge (original)
  - when down, returns frames-only with empty sector
  - `phse list` detects degraded data and shows warning
- Updated `alert_check()` to return `(alerts, triggering_price)` tuple and fixed alert output to show actual price + datetime.

## [0.1.0] - 2026-11-12

### Added

- **CLI commands**: `quote`, `history`, `list`, `scan`, `analyze`, `signals`, `backtest`, `chart`, `watchlist`, `alert`, `fundamentals`, `dividend`, `why`, `recap`, `about`
- **Data sources**: PSE Edge scraper (HTML/AJAX) + frames.pse.com.ph JSON parser with unified client that merges both
- **Technical indicators**: SMA (7/20/50/200), EMA (12/26), RSI (14), MACD (12/26/9), Bollinger Bands (20,2), ATR (14), VWAP
- **Signal engine**: SMA/EMA crossovers, RSI thresholds, Bollinger breaks, MACD histogram, composite scoring → BUY/HOLD/SELL
- **Backtesting**: SMA crossover strategy with P&L stats (total return, win rate, max drawdown, Sharpe ratio)
- **Interactive charts**: lightweight-charts-python candlestick renderer with volume + indicator overlays
- **Watchlist CRUD**: add/remove/list/clear with JSON storage under `~/.phse-cli/watchlist/`
- **Price alerts**: add/remove/list/check/reset with above/below threshold support
- **Market recap**: `phse recap` shows top gainers, losers, volume leaders
- **Company fundamentals**: P/E, P/BV, market cap, 52-week range, book value
- **Dividend tracker**: list/upcoming/add/remove with ex-date and payment-date
- **Signal explanation**: `phse why <SYMBOL>` shows contributing factors for composite signal
- **Bootstrap script**: `phse-bootstrap [SYMBOLS...] [--all]` for bulk historical data download
- **SQLite caching**: `~/.phse-cli/cache.db` with tables for companies (daily), quotes/ohlcv (EOD-frozen)
- **15 CLI commands** with Typer auto-help and completion

### Technical

- **Architecture**: Domain-separated modules (`data/`, `scan/`, `analysis/`, `chart/`, `watchlist/`, `recap/`, `fundamentals/`, `dividends/`, `why/`)
- **PSE Edge endpoints**: `/companyDirectory/search.ax` (POST, paginated), `/companyPage/stockData.do` (GET), `/common/DisclosureCht.ax` (POST, MM/DD/YYYY dates)
- **frames.pse.com.ph**: Embedded JSON parser from hidden `<input id="JsonId">` field, 367 stocks filtered from 388 entries
- **Unified client**: frames price + pse_edge OHLC/market cap/P/E merging
- **Test symbols**: GCASH (709, limited history), DMC (188, long history), FGEN (600, long history)
- **44 tests** passing (models, scraper, indicators, signals, backtest, chart)
- **Pydantic models**: Company, Quote, OHLCV, TechnicalSignal, AnalysisResult, ScanResult, WatchlistEntry, Alert, MarketSummary
- **Tech stack**: Typer, httpx, lxml, Pydantic, pandas, ta, lightweight-charts-python, rich, aiosqlite
- **Recap performance**: `phse recap` now runs in ~1.3s using a single frames.pse.com.ph API call (previously ~24s with per-stock fetching). All 367 companies are analyzed for gainers/losers/volume.

### Known Issues

see the [section in README](README.md#known-issues).
