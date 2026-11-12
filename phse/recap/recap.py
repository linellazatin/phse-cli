"""Market recap — summary of market activity."""

from __future__ import annotations

from datetime import datetime, timezone

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..config import get_settings
from ..data.pse_edge import PseEdgeClient
from ..data.unified import UnifiedPseClient

console = Console()


def market_recap() -> None:
    """Print a market recap with top gainers, losers, and volume leaders."""
    # Use frames.pse.com.ph for market-wide data (single API call, 234 valid stocks)
    from ..data.frames_pse import FramesPseClient
    
    frames = FramesPseClient(get_settings())
    
    # Get quotes for all stocks with non-zero volume (limit for performance)
    quotes = []
    for stock in frames.get_companies()[:30]:
        try:
            q = frames.get_quote(stock.symbol)
            if q and q.last_price and q.volume and q.volume > 0 and q.percent_change is not None:
                quotes.append(q)
        except Exception:
            continue
    
    if not quotes:
        console.print("[bold red]No valid quotes available.[/bold red]")
        return
    
    if not quotes:
        console.print("[bold red]No valid quotes available.[/bold red]")
        return
    
    # Sort by change and value
    gainers = sorted(quotes, key=lambda q: q.percent_change or 0, reverse=True)[:10]
    losers = sorted(quotes, key=lambda q: q.percent_change or 0)[:10]
    volume_leaders = sorted(quotes, key=lambda q: q.volume or 0, reverse=True)[:10]
    most_active = sorted(quotes, key=lambda q: (q.value or (q.volume or 0) * (q.last_price or 0)), reverse=True)[:10]
    
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
    
    # Most active by value
    table = Table(title="[bold]Most Active by Value[/]", show_header=True, header_style="bold")
    table.add_column("Symbol", style="cyan")
    table.add_column("Price", justify="right")
    table.add_column("Volume", justify="right")
    table.add_column("Value", justify="right")
    table.add_column("% Change", justify="right")
    for q in most_active:
        trade_val = q.value or (q.volume or 0) * (q.last_price or 0)
        change_color = "green" if (q.percent_change or 0) > 0 else "red"
        table.add_row(
            q.symbol,
            f"{q.last_price:.2f}" if q.last_price else "—",
            f"{q.volume:,}" if q.volume else "—",
            f"₱{trade_val:,.0f}" if trade_val else "—",
            f"[{change_color}]{q.percent_change:+.2f}%[/]" if q.percent_change else "—",
        )
    console.print(table)
    console.print()
