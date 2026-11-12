# PSE Tools

CLI tool for the Philippine Stock Exchange (PSE). Scan stocks, view quotes, analyze charts — all from the terminal.

## Install

```bash
pip install -e .
```

## Quick Start

```bash
# List all listed companies
pse list

# View a stock quote
pse quote DMC

# View historical prices
pse history DMC --period 6m

# Scan for top gainers
pse scan --top-gainers

# Scan for top losers
pse scan --top-losers

# Scan with filters
pse scan --sector banking --min-volume 10000
```

## Test Symbols

| Symbol | Company | Notes |
|--------|---------|-------|
| GCASH | Mynt, Inc. | Newly listed (Oct 2026) |
| DMC | DMCI Holdings, Inc. | Established stock |
| FGEN | First Gen Corporation | Energy sector |

## Commands

| Command | Description |
|---------|-------------|
| `pse list` | List all PSE-listed companies |
| `pse quote <SYMBOL>` | Show latest stock quote |
| `pse history <SYMBOL> --period 1m|3m|6m|1y` | Show historical OHLCV data |
| `pse scan [options]` | Screen stocks with filters |
| `pse analyze <SYMBOL>` | Technical analysis (Phase 2) |
| `pse watchlist` | Manage watchlist (Phase 4) |
| `pse about` | Show tool info |

## Scan Options

```bash
pse scan --top-gainers          # Top 10 gainers
pse scan --top-losers           # Top 10 losers
pse scan --sector banking       # Filter by sector
pse scan --min-volume 50000     # Minimum volume
pse scan --price-min 10 --price-max 100  # Price range
pse scan --sort volume          # Sort by field
```

## Architecture

```
pse-tools/
├── pse/
│   ├── cli.py          # CLI entry point
│   ├── config.py       # Settings
│   ├── data/           # Data layer (scraper, models, cache)
│   ├── scan/           # Stock screener
│   ├── analysis/       # Technical analysis
│   └── chart/          # Chart rendering
├── tests/
└── pyproject.toml
```

## Data Source

Data is fetched from [PSE Edge](https://edge.pse.com.ph) (the official PSE portal). No API key needed.

## License

MIT
