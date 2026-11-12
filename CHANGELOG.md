# Changelog

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
