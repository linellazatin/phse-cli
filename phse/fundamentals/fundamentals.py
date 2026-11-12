"""Company fundamentals — key financial metrics."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..config import get_settings
from ..data.pse_edge import PseEdgeClient

console = Console()


def company_fundamentals(symbol: str) -> None:
    """Show key financial metrics for a company."""
    client = PseEdgeClient(get_settings())
    
    # Resolve symbol
    company = client.resolve_symbol(symbol)
    if not company:
        console.print(f"[bold red]Could not find company '{symbol}'.[/bold red]")
        return
    
    # Fetch quote
    quote = client.get_quote(company.cmpy_id, symbol)
    if not quote:
        console.print(f"[bold red]Could not fetch quote for '{symbol}'.[/bold red]")
        return
    
    # Print fundamentals
    console.print()
    console.print(Panel(
        f"[bold]{quote.company_name}[/bold]\n"
        f"[dim]Symbol: {quote.symbol} | Sector: {company.sector} | Subsector: {company.subsector}[/dim]",
        title=f"[bold]Fundamentals: {symbol}[/bold]",
        border_style="blue",
    ))
    
    # Price metrics
    table = Table(title="[bold]Price Metrics[/bold]", show_header=True, header_style="bold")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    
    if quote.last_price:
        table.add_row("Last Price", f"{quote.last_price:.2f}")
    if quote.open:
        table.add_row("Open", f"{quote.open:.2f}")
    if quote.high:
        table.add_row("High", f"{quote.high:.2f}")
    if quote.low:
        table.add_row("Low", f"{quote.low:.2f}")
    if quote.previous_close:
        table.add_row("Previous Close", f"{quote.previous_close:.2f}")
    if quote.week_52_high:
        table.add_row("52W High", f"{quote.week_52_high:.2f}")
    if quote.week_52_low:
        table.add_row("52W Low", f"{quote.week_52_low:.2f}")
    
    console.print(table)
    
    # Valuation metrics
    table = Table(title="[bold]Valuation Metrics[/bold]", show_header=True, header_style="bold")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    
    if quote.pe_ratio:
        table.add_row("P/E Ratio", f"{quote.pe_ratio:.2f}")
    else:
        table.add_row("P/E Ratio", "N/A")
    
    if quote.pb_ratio:
        table.add_row("P/BV Ratio", f"{quote.pb_ratio:.2f}")
    else:
        table.add_row("P/BV Ratio", "N/A")
    
    if quote.book_value:
        table.add_row("Book Value", f"{quote.book_value:.2f}")
    else:
        table.add_row("Book Value", "N/A")
    
    if quote.market_cap:
        table.add_row("Market Cap", f"{quote.market_cap:,.0f}")
    else:
        table.add_row("Market Cap", "N/A")
    
    console.print(table)
    
    # Volume metrics
    table = Table(title="[bold]Volume Metrics[/bold]", show_header=True, header_style="bold")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    
    if quote.volume:
        table.add_row("Volume", f"{quote.volume:,}")
    else:
        table.add_row("Volume", "N/A")
    
    if quote.value:
        table.add_row("Value (PHP)", f"{quote.value:,.2f}")
    else:
        table.add_row("Value (PHP)", "N/A")
    
    if quote.average_price:
        table.add_row("Avg Price", f"{quote.average_price:.2f}")
    else:
        table.add_row("Avg Price", "N/A")
    
    console.print(table)
    
    # Change
    if quote.change is not None and quote.percent_change is not None:
        change_color = "green" if quote.change > 0 else "red"
        console.print(f"\n[bold]Change:[/bold] [#{change_color}]{quote.change:+.2f} ({quote.percent_change:+.2f}%)[/]")
    
    console.print()
