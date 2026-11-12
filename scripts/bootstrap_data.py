#!/usr/bin/env python3
"""Bootstrap script — download initial historical data for PSE stocks.

Usage:
    python -m scripts.bootstrap_data          # Default: DMC, FGEN
    python -m scripts.bootstrap_data DMC FGEN GCASH  # Specific symbols
    python -m scripts.bootstrap_data --all     # All listed companies
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta, timezone

from phse.config import get_settings
from phse.data.pse_edge import PseEdgeClient


def bootstrap(symbols: list[str], period: str = "1y", all_companies: bool = False):
    """Download historical data for the given symbols."""
    client = PseEdgeClient(get_settings())
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=365)  # 1 year

    # Resolve symbols
    if all_companies:
        companies = client.get_companies()
        symbols = [c.symbol for c in companies]
        print(f"Bootstrapping {len(symbols)} companies for {period}...")
    else:
        companies = []
        for sym in symbols:
            company = client.resolve_symbol(sym)
            if company:
                companies.append(company)
            else:
                print(f"[WARN] Symbol '{sym}' not found, skipping")
        if not companies:
            print("[ERROR] No valid symbols to bootstrap")
            sys.exit(1)
        print(f"Bootstrapping {len(companies)} companies for {period}...")

    total = len(companies)
    for i, company in enumerate(companies, 1):
        print(f"[{i}/{total}] {company.symbol} ({company.name})...", end=" ", flush=True)
        try:
            ohlcv = client.get_price_history(company.cmpy_id, company.symbol, period)
            if ohlcv:
                print(f"{len(ohlcv)} bars (oldest: {ohlcv[0].date}, newest: {ohlcv[-1].date})")
            else:
                print("no data")
        except Exception as e:
            print(f"error: {e}")
        time.sleep(0.5)  # throttle

    print(f"\nDone. Bootstrapped {total} companies.")


if __name__ == "__main__":
    import typer

    typer.run(bootstrap)
