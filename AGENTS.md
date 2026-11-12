## What this is
`phse` is a CLI-first, modular Python tool for monitoring, analyzing, and generating trading recommendations for the Philippine Stock Exchange (PSE). It provides terminal-native output with rich formatting, SQLite caching for EOD-frozen data, and interactive charts. The repository is structured around a core `phse/` package, with dedicated directories for scripts, tests, and documentation.

## Configuration and installation
Install via PyPI: `pip install phse-cli[chart]` (with chart support) or `pip install phse-cli` (CLI only). For development, clone the repository and run `pip install -e ".[chart]"` or `pip install -e .`. Update with `pip install --upgrade phse-cli[chart]` or `git pull && pip install -e .`.

## Commands
The repository crawl detected no explicit package scripts, but the project is designed as a CLI tool. Run commands directly via the installed `phse` entry point or `python -m phse`. Core capabilities include:
- Live quotes and historical OHLCV retrieval (1m/3m/6m/1y)
- Technical analysis with 7 indicators (SMA, EMA, RSI, MACD, Bollinger, ATR, VWAP) and composite scoring
- Signal engine generating BUY/HOLD/SELL recommendations
- Backtesting (SMA crossover strategy with Sharpe ratio, max drawdown, win rate)
- Market scanning, watchlist management, and price alerts
- Bootstrap utility for bulk historical data downloads

## Architecture
The codebase follows a modular, data-fetching architecture with a dual-source strategy: PSE Edge for rich data and `frames.pse.com.ph` as a fast fallback, with automatic merging. Historical data and EOD state are persisted in SQLite. The `phse/` directory contains the core logic, while `scripts/` holds auxiliary utilities. The signal engine applies technical indicators to generate composite scores. The `tests/` directory covers the test suite.

## Key files
Top-level inventory:
- `phse/` — Core Python package (34 `.py` files)
- `tests/` — Test suite
- `scripts/` — Auxiliary scripts
- `docs/` — Documentation
- `.your/` — Project-specific configuration
- `pyproject.toml` — Build configuration and dependencies
- `.gitignore`, `CHANGELOG.md`, `LICENSE`, `README.md`
- `.diagram-design` (1), `.gitignore` (2), `.md` (3), `LICENSE` (1), `.toml` (1), `.html` (2), `.py` (34)

## Testing and operational quirks
No automated test runner or CI configuration was detected in the crawl. Maintain narrow test scope when modifying behavior. Keep secrets and generated output out of tracked configuration. The dual data source fallback requires network access; offline mode relies entirely on the SQLite cache. Bootstrap operations can be resource-intensive for full market scans.
<!-- opl-init:fp a9ba3f5ccfc3304f -->
