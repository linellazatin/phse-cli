"""Market recap — summary of market activity."""

from __future__ import annotations

from datetime import datetime, timezone

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..config import get_settings
from ..data.pse_edge import PseEdgeClient

console = Console()


def market_recap() -> None:
    """Print a market recap with top gainers, losers, and volume leaders."""
    client = PseEdgeClient(get_settings())
    
    # Fetch all companies
    companies = client.get_companies()
    if not companies:
        console.print("[bold red]Could not fetch company list.[/bold red]")
        return
    
    # Fetch quotes for all companies
    quotes = []
    for company in companies[:50]:  # Limit to 50 for performance
        try:
            quote = client.get_quote(company.cmpy_id, company.symbol)
            if quote and quote.last_price and quote.volume and quote.volume > 0:
                if quote.percent_change is not None:
                    quotes.append(quote)
        except Exception:
            continue
    
    if not quotes:
        console.print("[bold red]No valid quotes available.[/bold red]")
        return
    
    # Sort by change
    gainers = sorted(quotes, key=lambda q: q.percent_change or 0, reverse=True)[:10]
    losers = sorted(quotes, key=lambda q: q.percent_change or 0)[:10]
    volume_leaders = sorted(quotes, key=lambda q: q.volume or 0, reverse=True)[:10]
    
    # Print recap
    console.print()
    console.print(Panel(
        f"[bold]Market Recap — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}[/bold]\n"
        f"[dim]Based on {len(quotes)} companies from PSE Edge[/dim]",
        title="[bold]PSE Market Recap[/bold]",
        border_style="blue",
    ))
    
    # Top gainers
    table = Table(title="[bold]Top Gainers[/]", show_header=True, header_style="bold")
    table.add_column("Symbol", style="cyan")
    table.add_column("Price", justify="right")
    table.add_column("Change", justify="right")
    table.add_column("% Change", justify="right")
    for q in gainers:
        change_color = "green" if (q.percent_change or 0) > 0 else "red"
        table.add_row(
            q.symbol,
            f"{q.last_price:.2f}" if q.last_price else "—",
            f"[{change_color}]{q.change:+.2f}[/]" if q.change else "—",
            f"[{change_color}]{q.percent_change:+.2f}%[/]" if q.percent_change else "—",
        )
    console.print(table)
    
    # Top losers
    table = Table(title="[bold]Top Losers[/]", show_header=True, header_style="bold")
    table.add_column("Symbol", style="cyan")
    table.add_column("Price", justify="right")
    table.add_column("Change", justify="right")
    table.add_column("% Change", justify="right")
    for q in losers:
        change_color = "red" if (q.percent_change or 0) < 0 else "green"
        table.add_row(
            q.symbol,
            f"{q.last_price:.2f}" if q.last_price else "—",
            f"[{change_color}]{q.change:+.2f}[/]" if q.change else "—",
            f"[{change_color}]{q.percent_change:+.2f}%[/]" if q.percent_change else "—",
        )
    console.print(table)
    
    # Volume leaders
    table = Table(title="[bold]Volume Leaders[/]", show_header=True, header_style="bold")
    table.add_column("Symbol", style="cyan")
    table.add_column("Price", justify="right")
    table.add_column("Volume", justify="right")
    table.add_column("% Change", justify="right")
    for q in volume_leaders:
        change_color = "green" if (q.percent_change or 0) > 0 else "red"
        table.add_row(
            q.symbol,
            f"{q.last_price:.2f}" if q.last_price else "—",
            f"{q.volume:,}" if q.volume else "—",
            f"[{change_color}]{q.percent_change:+.2f}%[/]" if q.percent_change else "—",
        )
    console.print(table)
    console.print()
