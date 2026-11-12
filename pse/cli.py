"""PSE Tools CLI — Philippine Stock Exchange analysis tool."""

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
from .data.models import Company, Quote, OHLCV, ScanResult
from .data.pse_edge import PseEdgeClient

app = typer.Typer(
    name="pse",
    help="PSE Tools — Philippine Stock Exchange CLI",
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
        console.print("Run [bold]pse list[/bold] to see all listed companies.")
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
         sector: Optional[str] = typer.Option(None, "--sector", "-s",
                                               help="Filter by sector"),
         min_volume: Optional[int] = typer.Option(None, "--min-volume",
                                                   help="Minimum volume filter"),
         price_min: Optional[float] = typer.Option(None, "--price-min",
                                                    help="Minimum price filter"),
         price_max: Optional[float] = typer.Option(None, "--price-max",
                                                    help="Maximum price filter"),
         sort_by: str = typer.Option("symbol", "--sort",
                                      help="Sort by: symbol, change, volume, price"),
):
    """Scan PSE stocks with filters and sorting."""
    client = PseEdgeClient(settings)

    # Get all companies
    try:
        companies = client.get_companies()
    except Exception as e:
        console.print(f"[bold red]Error fetching company list:[/bold red] {e}")
        raise typer.Exit(code=1)

    if not companies:
        console.print("[yellow]No companies found.[/yellow]")
        return

    # Fetch quotes for all companies (batch)
    console.print("[dim]Fetching quotes...[/dim]")
    results = []
    for i, company in enumerate(companies):
        try:
            q = client.get_quote(company.cmpy_id, company.symbol)
            results.append(ScanResult(
                symbol=q.symbol,
                company_name=q.company_name,
                last_price=q.last_price,
                change=q.change,
                percent_change=q.percent_change,
                volume=q.volume,
                market_cap=q.market_cap,
                sector=company.sector,
                pe_ratio=q.pe_ratio,
            ))
        except Exception:
            pass  # Skip companies that fail to fetch

    # Apply filters
    if sector:
        sector_lower = sector.lower()
        companies_by_symbol = {c.symbol.upper(): c for c in companies}
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
        results = results[:10]
        title = "Top 10 Gainers"
    elif top_losers:
        results.sort(key=sort_by)
        results = results[:10]
        title = "Top 10 Losers"
    else:
        results.sort(key=sort_key)
        title = f"Stock Scan ({len(results)} results)"

    _print_scan_results(results, title)


# ── analyze command (placeholder for Phase 2) ──────────────────────────

@app.command()
def analyze(symbol: str):
    """Show technical analysis for a PSE stock. (Coming in Phase 2)"""
    console.print(f"[bold]{symbol}[/bold] analysis — coming soon in Phase 2")


# ── Watchlist commands (placeholder for Phase 4) ───────────────────────

@app.command()
def watchlist(action: str = typer.Option("list", "--action", "-a",
                                          help="Action: list, add, remove"),
              symbol: Optional[str] = typer.Option(None, "--symbol", "-s",
                                                    help="Stock symbol"),
):
    """Manage your stock watchlist. (Coming in Phase 4)"""
    console.print(f"[bold]Watchlist[/bold] — action: {action}, symbol: {symbol or '—'}")
    console.print("[dim]Coming in Phase 4[/dim]")


# ── Help / About ───────────────────────────────────────────────────────

@app.command()
def about():
    """Show PSE Tools info."""
    console.print(Panel(
        Text("PSE Tools — Philippine Stock Exchange CLI\n"
             "A modular tool for scanning, analyzing, and charting PSE stocks.\n\n"
             "Test symbols: GCASH (Mynt), DMC (DMCI Holdings), FGEN (First Gen)\n\n"
             "Data source: PSE Edge (edge.pse.com.ph)\n"
             "Version: 0.1.0",
             style="cyan"),
        title="[bold]PSE Tools[/bold]",
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


if __name__ == "__main__":
    app()
