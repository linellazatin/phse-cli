# PSE Tools

CLI-first, modular tool for monitoring, analyzing, and generating trading recommendations for the Philippine Stock Exchange (PSE). Terminal-native output with rich formatting, SQLite caching, and interactive charts.

## Install

```bash
pip install -e ".[chart]"   # with chart support
# or
pip install -e .           # CLI only
```

## Quick Start

```bash
# List all PSE-listed companies
pse list

# View a stock quote
pse quote DMC

# View historical prices
pse history DMC --period 6m

# Scan for top gainers/losers
pse scan --top-gainers
pse scan --top-losers
pse scan --symbols DMC,FGEN,GCASH

# Technical analysis
pse analyze DMC
pse analyze DMC --period 1y

# Signal explanation
pse why DMC

# Market recap
pse recap

# Market-wide signals
pse signals --buy
pse signals --symbols DMC,FGEN

# Backtesting
pse backtest DMC --period 1y

# Interactive charts
pse chart DMC --period 1y
pse chart FGEN --no-indicators
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
| `pse list [--force]` | List all PSE-listed companies (cached, refreshes daily) |
| `pse quote <SYMBOL> [--latest]` | Show latest stock quote (price, volume, change) |
| `pse history <SYMBOL> [-p 1m\|3m\|6m\|1y]` | Show historical OHLCV data |
| `pse-bootstrap [SYMBOLS...] [--all]` | Bootstrap historical data for symbols |

### Analysis

| Command | Description |
|---------|-------------|
| `pse analyze <SYMBOL> [-p 1y]` | Full technical analysis with indicators, signals, support/resistance |
| `pse signals [-b/--buy] [-s/--sell] [-S symbols]` | Market-wide signal scan with BUY/SELL/HOLD filtering |
| `pse backtest <SYMBOL> [-p 1y] [-s 7] [-l 20]` | SMA crossover backtest with P&L stats |

### Charts

| Command | Description |
|---------|-------------|
| `pse chart <SYMBOL> [-p 1y] [--indicators] [--no-block]` | Interactive candlestick chart with volume + indicator overlays |

### Watchlist & Alerts

| Command | Description |
|---------|-------------|
| `pse watchlist list` | List watchlist symbols |
| `pse watchlist add --symbol DMC` | Add symbol to watchlist |
| `pse watchlist remove --symbol DMC` | Remove symbol from watchlist |
| `pse watchlist clear` | Clear entire watchlist |
| `pse alert add --symbol DMC --threshold 6.00 --below` | Set price alert |
| `pse alert list` | List all alerts |
| `pse alert check --symbol DMC` | Check if alerts triggered |
| `pse alert reset` | Reset triggered alerts |

### Fundamentals & Dividends

| Command | Description |
|---------|-------------|
| `pse fundamentals DMC` | Show company financial metrics |
| `pse dividend list` | List all dividend records |
| `pse dividend upcoming` | Show upcoming dividends |
| `pse dividend add --symbol DMC --ex-date 2026-12-15 --payment-date 2027-01-15 --amount 0.50` | Add dividend record |

### Utilities

| Command | Description |
|---------|-------------|
| `pse about` | Show tool info, version, data source |

## Scan Options

```bash
pse scan --top-gainers          # Top 10 gainers
pse scan --top-losers           # Top 10 losers
pse scan --symbols DMC,FGEN     # Target specific stocks (bypasses full scan)
pse scan -n 20                  # Limit results
pse scan --sort volume          # Sort by field
pse scan --price-min 10 --price-max 100  # Price range
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
pse backtest DMC --period 1y --short 7 --long 20
```

Outputs: total return, win rate, max drawdown, Sharpe ratio.

## Architecture

```
pse-tools/
├── pse/
│   ├── cli.py              # Typer CLI with all commands
│   ├── config.py           # Settings (cache dir, throttle, etc.)
│   ├── models.py           # Shared data models
│   ├── data/
│   │   ├── pse_edge.py     # PSE Edge scraper (HTML/AJAX)
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
│   ├── test_pse_tools.py   # Core scraper & model tests
│   ├── test_analysis.py    # Indicator, signal, backtest tests
│   └── test_chart.py       # Chart rendering tests
├── scripts/
│   └── bootstrap_data.py   # Historical data bootstrap
├── pyproject.toml
└── README.md
```

## Data Source

Data is fetched from [PSE Edge](https://edge.pse.com.ph) via HTML/AJAX scraping:

- **Company list**: `POST /companyDirectory/search.ax` (paginated)
- **Quote**: `GET /companyPage/stockData.do?cmpy_id=X`
- **History**: `POST /common/DisclosureCht.ax` (AJAX with cmpy_id, security_id, dates)

No API key required. Prices are EOD-frozen in SQLite cache; metadata refreshes daily.

## Caching

SQLite cache at `~/.pse-tools/cache.db`:

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

**34 tests passing.** Test symbols: GCASH, DMC, FGEN.

## CLI Reference

```bash
pse --help                          # Show all commands
pse COMMAND --help                  # Show command help
pse watchlist --help                # Watchlist help
pse alert --help                    # Alert help
pse dividend --help                 # Dividend help
```

## License

MIT
