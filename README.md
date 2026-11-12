# Philippine Securities Engine (phse)

CLI-first, modular tool for monitoring, analyzing, and generating trading recommendations for the Philippine Stock Exchange (PSE). Terminal-native output with rich formatting, SQLite caching, and interactive charts.

## Features

- **Live quotes** — Real-time price, volume, change with EOD-frozen SQLite caching
- **Historical data** — OHLCV history (1m/3m/6m/1y) with multi-period support
- **Technical analysis** — 7 indicators (SMA, EMA, RSI, MACD, Bollinger, ATR, VWAP) with composite scoring
- **Signal engine** — BUY/HOLD/SELL signals from SMA/EMA crossovers, RSI thresholds, Bollinger breaks, MACD histogram
- **Backtesting** — SMA crossover strategy with total return, win rate, max drawdown, Sharpe ratio
- **Interactive charts** — TradingView-style candlestick charts with volume + indicator overlays
- **Market scan** — Filter by sector, price range, volume; sort by change/volume/price
- **Watchlist** — Add/remove/list/clear symbols with JSON storage
- **Price alerts** — Set above/below thresholds, check triggers, reset alerts
- **Fundamentals** — P/E, P/BV, market cap, 52-week range, book value
- **Dividend tracker** — Track ex-dates, payment dates, dividend types
- **Signal explanation** — See contributing factors behind each composite signal
- **Market recap** — Top gainers, losers, volume leaders at a glance
- **Dual data sources** — PSE Edge (rich data) + frames.pse.com.ph (fast fallback) with automatic merging
- **Bootstrap** — Bulk download historical data for all or selected symbols

## Install

### From PyPI (recommended)

```bash
pip install phse-cli[chart]   # with chart support
# or
pip install phse-cli           # CLI only
```

### From Source (development)

```bash
git clone https://github.com/YOUR-USER/phse.git
cd phse
pip install -e ".[chart]"   # with chart support
# or
pip install -e .           # CLI only
```

### Update

```bash
# From PyPI
pip install --upgrade phse-cli[chart]

# From source
git pull
pip install -e .
```

## Quick Start

```bash
# List all PSE-listed companies
phse list

# View a stock quote
phse quote DMC

# View historical prices
phse history DMC --period 6m

# Scan for top gainers/losers
phse scan --top-gainers
phse scan --top-losers
phse scan --symbols DMC,FGEN,GCASH

# Technical analysis
phse analyze DMC
phse analyze DMC --period 1y

# Signal explanation
phse why DMC

# Market recap
phse recap

# Market-wide signals
phse signals --buy
phse signals --symbols DMC,FGEN

# Backtesting
phse backtest DMC --period 1y

# Interactive charts
phse chart DMC --period 1y
phse chart FGEN --no-indicators
```

## Test Symbols

| Symbol | Company | Notes |
|--------|---------|-------|
| GCASH | Mynt, Inc. | Listed Oct 20, 2026 — limited history. Use for scraper validation. |
| DMC | DMCI Holdings, Inc. | Long history — primary test symbol |
| FGEN | First Gen Corporation | Long history — primary test symbol |

## Commands

### Market Data

| Command | Description |
|---------|-------------|
| `phse list [--force]` | List all PSE-listed companies (cached, refreshes daily) |
| `phse quote <SYMBOL> [--latest]` | Show latest stock quote (price, volume, change) |
| `phse history <SYMBOL> [-p 1m\|3m\|6m\|1y]` | Show historical OHLCV data |
| `phse-bootstrap [SYMBOLS...] [--all]` | Bootstrap historical data for symbols |

### Analysis

| Command | Description |
|---------|-------------|
| `phse analyze <SYMBOL> [-p 1y]` | Full technical analysis with indicators, signals, support/resistance |
| `phse signals [-b/--buy] [-s/--sell] [-S symbols]` | Market-wide signal scan with BUY/SELL/HOLD filtering |
| `phse backtest <SYMBOL> [-p 1y] [-s 7] [-l 20]` | SMA crossover backtest with P&L stats |

### Charts

| Command | Description |
|---------|-------------|
| `phse chart <SYMBOL> [-p 1y] [--indicators] [--no-block]` | Interactive candlestick chart with volume + indicator overlays |

### Watchlist & Alerts

| Command | Description |
|---------|-------------|
| `phse watchlist list` | List watchlist symbols |
| `phse watchlist add --symbol DMC` | Add symbol to watchlist |
| `phse watchlist remove --symbol DMC` | Remove symbol from watchlist |
| `phse watchlist clear` | Clear entire watchlist |
| `phse alert add --symbol DMC --threshold 6.00 --below` | Set price alert |
| `phse alert list` | List all alerts |
| `phse alert check --symbol DMC` | Check if alerts triggered |
| `phse alert reset` | Reset triggered alerts |

### Fundamentals & Dividends

| Command | Description |
|---------|-------------|
| `phse fundamentals DMC` | Show company financial metrics |
| `phse dividend list` | List all dividend records |
| `phse dividend upcoming` | Show upcoming dividends |
| `phse dividend add --symbol DMC --ex-date 2026-12-15 --payment-date 2027-01-15 --amount 0.50` | Add dividend record |

### Utilities

| Command | Description |
|---------|-------------|
| `phse about` | Show tool info, version, data source |

## Scan Options

```bash
phse scan --top-gainers          # Top 10 gainers
phse scan --top-losers           # Top 10 losers
phse scan --symbols DMC,FGEN     # Target specific stocks (bypasses full scan)
phse scan -n 20                  # Limit results
phse scan --sort volume          # Sort by field
phse scan --price-min 10 --price-max 100  # Price range
```

## Technical Analysis

### Indicators

| Indicator | Period | Description |
|-----------|--------|-------------|
| SMA | 7, 20, 50, 200 | Simple Moving Average |
| EMA | 12, 26 | Exponential Moving Average |
| RSI | 14 | Relative Strength Index |
| MACD | 12, 26, 9 | Moving Average Convergence Divergence |
| Bollinger Bands | 20, 2 | Price volatility bands |
| ATR | 14 | Average True Range (volatility) |
| VWAP | — | Volume Weighted Average Price |

### Signal Engine

- **SMA Crossovers**: Golden cross (SMA 7 > 20), Death cross (SMA 50 < 200)
- **EMA Crossover**: EMA 12 vs EMA 26
- **RSI**: >70 overbought, <30 oversold
- **Bollinger**: Price above upper (sell), below lower (buy)
- **MACD**: Histogram direction and signal line crossover
- **Composite Score**: Weighted aggregation → BUY/HOLD/SELL with confidence %

### Backtesting

```bash
phse backtest DMC --period 1y --short 7 --long 20
```

Outputs: total return, win rate, max drawdown, Sharpe ratio.

## Architecture

```
phse-cli/
├── phse/
│   ├── cli.py              # Typer CLI with all commands
│   ├── config.py           # Settings (cache dir, throttle, etc.)
│   ├── models.py           # Shared data models
│   ├── data/
│   │   ├── pse_edge.py     # PSE Edge scraper (HTML/AJAX)
│   │   ├── frames_pse.py   # frames.pse.com.ph JSON parser (backup source)
│   │   ├── unified.py      # Auto-merges frames_pse + pse_edge
│   │   ├── cache.py        # SQLite caching layer
│   │   └── models.py       # Company, Quote, OHLCV models
│   ├── scan/
│   │   └── screener.py     # Stock screener with filters
│   ├── analysis/
│   │   ├── models.py       # IndicatorResult, Signal, AnalysisResult
│   │   ├── indicators.py   # SMA, EMA, RSI, MACD, BB, ATR, VWAP
│   │   ├── signals.py      # Signal engine + composite scoring
│   │   └── backtest.py     # SMA crossover backtest engine
│   ├── chart/
│   │   └── renderer.py     # lightweight-charts-python renderer
│   ├── watchlist/
│   │   ├── watchlist.py    # Watchlist CRUD
│   │   └── alerts.py       # Price alert management
│   ├── recap/
│   │   └── recap.py        # Market recap (top gainers/losers)
│   ├── fundamentals/
│   │   └── fundamentals.py # Company financial metrics
│   ├── dividends/
│   │   └── dividends.py    # Dividend tracking
│   └── why/
│       └── why.py          # Signal explanation
├── tests/
│   ├── test_phse_cli.py   # Core scraper & model tests
│   ├── test_analysis.py    # Indicator, signal, backtest tests
│   └── test_chart.py       # Chart rendering tests
├── scripts/
│   └── bootstrap_data.py   # Historical data bootstrap
├── pyproject.toml
└── README.md
```

## Data Source

Primary: [PSE Edge](https://edge.pse.com.ph) via HTML/AJAX scraping

- **Company list**: `POST /companyDirectory/search.ax` (paginated)
- **Quote**: `GET /companyPage/stockData.do?cmpy_id=X`
- **History**: `POST /common/DisclosureCht.ax` (AJAX with cmpy_id, security_id, dates)

Secondary: [frames.pse.com.ph](https://frames.pse.com.ph) via JSON parsing

- **Quote**: Embedded JSON in hidden input field (fast, lightweight)
- **Company list**: Same JSON (388 entries, filters to ~367 stocks)

Unified client merges both: frames price + pse_edge OHLC/market cap/P/E.

No API key required. Prices are EOD-frozen in SQLite cache; metadata refreshes daily.

## Caching

SQLite cache at `~/.phse-cli/cache.db`:

| Table | Refresh Policy |
|-------|---------------|
| `companies` | Daily |
| `quotes` | EOD-frozen |
| `ohlcv` | EOD-frozen |

## Tech Stack

- **CLI**: Typer (auto-help, fast development)
- **HTTP**: httpx (async HTTP client)
- **HTML Parsing**: lxml
- **Data Models**: Pydantic
- **Analysis**: pandas + ta library
- **Charts**: lightweight-charts-python (TradingView engine)
- **Cache**: SQLite (zero-config)
- **Testing**: pytest

## Tests

```bash
pytest tests/ -v          # All tests
pytest tests/test_analysis.py -v   # Analysis module
pytest tests/test_chart.py -v      # Chart module
```

**44 tests passing.** Test symbols: GCASH, DMC, FGEN.

## CLI Reference

```bash
phse --help                          # Show all commands
phse COMMAND --help                  # Show command help
phse watchlist --help                # Watchlist help
phse alert --help                    # Alert help
phse dividend --help                 # Dividend help
```

## License

MIT
