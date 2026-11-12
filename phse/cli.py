"""Philippine Securities Engine (phse) CLI - Philippine Stock Exchange analysis tool."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import rich
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .config import get_settings
from .analysis import backtest_sma_crossover, compute_indicators, generate_signals
from .analysis.models import AnalysisResult
from .chart.renderer import render_chart
from .dividends import dividend_add, dividend_list, dividend_remove, dividend_upcoming
from .why import explain_signal
from .fundamentals import company_fundamentals
from .recap import market_recap
from .watchlist import (
    alert_add,
    alert_check,
    alert_list,
    alert_remove,
    alert_reset,
    watchlist_add,
    watchlist_clear,
    watchlist_list,
    watchlist_remove,
)
from .data.models import Company, Quote, OHLCV, ScanResult
from .data.pse_edge import PseEdgeClient

app = typer.Typer(
    name="phse",
    help="Philippine Securities Engine (phse) CLI",
    add_completion=True,
    no_args_is_help=True,
)

console = Console()
settings = get_settings()


# ── quote command ───────────────────────────────────────────────────────

@app.command()
def quote(symbol: str, latest: bool = typer.Option(False, "--latest", "-l",
          help="Force fetch latest quote (skip cache)"),
):
    """Show the latest quote for a PSE stock symbol."""
    client = PseEdgeClient(settings)

    # Resolve symbol to company
    company = client.resolve_symbol(symbol)
    if not company:
        console.print(f"[bold red]Error: Symbol '{symbol}' not found in PSE directory.[/bold red]")
        console.print("Run [bold]phse list[/bold] to see all listed companies.")
        raise typer.Exit(code=1)

    # Fetch quote
    try:
        quote_data = client.get_quote(company.cmpy_id, symbol)
    except Exception as e:
        console.print(f"[bold red]Error fetching quote:[/bold red] {e}")
        raise typer.Exit(code=1)

    _print_quote(quote_data)


# ── history command ─────────────────────────────────────────────────────

@app.command()
def history(symbol: str, period: str = typer.Option("1m", "--period", "-p",
            help="Time period: 1m, 3m, 6m, 1y"),
):
    """Show historical price data for a PSE stock."""
    client = PseEdgeClient(settings)

    # Resolve symbol
    company = client.resolve_symbol(symbol)
    if not company:
        console.print(f"[bold red]Error: Symbol '{symbol}' not found.[/bold red]")
        raise typer.Exit(code=1)

    # Fetch history
    try:
        ohlcv = client.get_price_history(company.cmpy_id, symbol, period)
    except Exception as e:
        console.print(f"[bold red]Error fetching history:[/bold red] {e}")
        raise typer.Exit(code=1)

    if not ohlcv:
        console.print(f"[yellow]No historical data available for '{symbol}' in this period.[/yellow]")
        return

    _print_history(ohlcv)


# ── list command ────────────────────────────────────────────────────────

@app.command()
def list(force: bool = typer.Option(False, "--force", "-f",
              help="Force refresh from PSE Edge (skip cache)")):
    """List all listed companies on the PSE."""
    client = PseEdgeClient(settings)

    try:
        companies = client.get_companies()
    except Exception as e:
        console.print(f"[bold red]Error fetching company list:[/bold red] {e}")
        raise typer.Exit(code=1)

    if not companies:
        console.print("[yellow]No companies found.[/yellow]")
        return

    table = Table(title=f"PSE Listed Companies ({len(companies)} total)", show_lines=True)
    table.add_column("Symbol", style="cyan", width=10)
    table.add_column("Company", style="white", width=35)
    table.add_column("Sector", style="green", width=20)
    table.add_column("Listed", style="dim", width=12)

    for c in sorted(companies, key=lambda x: x.symbol):
        listed = c.listing_date.strftime("%b %Y") if c.listing_date else "—"
        table.add_row(c.symbol, c.name, c.sector or "—", listed)

    console.print(table)


# ── scan command ────────────────────────────────────────────────────────

@app.command()
def scan(top_gainers: bool = typer.Option(False, "--top-gainers", "-g"),
         top_losers: bool = typer.Option(False, "--top-losers", "-l"),
         symbols: Optional[str] = typer.Option(None, "--symbols", "-S",
                                                help="Comma-separated symbols to scan (e.g. DMC,FGEN)"),
         sector: Optional[str] = typer.Option(None, "--sector", "-s",
                                               help="Filter by sector"),
         min_volume: Optional[int] = typer.Option(None, "--min-volume",
                                                   help="Minimum volume filter"),
         price_min: Optional[float] = typer.Option(None, "--price-min",
                                                    help="Minimum price filter"),
         price_max: Optional[float] = typer.Option(None, "--price-max",
                                                    help="Maximum price filter"),
         limit: int = typer.Option(50, "--limit", "-n",
                                    help="Maximum number of results"),
         sort_by: str = typer.Option("symbol", "--sort",
                                      help="Sort by: symbol, change, volume, price"),
):
    """Scan PSE stocks with filters and sorting."""
    client = PseEdgeClient(settings)

    # Get companies
    try:
        companies = client.get_companies()
    except Exception as e:
        console.print(f"[bold red]Error fetching company list:[/bold red] {e}")
        raise typer.Exit(code=1)

    if not companies:
        console.print("[yellow]No companies found.[/yellow]")
        return

    # Filter to specific symbols if provided
    if symbols:
        symbol_set = {s.strip().upper() for s in symbols.split(",")}
        companies = [c for c in companies if c.symbol.upper() in symbol_set]

    # Build company lookup for names
    companies_by_symbol = {c.symbol.upper(): c for c in companies}

    # Fetch quotes
    console.print(f"[dim]Fetching quotes for {len(companies)} companies...[/dim]")
    results = []
    for company in companies:
        try:
            q = client.get_quote(company.cmpy_id, company.symbol)
            # Use company name from company list (more reliable than quote page)
            company_name = companies_by_symbol.get(company.symbol.upper(), company).name
            results.append(ScanResult(
                symbol=q.symbol,
                company_name=company_name,
                last_price=q.last_price,
                change=q.change,
                percent_change=q.percent_change,
                volume=q.volume,
                market_cap=q.market_cap,
                sector=company.sector,
                pe_ratio=q.pe_ratio,
            ))
        except Exception:
            pass

    # Apply filters
    if sector:
        sector_lower = sector.lower()
        results = [r for r in results
                   if r.symbol in companies_by_symbol
                   and sector_lower in (companies_by_symbol[r.symbol].sector or "").lower()]

    if min_volume:
        results = [r for r in results if (r.volume or 0) >= min_volume]

    if price_min:
        results = [r for r in results if (r.last_price or 0) >= price_min]

    if price_max:
        results = [r for r in results if (r.last_price or float("inf")) <= price_max]

    # Sort
    sort_key = {
        "symbol": lambda r: r.symbol,
        "change": lambda r: r.percent_change or 0,
        "volume": lambda r: r.volume or 0,
        "price": lambda r: r.last_price or 0,
    }.get(sort_by, lambda r: r.symbol)

    if top_gainers:
        results.sort(key=sort_key, reverse=True)
        results = results[:min(10, limit)]
        title = "Top 10 Gainers"
    elif top_losers:
        results.sort(key=sort_key)
        results = results[:min(10, limit)]
        title = "Top 10 Losers"
    else:
        results.sort(key=sort_key)
        results = results[:limit]
        title = f"Stock Scan ({len(results)} results)"

    _print_scan_results(results, title)


# ── analyze command ───────────────────────────────────────────────────

@app.command()
def analyze(symbol: str, period: str = typer.Option("1y", "--period", "-p",
            help="Time period for analysis: 1m, 3m, 6m, 1y"),
):
    """Show technical analysis and signals for a PSE stock."""
    client = PseEdgeClient(settings)

    # Resolve symbol
    company = client.resolve_symbol(symbol)
    if not company:
        console.print(f"[bold red]Error: Symbol '{symbol}' not found.[/bold red]")
        raise typer.Exit(code=1)

    # Fetch history
    try:
        ohlcv = client.get_price_history(company.cmpy_id, symbol, period)
    except Exception as e:
        console.print(f"[bold red]Error fetching history:[/bold red] {e}")
        raise typer.Exit(code=1)

    if len(ohlcv) < 20:
        console.print(f"[yellow]Need at least 20 bars for analysis. Got {len(ohlcv)}.[/yellow]")
        return

    # Compute indicators
    indicators = compute_indicators(ohlcv, symbol)
    current_price = ohlcv[-1].close

    # Generate signals
    analysis = generate_signals(indicators, current_price)

    # Compute support/resistance from recent data
    window = min(20, len(ohlcv))
    recent = ohlcv[-window:]
    support = min(o.low for o in recent)
    resistance = max(o.high for o in recent)
    analysis.support_level = support
    analysis.resistance_level = resistance

    _print_analysis(analysis, current_price, symbol)


# ── watchlist command ─────────────────────────────────────────────────

@app.command()
def watchlist(
    command: str = typer.Argument("list", help="Command: list, add, remove, clear"),
    symbol: str = typer.Option("", "-s", "--symbol", help="Symbol to add/remove"),
):
    """Manage your watchlist."""
    if command == "list":
        items = watchlist_list()
        if not items:
            console.print("[dim]Watchlist is empty.[/dim]")
        else:
            console.print(f"[bold]Watchlist ({len(items)} symbols):[/bold]")
            for sym in items:
                console.print(f"  [green]{sym}[/green]")
    elif command == "add":
        if not symbol:
            console.print("[bold red]Error: --symbol is required for add.[/bold red]")
            raise typer.Exit(code=1)
        console.print(watchlist_add(symbol))
    elif command == "remove":
        if not symbol:
            console.print("[bold red]Error: --symbol is required for remove.[/bold red]")
            raise typer.Exit(code=1)
        console.print(watchlist_remove(symbol))
    elif command == "clear":
        console.print(watchlist_clear())
    else:
        console.print(f"[bold red]Unknown command: {command}[/bold red]")
        console.print("[dim]Available: list, add, remove, clear[/dim]")
        raise typer.Exit(code=1)


# ── why command ───────────────────────────────────────────────────────

@app.command()
def why(symbol: str, period: str = typer.Option("1y", "--period", "-p")):
    """Explain why a stock got its current signal."""
    explain_signal(symbol, period)


# ── dividend command ──────────────────────────────────────────────────

@app.command()
def dividend(
    command: str = typer.Argument("list", help="Command: list, upcoming, add, remove"),
    symbol: str = typer.Option("", "-s", "--symbol", help="Stock symbol"),
    ex_date: str = typer.Option("", "-e", "--ex-date", help="Ex-date (YYYY-MM-DD)"),
    payment_date: str = typer.Option("", "-p", "--payment-date", help="Payment date (YYYY-MM-DD)"),
    amount: float = typer.Option(0.0, "-a", "--amount", help="Amount per share (PHP)"),
):
    """Track dividend payments."""
    if command == "list":
        items = dividend_list(symbol if symbol else None)
        if not items:
            console.print("[dim]No dividend records.[/dim]")
        else:
            console.print(f"[bold]Dividend Records ({len(items)}):[/bold]")
            for d in items:
                console.print(f"  [bold]{d['symbol']}[/bold] ex-{d['ex_date']} → {d['payment_date']}  P{d['amount_per_share']:.4f}/share  [{d['dividend_type']}]")
    elif command == "upcoming":
        items = dividend_upcoming()
        if not items:
            console.print("[dim]No upcoming dividends.[/dim]")
        else:
            console.print(f"[bold]Upcoming Dividends ({len(items)}):[/bold]")
            for d in items:
                console.print(f"  [bold]{d['symbol']}[/bold] ex-{d['ex_date']}  P{d['amount_per_share']:.4f}/share")
    elif command == "add":
        if not symbol:
            console.print("[bold red]Error: --symbol is required for add.[/bold red]")
            raise typer.Exit(code=1)
        if not ex_date or not payment_date or amount <= 0:
            console.print("[bold red]Error: --ex-date, --payment-date, and --amount are required for add.[/bold red]")
            raise typer.Exit(code=1)
        console.print(dividend_add(symbol, ex_date, payment_date, amount))
    elif command == "remove":
        if not symbol:
            console.print("[bold red]Error: --symbol is required for remove.[/bold red]")
            raise typer.Exit(code=1)
        console.print(dividend_remove(symbol, ex_date if ex_date else None))
    else:
        console.print(f"[bold red]Unknown command: {command}[/bold red]")
        console.print("[dim]Available: list, upcoming, add, remove[/dim]")
        raise typer.Exit(code=1)


# ── fundamentals command ──────────────────────────────────────────────

@app.command()
def fundamentals(symbol: str):
    """Show company fundamentals and key financial metrics."""
    company_fundamentals(symbol)


# ── recap command ─────────────────────────────────────────────────────

@app.command()
def recap():
    """Show a market recap with top gainers, losers, and volume leaders."""
    market_recap()


# ── alert command ─────────────────────────────────────────────────────

@app.command()
def alert(
    command: str = typer.Argument("list", help="Command: add, list, remove, check, reset"),
    symbol: str = typer.Option("", "-s", "--symbol", help="Stock symbol"),
    threshold: float = typer.Option(0.0, "-t", "--threshold", help="Price threshold"),
    above: bool = typer.Option(True, "--above/--below", help="Alert when price is above/below threshold"),
):
    """Set and manage price alerts."""
    if command == "list":
        items = alert_list()
        if not items:
            console.print("[dim]No alerts set.[/dim]")
        else:
            console.print(f"[bold]Price Alerts ({len(items)}):[/bold]")
            for a in items:
                direction = "↑" if a["above"] else "↓"
                status = "[dim]triggered[/dim]" if a["triggered"] else "[green]active[/green]"
                console.print(f"  {direction} [bold]{a['symbol']}[/bold] at {a['threshold']:.2f} — {status}")
    elif command == "add":
        if not symbol:
            console.print("[bold red]Error: --symbol is required for add.[/bold red]")
            raise typer.Exit(code=1)
        if threshold <= 0:
            console.print("[bold red]Error: --threshold must be positive.[/bold red]")
            raise typer.Exit(code=1)
        console.print(alert_add(symbol, threshold, above))
    elif command == "remove":
        if not symbol:
            console.print("[bold red]Error: --symbol is required for remove.[/bold red]")
            raise typer.Exit(code=1)
        console.print(alert_remove(symbol, threshold if threshold > 0 else None))
    elif command == "check":
        if not symbol:
            console.print("[bold red]Error: --symbol is required for check.[/bold red]")
            raise typer.Exit(code=1)
        # Fetch current price
        from phse.data.pse_edge import PseEdgeClient
        from phse.config import get_settings
        client = PseEdgeClient(get_settings())
        quote = client.get_quote(0, symbol)
        if quote is None or quote.last_price is None:
            console.print(f"[bold red]Could not fetch quote for '{symbol}'.[/bold red]")
            raise typer.Exit(code=1)
        triggered = alert_check(quote.last_price, symbol)
        if triggered:
            console.print(f"[bold red]⚠ ALERT TRIGGERED for {symbol}![/bold red]")
            for a in triggered:
                direction = "above" if a.above else "below"
                console.print(f"  Price {a.threshold:.2f} crossed {direction} {a.threshold:.2f}")
        else:
            console.print(f"[dim]No alerts triggered for {symbol} (current: {quote.last_price:.2f})[/dim]")
    elif command == "reset":
        console.print(alert_reset(symbol if symbol else None))
    else:
        console.print(f"[bold red]Unknown command: {command}[/bold red]")
        console.print("[dim]Available: add, list, remove, check, reset[/dim]")
        raise typer.Exit(code=1)


# ── chart command ─────────────────────────────────────────────────────

@app.command()
def chart(symbol: str, period: str = typer.Option("1y", "--period", "-p",
            help="Time period: 1m, 3m, 6m, 1y"),
          indicators: bool = typer.Option(True, "--indicators/--no-indicators",
            help="Show indicator overlays (SMA, Bollinger Bands)"),
          block: bool = typer.Option(True, "--block/--no-block",
            help="Block until chart window is closed"),
):
    """Open an interactive candlestick chart for a PSE stock."""
    client = PseEdgeClient(settings)

    # Resolve symbol
    company = client.resolve_symbol(symbol)
    if not company:
        console.print(f"[bold red]Error: Symbol '{symbol}' not found.[/bold red]")
        raise typer.Exit(code=1)

    # Fetch history
    try:
        ohlcv = client.get_price_history(company.cmpy_id, symbol, period)
    except Exception as e:
        console.print(f"[bold red]Error fetching history:[/bold red] {e}")
        raise typer.Exit(code=1)

    if len(ohlcv) < 20:
        console.print(f"[yellow]Need at least 20 bars for chart. Got {len(ohlcv)}.[/yellow]")
        return

    # Compute indicators for overlays
    indicators_data = compute_indicators(ohlcv, symbol) if indicators else None

    # Render chart
    try:
        chart = render_chart(symbol, ohlcv, indicators_data)
        console.print(f"[dim]Opening chart for {symbol}...[/dim]")
        chart.show(block=block)
    except Exception as e:
        console.print(f"[bold red]Error rendering chart:[/bold red] {e}")
        console.print("[dim]Tip: Ensure lightweight-charts is installed (pip install lightweight-charts)[/dim]")
        raise typer.Exit(code=1)


# ── backtest command ──────────────────────────────────────────────────

@app.command()
def backtest(symbol: str, period: str = typer.Option("1y", "--period", "-p",
            help="Time period: 1m, 3m, 6m, 1y"),
            short: int = typer.Option(7, "--short", "-s",
            help="Short SMA period"),
            long: int = typer.Option(20, "--long", "-l",
            help="Long SMA period"),
):
    """Backtest a simple SMA crossover strategy."""
    client = PseEdgeClient(settings)

    # Resolve symbol
    company = client.resolve_symbol(symbol)
    if not company:
        console.print(f"[bold red]Error: Symbol '{symbol}' not found.[/bold red]")
        raise typer.Exit(code=1)

    # Fetch history
    try:
        ohlcv = client.get_price_history(company.cmpy_id, symbol, period)
    except Exception as e:
        console.print(f"[bold red]Error fetching history:[/bold red] {e}")
        raise typer.Exit(code=1)

    if len(ohlcv) < long + 10:
        console.print(f"[yellow]Need at least {long + 10} bars. Got {len(ohlcv)}.[/yellow]")
        return

    # Run backtest
    result = backtest_sma_crossover(ohlcv, symbol, short, long)

    # Print results
    console.print()
    console.print(Panel(
        f"[bold]{result.strategy}[/bold] on {result.symbol}\n\n"
        f"[dim]Period:[/dim]  {result.period_days} trading days\n"
        f"[dim]Total Return:[/dim]  {result.total_return_pct:+.2f}%\n"
        f"[dim]Win Rate:[/dim]  {result.win_rate:.0f}% ({result.buy_count} buys, {result.sell_count} sells)\n"
        f"[dim]Max Drawdown:[/dim]  {result.max_drawdown_pct:.2f}%\n"
        f"[dim]Sharpe Ratio:[/dim]  {result.sharpe_ratio:.2f}",
        title="Backtest Results",
        border_style="blue",
    ))
    console.print()


# ── signals command ───────────────────────────────────────────────────

@app.command()
def signals(top_gainers: bool = typer.Option(False, "--buy", "-b",
              help="Show stocks with buy signals"),
            top_losers: bool = typer.Option(False, "--sell", "-s",
              help="Show stocks with sell signals"),
            symbols: Optional[str] = typer.Option(None, "--symbols", "-S",
              help="Comma-separated symbols to analyze"),
            period: str = typer.Option("1m", "--period", "-p",
              help="Time period: 1m, 3m, 6m, 1y"),
):
    """Scan stocks for buy/sell signals."""
    client = PseEdgeClient(settings)

    # Get companies
    try:
        companies = client.get_companies()
    except Exception as e:
        console.print(f"[bold red]Error fetching company list:[/bold red] {e}")
        raise typer.Exit(code=1)

    if symbols:
        symbol_set = {s.strip().upper() for s in symbols.split(",")}
        companies = [c for c in companies if c.symbol.upper() in symbol_set]

    console.print(f"[dim]Analyzing {len(companies)} stocks...[/dim]")

    buy_signals = []
    sell_signals = []
    neutral_signals = []

    for company in companies:
        try:
            ohlcv = client.get_price_history(company.cmpy_id, company.symbol, period)
            if len(ohlcv) < 20:
                continue

            indicators = compute_indicators(ohlcv, company.symbol)
            current_price = ohlcv[-1].close
            analysis = generate_signals(indicators, current_price)

            if analysis.composite_signal == "BUY":
                buy_signals.append((company.symbol, analysis))
            elif analysis.composite_signal == "SELL":
                sell_signals.append((company.symbol, analysis))
            else:
                neutral_signals.append((company.symbol, analysis))
        except Exception:
            continue

    # Print results
    if top_gainers and buy_signals:
        buy_signals.sort(key=lambda x: x[1].composite_score, reverse=True)
        _print_signals_table("Buy Signals", buy_signals[:10])
    elif top_losers and sell_signals:
        sell_signals.sort(key=lambda x: x[1].composite_score)
        _print_signals_table("Sell Signals", sell_signals[:10])
    else:
        # Show summary
        console.print()
        console.print(Panel(
            f"[green]BUY:[/green]   {len(buy_signals)} stock(s)\n"
            f"[yellow]HOLD:[/yellow] {len(neutral_signals)} stock(s)\n"
            f"[red]SELL:[/red]   {len(sell_signals)} stock(s)",
            title=f"Signal Summary ({len(companies)} analyzed)",
        ))
        console.print()

        if buy_signals:
            buy_signals.sort(key=lambda x: x[1].composite_score, reverse=True)
            _print_signals_table("Top Buy Signals", buy_signals[:5])

        if sell_signals:
            sell_signals.sort(key=lambda x: x[1].composite_score)
            _print_signals_table("Top Sell Signals", sell_signals[:5])


# ── Help / About ───────────────────────────────────────────────────────

@app.command()
def about():
    """Show phse cli info."""
    console.print(Panel(
        Text("Philippine Securities Engine (phse) CLI\n"
             "A modular tool for scanning, analyzing, and charting PSE stocks.\n\n"
             "Data source: PSE Edge (edge.pse.com.ph)\n"
             "Version: 0.1.0",
             style="cyan"),
        title="[bold]phse cli[/bold]",
        border_style="blue",
    ))


# ── Output helpers ─────────────────────────────────────────────────────

def _print_quote(quote: Quote):
    """Print a formatted quote table."""
    # Header
    color = "green" if (quote.percent_change or 0) > 0 else "red" if (quote.percent_change or 0) < 0 else "yellow"
    arrow = "▲" if (quote.percent_change or 0) > 0 else "▼" if (quote.percent_change or 0) < 0 else "—"

    console.print()
    console.print(Panel(
        Text(f"{quote.symbol} — {quote.company_name}", style="bold white"),
        title=f"[{color}]{arrow} {quote.last_price or 'N/A'}[/{color}]",
        subtitle=f"Change: {quote.change:+.2f} ({quote.percent_change:+.2f}%)",
    ))
    console.print()

    # Price table
    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("Metric", style="dim")
    table.add_column("Value", style="white")

    table.add_row("Open", f"{quote.open:,.2f}" if quote.open else "N/A")
    table.add_row("Previous Close", f"{quote.previous_close:,.2f}" if quote.previous_close else "N/A")
    table.add_row("High", f"{quote.high:,.2f}" if quote.high else "N/A")
    table.add_row("Low", f"{quote.low:,.2f}" if quote.low else "N/A")
    table.add_row("Volume", f"{quote.volume:,}" if quote.volume else "N/A")
    table.add_row("Avg Price", f"{quote.average_price:,.2f}" if quote.average_price else "N/A")
    table.add_row("Market Cap", f"{quote.market_cap:,.0f}" if quote.market_cap else "N/A")
    table.add_row("P/E Ratio", f"{quote.pe_ratio:.2f}" if quote.pe_ratio else "N/A")
    table.add_row("P/BV Ratio", f"{quote.pb_ratio:.2f}" if quote.pb_ratio else "N/A")
    table.add_row("Book Value", f"{quote.book_value:,.2f}" if quote.book_value else "N/A")
    table.add_row("52W High", f"{quote.week_52_high:,.2f}" if quote.week_52_high else "N/A")
    table.add_row("52W Low", f"{quote.week_52_low:,.2f}" if quote.week_52_low else "N/A")

    console.print(table)

    if quote.stale:
        console.print("[dim]⚠ Data may be stale (market open)[/dim]")


def _print_history(ohlcv: list[OHLCV]):
    """Print historical OHLCV data as a table."""
    table = Table(title="Historical Price Data", show_lines=True)
    table.add_column("Date", style="dim", width=12)
    table.add_column("Open", style="white", width=12)
    table.add_column("High", style="green", width=12)
    table.add_column("Low", style="red", width=12)
    table.add_column("Close", style="white", width=12)
    table.add_column("Volume", style="dim", width=15)

    for bar in reversed(ohlcv):  # oldest first
        close_color = "green" if len(ohlcv) > 1 and bar.close >= ohlcv[max(0, ohlcv.index(bar) - 1)].close else "red"
        table.add_row(
            bar.date.strftime("%Y-%m-%d"),
            f"{bar.open:,.2f}",
            f"{bar.high:,.2f}",
            f"{bar.low:,.2f}",
            f"[{close_color}]{bar.close:,.2f}[/{close_color}]",
            f"{bar.volume:,}",
        )

    console.print(table)
    console.print(f"[dim]{len(ohlcv)} rows shown[/dim]")


def _print_scan_results(results: list[ScanResult], title: str):
    """Print scan results as a table."""
    table = Table(title=title, show_lines=True)
    table.add_column("Symbol", style="cyan", width=10)
    table.add_column("Company", style="white", width=30)
    table.add_column("Price", style="white", width=12)
    table.add_column("Change", style="green", width=12)
    table.add_column("Volume", style="dim", width=15)
    table.add_column("Mkt Cap", style="dim", width=15)
    table.add_column("Sector", style="green", width=20)

    for r in results:
        change_str = f"{r.percent_change:+.2f}%" if r.percent_change is not None else "—"
        change_style = "green" if (r.percent_change or 0) > 0 else "red" if (r.percent_change or 0) < 0 else "yellow"
        table.add_row(
            r.symbol,
            r.company_name[:28],
            f"{r.last_price:,.2f}" if r.last_price else "N/A",
            f"[{change_style}]{change_str}[/{change_style}]",
            f"{r.volume:,}" if r.volume else "N/A",
            f"{r.market_cap:,.0f}" if r.market_cap else "N/A",
            r.sector or "—",
        )

    console.print(table)


def _print_analysis(analysis: AnalysisResult, current_price: float, symbol: str):
    """Print comprehensive analysis output."""
    from .analysis.models import AnalysisResult

    # Header
    color = {"BUY": "green", "SELL": "red", "HOLD": "yellow"}.get(analysis.composite_signal, "white")
    arrow = {"BUY": "▲", "SELL": "▼", "HOLD": "—"}.get(analysis.composite_signal, "—")

    console.print()
    console.print(Panel(
        Text(f"{symbol} — Technical Analysis", style="bold white"),
        title=f"[{color}]{analysis.composite_signal} (confidence: {analysis.composite_confidence:.0%})[/{color}]",
        subtitle=f"Score: {analysis.composite_score:+.3f}  |  Current: {current_price:.2f}",
    ))
    console.print()

    # Indicators table
    ind = analysis.indicators
    table = Table(title="Technical Indicators", show_lines=False)
    table.add_column("Indicator", style="dim", width=18)
    table.add_column("Value", style="white", width=14)
    table.add_column("Signal", width=14)

    if ind.sma_7:
        table.add_row("SMA 7", f"{ind.sma_7:.2f}", _sma_signal(current_price, ind.sma_7))
    if ind.sma_20:
        table.add_row("SMA 20", f"{ind.sma_20:.2f}", _sma_signal(current_price, ind.sma_20))
    if ind.sma_50:
        table.add_row("SMA 50", f"{ind.sma_50:.2f}", _sma_signal(current_price, ind.sma_50))
    if ind.sma_200:
        table.add_row("SMA 200", f"{ind.sma_200:.2f}", _sma_signal(current_price, ind.sma_200))
    if ind.ema_12:
        table.add_row("EMA 12", f"{ind.ema_12:.2f}", _ema_signal(ind.ema_12, ind.ema_26))
    if ind.rsi_14:
        table.add_row("RSI 14", f"{ind.rsi_14:.1f}", _rsi_signal(ind.rsi_14))
    if ind.macd_line is not None:
        table.add_row("MACD", f"{ind.macd_line:.3f}", _macd_signal(ind.macd_line, ind.macd_signal, ind.macd_hist))
    if ind.bb_upper:
        table.add_row("BB Upper", f"{ind.bb_upper:.2f}", _bb_signal(current_price, ind.bb_upper, ind.bb_lower))
    if ind.bb_lower:
        table.add_row("BB Lower", f"{ind.bb_lower:.2f}", _bb_signal(current_price, ind.bb_upper, ind.bb_lower))
    if ind.atr_14:
        table.add_row("ATR 14", f"{ind.atr_14:.2f}", "—")
    if ind.vwap:
        table.add_row("VWAP", f"{ind.vwap:.2f}", "—")

    console.print(table)
    console.print()

    # Signals
    if analysis.signals:
        table2 = Table(title="Signal Details", show_lines=False)
        table2.add_column("Signal", style="dim", width=14)
        table2.add_column("Direction", width=10)
        table2.add_column("Strength", width=10)
        table2.add_column("Reason", style="white")
        for s in analysis.signals:
            dir_color = {"BUY": "green", "SELL": "red", "NEUTRAL": "yellow"}.get(s.direction, "white")
            table2.add_row(
                s.name,
                f"[{dir_color}]{s.direction}[/{dir_color}]",
                f"{s.strength:.0%}",
                s.reason,
            )
        console.print(table2)
        console.print()

    # Support/Resistance
    if analysis.support_level and analysis.resistance_level:
        console.print(f"[dim]Support:[/dim]  {analysis.support_level:.2f}  [dim]Resistance:[/dim]  {analysis.resistance_level:.2f}")


def _sma_signal(price: float, sma: float) -> str:
    """Return colored SMA signal."""
    if price > sma:
        return "[green]BULLISH[/green]"
    return "[red]BEARISH[/red]"


def _ema_signal(ema12: float, ema26: float | None) -> str:
    """Return colored EMA signal."""
    if ema26 is None:
        return "—"
    if ema12 > ema26:
        return "[green]BULLISH[/green]"
    return "[red]BEARISH[/red]"


def _rsi_signal(rsi: float) -> str:
    """Return colored RSI signal."""
    if rsi < 30:
        return "[green]OVERSOLD[/green]"
    elif rsi < 45:
        return "[green]WEAK[/green]"
    elif rsi > 70:
        return "[red]OVERBOUGHT[/red]"
    elif rsi > 55:
        return "[red]STRONG[/red]"
    return "[yellow]NEUTRAL[/yellow]"


def _macd_signal(macd: float, signal: float | None, hist: float | None) -> str:
    """Return colored MACD signal."""
    if signal is not None:
        if macd > signal:
            return "[green]BULLISH[/green]"
        return "[red]BEARISH[/red]"
    return "—"


def _bb_signal(price: float, upper: float | None, lower: float | None) -> str:
    """Return colored Bollinger Band signal."""
    if lower and price <= lower:
        return "[green]NEAR LOWER[/green]"
    if upper and price >= upper:
        return "[red]NEAR UPPER[/red]"
    return "[yellow]MIDDLE[/yellow]"


def _print_signals_table(title: str, signals: list[tuple[str, AnalysisResult]]):
    """Print a signals table."""
    table = Table(title=title, show_lines=False)
    table.add_column("Symbol", style="cyan", width=10)
    table.add_column("Signal", width=10)
    table.add_column("Score", width=10)
    table.add_column("Confidence", width=12)
    table.add_column("Key Reason", style="white")

    for symbol, analysis in signals:
        dir_color = {"BUY": "green", "SELL": "red", "HOLD": "yellow"}.get(analysis.composite_signal, "white")
        key_reason = analysis.signals[0].reason if analysis.signals else "—"
        table.add_row(
            symbol,
            f"[{dir_color}]{analysis.composite_signal}[/{dir_color}]",
            f"{analysis.composite_score:+.3f}",
            f"{analysis.composite_confidence:.0%}",
            key_reason[:40],
        )

    console.print(table)
    console.print()


if __name__ == "__main__":
    app()
