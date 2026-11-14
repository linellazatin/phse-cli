## What this is

The Philippine Securities Engine (`phse`) is a CLI-first, modular Python tool for monitoring, analyzing, and generating trading recommendations for the Philippine Stock Exchange (PSE). It delivers terminal-native output with rich formatting, SQLite caching, and interactive charts.

## Architecture

- **Data Layer:** Dual data sources with automatic merging: PSE Edge (rich metadata) and frames.pse.com.ph (fast fallback). Historical OHLCV retrieval supports 1m, 3m, 6m, and 1y periods. Live quotes are persisted via EOD-frozen SQLite storage.
- **Analysis Engine:** Computes 7 technical indicators (SMA, EMA, RSI, MACD, Bollinger, ATR, VWAP) and applies composite scoring. A signal engine evaluates crossovers, thresholds, and histogram breaks to emit BUY/HOLD/SELL recommendations with explainable contributing factors.
- **Backtesting & Scanning:** Built-in backtesting tracks total return, win rate, max drawdown, and Sharpe ratio for SMA crossover strategies. Market scan filters/sorts by sector, price, or volume, with a `--bulk` mode that reduces HTTP calls from 368 to 1.
- **State Management:** Watchlists and price alerts use JSON storage. Dividend tracking records ex-dates, payment dates, and types.

## Configuration and installation

Install via PyPI or clone from source:
```bash
pip install phse-cli[chart]   # includes chart support
# or
pip install phse-cli          # CLI only
```
For development:
```bash
git clone https://github.com/linellazatin/phse-cli.git
cd phse
pip install -e ".[chart]"
# or
pip install -e .
```
Update in place with `pip install --upgrade phse-cli[chart]` or `git pull && pip install -e ".[chart]"`.

## Commands

The repository crawl detected no explicit package scripts in the top-level inventory, but the project is structured as a CLI-first application. Entry points are configured in `pyproject.toml`. Typical usage invokes the CLI binary directly with subcommands mapped to the feature modules (quotes, historical data, technical analysis, backtesting, market scan, watchlist, alerts, fundamentals, dividends, and bootstrap).

## Key files

- `pyproject.toml` – Project metadata, dependencies, and CLI entry points.
- `phse/` – Core package directory containing the modular logic.
- `tests/` – Test suite for validation.
- `scripts/` – Auxiliary execution scripts.
- `AGENTS.md` – Agent-specific instructions.
- Top-level inventory: `.github/`, `.ruff_cache/`, `.your/`, `.gitignore`, `CHANGELOG.md`, `LICENSE`, `README.md`.
- File distribution: 34 `.py` files, 4 `.md` files, plus `.toml`, `.yml`, `.TAG`, numeric asset files, and `.gitignore` variants.

## Testing and operational quirks

- The crawl detected no package scripts; rely on `pyproject.toml` for entry point resolution.
- Keep secrets and generated output out of tracked configuration.
- Inspect specific files before changing behavior; this guide is a starting point, not a substitute for reading the code.
<!-- opl-init:fp 434b230dd3b7bec1 -->
